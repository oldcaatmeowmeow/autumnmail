from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

import uvicorn

from . import __version__, paths
from .core import scheduler
from .security.token import new_token
from .server import create_app
from .store import repo

_MUTEX_HANDLE = None


class ServerThread(threading.Thread):
    def __init__(self, app, port: int) -> None:
        super().__init__(daemon=True, name="autumnmail-server")
        self.config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="debug" if os.environ.get("AUTUMNMAIL_DEBUG") else "warning",
            access_log=False,
        )
        self.server = uvicorn.Server(self.config)

    def run(self) -> None:  # pragma: no cover - thread entry
        self.server.run()

    def stop(self) -> None:
        self.server.should_exit = True


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(port: int, timeout: float = 20.0) -> bool:
    url = f"http://127.0.0.1:{port}/api/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False


def acquire_single_instance():
    """Return a handle, or None if another instance already owns the mutex."""
    global _MUTEX_HANDLE
    if os.name != "nt":
        return object()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_bool,
        ctypes.c_wchar_p,
    ]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel32.CreateMutexW(None, False, "Local\\AutumnMail_Singleton")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                "秋信（AutumnMail）已在运行。\n请在任务栏或浏览器窗口中打开。",
                "秋信",
                0x40,
            )
        except Exception:
            pass
        return None
    _MUTEX_HANDLE = handle
    return handle


def _edge_candidates() -> list[Path]:
    candidates: list[Path] = []
    for env in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        base = os.environ.get(env)
        if base:
            candidates.append(
                Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            )
    for name in ("msedge", "chrome"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    return candidates


def launch_edge_app(url: str) -> bool:
    for exe in _edge_candidates():
        if not exe.exists():
            continue
        profile = paths.data_dir() / "edge-profile"
        profile.mkdir(parents=True, exist_ok=True)
        try:
            process = subprocess.Popen(
                [
                    str(exe),
                    f"--app={url}",
                    f"--user-data-dir={profile}",
                    "--window-size=1380,880",
                    "--no-first-run",
                    "--no-default-browser-check",
                ]
            )
            process.wait()
            return True
        except Exception as exc:  # pragma: no cover - platform dependent
            print(f"[edge] 启动失败: {exc}")
    return False


def launch_window(url: str, debug: bool = False) -> None:
    try:
        import webview

        webview.create_window(
            "秋信 · AutumnMail",
            url,
            width=1380,
            height=880,
            min_size=(1080, 680),
            background_color="#0b1220",
        )
        webview.start(
            debug=debug,
            private_mode=False,
            storage_path=str(paths.data_dir() / "webview"),
        )
        return
    except Exception as exc:  # pragma: no cover - platform dependent
        print(f"[webview] 启动失败，回退到 Edge 应用窗口: {exc}")

    if launch_edge_app(url):
        return

    print("[fallback] 未找到 Edge/Chrome，改用默认浏览器。")
    webbrowser.open(url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


def _configure_stdio() -> None:
    """Keep Chinese CLI output readable on Windows terminals."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(prog="autumnmail", description="秋信（AutumnMail）· 秋招邮件助手")
    parser.add_argument("--no-window", action="store_true", help="只启动本地服务，不开窗口")
    parser.add_argument("--open", action="store_true", help="配合 --no-window，自动打开浏览器")
    parser.add_argument("--dev", action="store_true", help="开发模式（开启 /docs 与调试日志）")
    parser.add_argument("--debug", action="store_true", help="pywebview 调试模式")
    parser.add_argument("--port", type=int, default=0, help="固定端口（默认随机）")
    parser.add_argument("--data-dir", default=None, help="覆盖本地数据目录")
    parser.add_argument("--allow-multi", action="store_true", help="允许多实例运行")
    parser.add_argument("--no-scheduler", action="store_true", help="不启动后台定时同步")
    args = parser.parse_args(argv)

    if args.data_dir:
        os.environ["AUTUMNMAIL_DATA_DIR"] = str(Path(args.data_dir).expanduser().resolve())
    if args.dev:
        os.environ.setdefault("AUTUMNMAIL_DEBUG", "1")

    paths.ensure_dirs()
    if not args.allow_multi and acquire_single_instance() is None:
        return 0

    token = os.environ.get("AUTUMNMAIL_TOKEN") or new_token()
    port = args.port or free_port()
    app = create_app(token=token, dev=args.dev)
    server = ServerThread(app, port)
    server.start()

    if not wait_health(port):
        print("服务启动失败：健康检查超时。", flush=True)
        server.stop()
        return 1

    url = f"http://127.0.0.1:{port}/#token={token}"
    print(f"秋信 AutumnMail {__version__}", flush=True)
    print(f"本地服务: http://127.0.0.1:{port}", flush=True)
    print(f"数据目录: {paths.data_dir()}", flush=True)
    print(f"访问地址: {url}", flush=True)

    if not args.no_scheduler:
        settings = repo.get_settings()
        scheduler.start(settings["scan_interval_min"])

    try:
        if args.no_window:
            if args.open:
                webbrowser.open(url)
            print("按 Ctrl+C 停止。")
            while True:
                time.sleep(1)
        else:
            launch_window(url, debug=args.debug)
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.stop()
        server.stop()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
