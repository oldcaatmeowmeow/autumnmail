from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from .. import __version__
from ..store import repo
from .deps import require_token

router = APIRouter(prefix="/api", dependencies=[Depends(require_token)])
TZ = timezone(timedelta(hours=8))


class AccountIn(BaseModel):
    email: str
    auth_code: str = ""
    display_name: str | None = None


class SettingsIn(BaseModel):
    onboarded: bool | None = None
    demo_mode: bool | None = None
    scan_interval_min: int | None = None
    scan_since_days: int | None = None
    notify_enabled: bool | None = None
    quiet_hours: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_base_url: str | None = None
    llm_rules_only: bool | None = None
    llm_api_key: str | None = None
    clear_api_key: bool = False
    theme: str | None = None


class EventStatusIn(BaseModel):
    status: str


class ReviewIn(BaseModel):
    action: str = Field(default="confirm", pattern="^(confirm|skip|change)$")
    category: str | None = None


@router.get("/bootstrap")
def bootstrap() -> dict:
    settings = repo.get_settings()
    return {
        "onboarded": settings["onboarded"],
        "demo_mode": settings["demo_mode"],
        "settings": settings,
        "accounts": repo.list_accounts(),
        "counts": repo.counts(),
        "review_count": len(repo.review_queue()),
        "meta": repo.meta(),
    }


@router.get("/dashboard")
def dashboard() -> dict:
    return repo.dashboard()


@router.get("/opportunities")
def opportunities(
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> list[dict]:
    return repo.list_applications(status=status, q=q)


@router.get("/opportunities/{app_id}")
def opportunity(app_id: int) -> dict:
    data = repo.get_application(app_id)
    if not data:
        raise HTTPException(status_code=404, detail="机会不存在")
    return data


@router.get("/events")
def events(
    start: str | None = Query(default=None, alias="from"),
    end: str | None = Query(default=None, alias="to"),
) -> list[dict]:
    now = datetime.now(TZ)
    if not start:
        start = (now - timedelta(days=30)).isoformat(timespec="minutes")
    if not end:
        end = (now + timedelta(days=60)).isoformat(timespec="minutes")
    return repo.list_events(start, end)


@router.patch("/events/{event_id}")
def update_event(event_id: int, payload: EventStatusIn) -> dict:
    try:
        event = repo.update_event_status(event_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")
    return event


@router.get("/review")
def review() -> list[dict]:
    return repo.review_queue()


@router.post("/review/{event_id}")
def resolve_review(event_id: int, payload: ReviewIn) -> dict:
    event = repo.resolve_review(event_id, payload.action, payload.category)
    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")
    return event


@router.get("/accounts")
def accounts() -> list[dict]:
    return repo.list_accounts()


@router.post("/accounts", status_code=201)
def create_account(payload: AccountIn) -> dict:
    try:
        return repo.add_account(payload.email, payload.auth_code, payload.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/accounts/{account_id}")
def remove_account(account_id: str) -> dict:
    repo.delete_account(account_id)
    return {"ok": True}


@router.post("/accounts/{account_id}/test")
def test_account(account_id: str) -> dict:
    repo.public_account(account_id)
    return {
        "ok": True,
        "message": "M0 骨架：账户已记录。真实 IMAP 连接校验将在 M1 接入。",
    }


@router.get("/settings")
def settings() -> dict:
    return repo.get_settings()


@router.put("/settings")
def save_settings(payload: SettingsIn) -> dict:
    return repo.update_settings(payload.model_dump(exclude_unset=True))


@router.post("/sync")
def sync() -> dict:
    return repo.sync_mock()


@router.post("/demo/reset")
def reset_demo() -> dict:
    ok = repo.reset_demo()
    return {"ok": ok, "message": "演示数据已重置"}


@router.get("/export/csv")
def export_csv() -> Response:
    content = "\ufeff" + repo.export_csv()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="autumnmail-applications.csv"'
        },
    )


@router.get("/export/ics")
def export_ics() -> Response:
    return Response(
        content=repo.export_ics(),
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="autumnmail-interviews.ics"'
        },
    )


@router.get("/meta")
def meta() -> dict:
    data = repo.meta()
    data["version"] = __version__
    return data
