from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _escape(value: str | None) -> str:
    if not value:
        return ""
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def build_ics(events: list[dict], calendar_name: str = "秋招面试") -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//AutumnMail//Autumn Mail Agent//CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(calendar_name)}",
    ]
    stamp = _utc(datetime.now(timezone.utc))
    for event in events:
        raw = event.get("event_time") or event.get("deadline")
        if not raw:
            continue
        try:
            start = datetime.fromisoformat(raw)
        except ValueError:
            continue
        duration = int(event.get("duration_min") or 60)
        end = start + timedelta(minutes=duration)
        summary = " · ".join(
            part
            for part in (
                event.get("company"),
                event.get("title") or event.get("category"),
            )
            if part
        )
        description_parts = [
            f"阶段：{event.get('category') or ''}",
            f"岗位：{event.get('position') or ''}",
            f"平台：{event.get('platform') or ''}",
            f"依据：{event.get('evidence') or ''}",
        ]
        location = event.get("link") or event.get("location") or event.get("platform") or ""
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:autumnmail-event-{event.get('id')}@local",
                f"DTSTAMP:{stamp}",
                f"DTSTART:{_utc(start)}",
                f"DTEND:{_utc(end)}",
                f"SUMMARY:{_escape(summary)}",
                f"DESCRIPTION:{_escape(chr(10).join(description_parts))}",
                f"LOCATION:{_escape(location)}",
                "STATUS:CONFIRMED",
                "BEGIN:VALARM",
                "TRIGGER:-PT30M",
                "ACTION:DISPLAY",
                f"DESCRIPTION:{_escape(summary)}",
                "END:VALARM",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
