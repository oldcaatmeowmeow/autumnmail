"""Secret storage.

On Windows we use DPAPI (per-user, per-machine) so the stored blob can only be
decrypted by the same Windows account. On other platforms we fall back to an
explicitly-marked plain base64 blob so development still works — never ship
that fallback as a security guarantee.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from .. import paths

_IS_WINDOWS = os.name == "nt"

if _IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    class _DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    _CRYPTPROTECT_UI_FORBIDDEN = 0x01

    def _to_blob(data: bytes) -> tuple[_DATA_BLOB, ctypes.Array]:
        buffer = ctypes.create_string_buffer(data, len(data))
        blob = _DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
        return blob, buffer

    def _protect(data: bytes) -> bytes:
        blob_in, _buffer = _to_blob(data)
        blob_out = _DATA_BLOB()
        ok = ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(blob_in),
            None,
            None,
            None,
            None,
            _CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(blob_out),
        )
        if not ok:
            raise OSError("CryptProtectData failed")
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(
                ctypes.cast(blob_out.pbData, ctypes.c_void_p)
            )

    def _unprotect(data: bytes) -> bytes:
        blob_in, _buffer = _to_blob(data)
        blob_out = _DATA_BLOB()
        ok = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in),
            None,
            None,
            None,
            None,
            _CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(blob_out),
        )
        if not ok:
            raise OSError("CryptUnprotectData failed")
        try:
            return ctypes.string_at(blob_out.pbData, blob_out.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(
                ctypes.cast(blob_out.pbData, ctypes.c_void_p)
            )


class SecretStore:
    """Tiny encrypted key/value store backed by a JSON file."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else paths.secrets_path()
        self._data: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            parsed = json.loads(self.path.read_text("utf-8"))
            if isinstance(parsed, dict):
                self._data = {str(k): str(v) for k, v in parsed.items()}
        except Exception:
            self._data = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, ensure_ascii=False), "utf-8")
        os.replace(tmp, self.path)

    def set(self, name: str, value: str) -> None:
        if not value:
            self.delete(name)
            return
        raw = value.encode("utf-8")
        if _IS_WINDOWS:
            encoded = "dpapi:" + base64.b64encode(_protect(raw)).decode("ascii")
        else:
            encoded = "plain:" + base64.b64encode(raw).decode("ascii")
        self._data[name] = encoded
        self._save()

    def get(self, name: str) -> str:
        value = self._data.get(name)
        if not value:
            return ""
        try:
            prefix, payload = value.split(":", 1)
            raw = base64.b64decode(payload)
            if prefix == "dpapi" and _IS_WINDOWS:
                raw = _unprotect(raw)
            return raw.decode("utf-8")
        except Exception:
            return ""

    def has(self, name: str) -> bool:
        return bool(self._data.get(name))

    def delete(self, name: str) -> None:
        if name in self._data:
            del self._data[name]
            self._save()
