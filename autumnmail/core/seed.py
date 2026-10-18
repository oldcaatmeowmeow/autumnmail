from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..store import db

TZ = timezone(timedelta(hours=8))


def _at(days: int, hour: int = 9, minute: int = 0) -> datetime:
    return (datetime.now(TZ) + timedelta(days=days)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )


def _iso(days: int, hour: int = 9, minute: int = 0) -> str:
    return _at(days, hour, minute).isoformat(timespec="minutes")


def _event(
    category: str,
    title: str,
    *,
    days: int | None = None,
    hour: int = 9,
    minute: int = 0,
    deadline_days: int | None = None,
    deadline_hour: int = 23,
    deadline_minute: int = 59,
    duration_min: int | None = None,
    platform: str | None = None,
    link: str | None = None,
    location: str | None = None,
    needs_reply: bool = False,
    status: str = "pending",
    evidence: str = "",
    confidence: float = 0.9,
    decided_by: str = "demo",
) -> dict:
    return {
        "category": category,
        "title": title,
        "event_time": _iso(days, hour, minute) if days is not None else None,
        "deadline": _iso(deadline_days, deadline_hour, deadline_minute)
        if deadline_days is not None
        else None,
        "duration_min": duration_min,
        "platform": platform,
        "link": link,
        "location": location,
        "needs_reply": 1 if needs_reply else 0,
        "status": status,
        "evidence": evidence,
        "confidence": confidence,
        "decided_by": decided_by,
    }


APPLICATIONS: list[dict] = [
    {
        "company": "字节跳动",
        "position": "后端开发工程师",
        "location": "北京",
        "status": "面试中",
        "events": [
            _event("投递确认", "简历已收到", days=-12, hour=10, status="done",
                   evidence="感谢您投递字节跳动后端开发工程师岗位，我们已收到您的简历。", confidence=0.96),
            _event("测评邀请", "在线测评", days=-9, hour=20, status="done",
                   evidence="请在 10 月 11 日 20:00 前完成在线测评。", confidence=0.94),
            _event("技术面", "一面", days=-5, hour=15, status="done", duration_min=45,
                   platform="飞书", evidence="邀请您参加字节跳动后端开发工程师一面。", confidence=0.90),
            _event("技术面", "二面", days=2, hour=14, duration_min=60,
                   platform="腾讯会议", link="https://meeting.tencent.com/demo",
                   needs_reply=True, confidence=0.92,
                   evidence="邀请您参加二面，时间 10 月 20 日 14:00，会议链接见邮件正文。"),
        ],
    },
    {
        "company": "美团",
        "position": "数据开发工程师",
        "location": "北京",
        "status": "测评中",
        "events": [
            _event("投递确认", "简历已收到", days=-6, hour=11, status="done",
                   evidence="感谢您投递美团数据开发工程师岗位。", confidence=0.93),
            _event("测评邀请", "在线测评（限时）", days=1, hour=23, minute=59,
                   deadline_days=1, deadline_hour=23, deadline_minute=59,
                   needs_reply=True, confidence=0.88,
                   evidence="请于 10 月 19 日 23:59 前完成在线测评，逾期视为放弃。"),
        ],
    },
    {
        "company": "腾讯",
        "position": "后台开发工程师",
        "location": "深圳",
        "status": "面试中",
        "events": [
            _event("投递确认", "简历已收到", days=-15, hour=9, minute=30, status="done",
                   evidence="感谢您投递腾讯后台开发工程师岗位。", confidence=0.95),
            _event("技术面", "一面", days=3, hour=10, minute=30, duration_min=45,
                   platform="牛客", link="https://www.nowcoder.com/demo", confidence=0.81,
                   evidence="腾讯后台开发一面安排在 10 月 21 日上午 10:30。"),
        ],
    },
    {
        "company": "阿里巴巴",
        "position": "Java 开发工程师",
        "location": "杭州",
        "status": "已拒绝",
        "events": [
            _event("投递确认", "简历已收到", days=-20, hour=14, status="done",
                   evidence="感谢您投递阿里巴巴 Java 开发工程师岗位。", confidence=0.97),
            _event("拒信", "流程结束", days=-1, hour=9, minute=30, status="done",
                   evidence="很遗憾，本次未能进入下一轮，感谢您的关注。", confidence=0.95),
        ],
    },
    {
        "company": "网易",
        "position": "游戏客户端开发",
        "location": "杭州",
        "status": "测评中",
        "events": [
            _event("笔试邀请", "在线笔试", days=1, hour=19, duration_min=90,
                   confidence=0.77,
                   evidence="网易游戏笔试将于 10 月 19 日 19:00 开始，请提前登录。"),
        ],
    },
    {
        "company": "小红书",
        "position": "前端开发工程师",
        "location": "上海",
        "status": "投递中",
        "events": [
            _event("投递确认", "简历已收到", days=-3, hour=16, status="done",
                   evidence="感谢您投递小红书前端开发工程师岗位。", confidence=0.90),
        ],
    },
    {
        "company": "云栖科技",
        "position": "全栈开发工程师",
        "location": "远程",
        "status": "面试中",
        "events": [
            _event("技术面", "一面（待确认）", days=5, hour=16, duration_min=45,
                   needs_reply=True, confidence=0.62,
                   evidence="想约您本周聊聊，方便的话回复一下时间。"),
        ],
    },
]


def seed_demo(force: bool = False) -> bool:
    """Insert a deterministic-ish demo dataset. Returns True if seeded."""
    conn = db.connect()
    try:
        count = conn.execute("SELECT COUNT(*) AS c FROM applications").fetchone()["c"]
        if count and not force:
            return False
        if force:
            conn.executescript(
                "DELETE FROM feedback; DELETE FROM events; DELETE FROM messages;"
                "DELETE FROM applications; DELETE FROM accounts;"
            )

        now = datetime.now(TZ)
        conn.execute(
            """INSERT OR REPLACE INTO accounts
               (id, email, provider, auth_type, display_name, scan_since, last_sync_at, enabled, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)""",
            (
                "demo-account",
                "demo@qq.com",
                "qq",
                "app_password",
                "演示邮箱",
                _iso(-90),
                now.isoformat(timespec="minutes"),
                _iso(-30),
            ),
        )

        msg_seq = 0
        for app in APPLICATIONS:
            earliest = min(
                (e["event_time"] for e in app["events"] if e["event_time"]),
                default=_iso(0),
            )
            last = max(
                (e["event_time"] or e["deadline"] or earliest for e in app["events"]),
                default=earliest,
            )
            cursor = conn.execute(
                """INSERT INTO applications
                   (company, company_norm, position, location, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    app["company"],
                    app["company"].lower(),
                    app["position"],
                    app["location"],
                    app["status"],
                    earliest,
                    last,
                ),
            )
            app_id = int(cursor.lastrowid)

            for event in app["events"]:
                msg_seq += 1
                message_id = f"demo-msg-{msg_seq}"
                conn.execute(
                    """INSERT INTO messages
                       (id, account_id, subject, from_addr, from_name, received_at, snippet, body_text, raw_link)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        message_id,
                        "demo-account",
                        f"{app['company']}：{event['title']}",
                        "campus@example.com",
                        app["company"] + " 校园招聘",
                        (now - timedelta(days=1)).isoformat(timespec="minutes"),
                        event["evidence"],
                        event["evidence"],
                        "",
                    ),
                )
                conn.execute(
                    """INSERT INTO events
                       (application_id, category, title, event_time, deadline, duration_min,
                        location, link, platform, needs_reply, status, evidence, message_id,
                        decided_by, confidence, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        app_id,
                        event["category"],
                        event["title"],
                        event["event_time"],
                        event["deadline"],
                        event["duration_min"],
                        event["location"] or app["location"],
                        event["link"],
                        event["platform"],
                        event["needs_reply"],
                        event["status"],
                        event["evidence"],
                        message_id,
                        event["decided_by"],
                        event["confidence"],
                        (now - timedelta(days=1)).isoformat(timespec="minutes"),
                    ),
                )

        for key, value in {
            "initialized": "true",
            "onboarded": "true",
            "demo_mode": "true",
        }.items():
            conn.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
        conn.commit()
        return True
    finally:
        conn.close()


def reset_demo() -> bool:
    conn = db.connect()
    try:
        if conn.execute("SELECT COUNT(*) AS c FROM applications").fetchone()["c"]:
            conn.executescript(
                "DELETE FROM feedback; DELETE FROM events; DELETE FROM messages;"
                "DELETE FROM applications; DELETE FROM accounts;"
            )
            conn.commit()
    finally:
        conn.close()
    return seed_demo(force=True)
