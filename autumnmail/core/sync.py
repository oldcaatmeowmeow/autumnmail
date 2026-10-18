from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..store import repo
from . import presets
from .connectors.base import ConnectorError
from .connectors.imap import ImapConnector

TZ = timezone(timedelta(hours=8))


def test_account(
    email: str,
    password: str,
    provider_key: str,
    imap_host: str | None = None,
    imap_port: int | None = None,
) -> dict:
    provider = presets.provider_info(provider_key)
    if not provider.available:
        raise ValueError(provider.hint)
    if not password:
        raise ValueError("请填写邮箱授权码（不是登录密码）")

    host = (imap_host or provider.imap_host or "").strip()
    port = int(imap_port or provider.imap_port)
    if not host:
        raise ValueError("缺少 IMAP 服务器地址")

    connector = ImapConnector(host=host, port=port, user=email, password=password)
    return connector.test()


def _since_for(account: dict, default_days: int) -> datetime:
    now = datetime.now(TZ)
    candidates = [now - timedelta(days=max(1, int(default_days)))]

    scan_since = account.get("scan_since")
    if scan_since:
        try:
            candidates.append(datetime.fromisoformat(scan_since))
        except ValueError:
            pass

    last_sync = account.get("last_sync_at")
    if last_sync:
        try:
            candidates.append(datetime.fromisoformat(last_sync) - timedelta(days=1))
        except ValueError:
            pass

    return max(candidates)


def sync_account(
    account_id: str,
    since_days: int = 90,
    limit: int = 200,
    connector_factory=None,
) -> dict:
    account = repo.get_account_raw(account_id)
    if not account:
        return {"ok": False, "account": "", "message": "账户不存在", "scanned": 0, "new": 0}
    if str(account["id"]).startswith("demo"):
        return {
            "ok": False,
            "account": account["email"],
            "message": "演示账户不连接真实邮箱，请先移除并添加你的 QQ / 163 邮箱",
            "scanned": 0,
            "new": 0,
        }

    password = repo.secret_store().get(repo.SECRET_ACCOUNT_PREFIX + account_id)
    if not password:
        return {
            "ok": False,
            "account": account["email"],
            "message": "未找到授权码，请移除后重新添加邮箱",
            "scanned": 0,
            "new": 0,
        }

    provider = presets.provider_info(account["provider"])
    if not provider.available:
        return {
            "ok": False,
            "account": account["email"],
            "message": provider.hint,
            "scanned": 0,
            "new": 0,
        }

    host = (account.get("imap_host") or provider.imap_host or "").strip()
    port = int(account.get("imap_port") or provider.imap_port)
    if not host:
        return {
            "ok": False,
            "account": account["email"],
            "message": "缺少 IMAP 服务器地址",
            "scanned": 0,
            "new": 0,
        }

    since = _since_for(account, since_days)
    factory = connector_factory or (lambda **kwargs: ImapConnector(**kwargs))
    connector = factory(
        host=host,
        port=port,
        user=account["email"],
        password=password,
    )

    run_id = repo.start_sync_run(account_id)
    try:
        mails = connector.fetch(since.date(), limit=limit)
        inserted = repo.upsert_messages(account_id, mails)
        repo.mark_synced(account_id)
        repo.finish_sync_run(run_id, "ok", len(mails), inserted)
        return {
            "ok": True,
            "account": account["email"],
            "scanned": len(mails),
            "new": inserted,
            "message": f"扫描 {len(mails)} 封，新增 {inserted} 封",
        }
    except ConnectorError as exc:
        repo.finish_sync_run(run_id, "error", 0, 0, str(exc))
        return {
            "ok": False,
            "account": account["email"],
            "message": str(exc),
            "scanned": 0,
            "new": 0,
        }
    except Exception as exc:  # pragma: no cover - defensive for provider quirks
        message = f"同步失败：{exc}"
        repo.finish_sync_run(run_id, "error", 0, 0, message)
        return {
            "ok": False,
            "account": account["email"],
            "message": message,
            "scanned": 0,
            "new": 0,
        }


def sync_all(since_days: int = 90, limit: int = 200) -> dict:
    accounts = [a for a in repo.list_accounts() if a.get("enabled")]
    real = [a for a in accounts if not str(a["id"]).startswith("demo")]
    if not real:
        return {
            "ok": False,
            "message": "还没有添加真实邮箱",
            "results": [],
            "scanned": 0,
            "new": 0,
        }

    results = [sync_account(a["id"], since_days=since_days, limit=limit) for a in real]
    scanned = sum(r.get("scanned", 0) for r in results)
    new = sum(r.get("new", 0) for r in results)
    ok = all(r.get("ok") for r in results)
    return {
        "ok": ok,
        "message": f"扫描 {scanned} 封，新增 {new} 封" if ok else "部分邮箱同步失败",
        "results": results,
        "scanned": scanned,
        "new": new,
    }
