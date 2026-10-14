import csv
import io
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionFactory
from app.models.meeting import Meeting


def parse_iso_week(week_str: str) -> tuple[datetime, datetime]:
    """
    Приймає ISO-тиждень (наприклад, "2026-W40") та повертає (start_of_week, end_of_week)
    у UTC з міткою часового поясу.
    """
    start_naive = datetime.strptime(f"{week_str}-1", "%G-W%V-%u")
    start_of_week = start_naive.replace(tzinfo=UTC)
    end_of_week = start_of_week + timedelta(days=7)
    return start_of_week, end_of_week


async def build_weekly_report(week: str, db: AsyncSession | None = None) -> bytes:
    """
    Генерує CSV-звіт за вказаний ISO-тиждень (наприклад, "2026-W40").
    Працює асинхронно з AsyncSession та асинхронним двигуном проекту.
    """
    close_db = False
    if db is None:
        db = SessionFactory()
        close_db = True

    try:
        # 1. Часові рамки для поточного та попереднього тижнів
        start_curr, end_curr = parse_iso_week(week)
        start_prev, end_prev = start_curr - timedelta(days=7), start_curr

        # 2. Отримуємо зустрічі за поточний тиждень
        query_curr = select(Meeting).where(
            Meeting.starts_at < end_curr, Meeting.ends_at > start_curr
        )
        res_curr = await db.scalars(query_curr)
        curr_meetings = list(res_curr.all())

        # 3. Отримуємо зустрічі за попередній тиждень
        query_prev = select(Meeting).where(
            Meeting.starts_at < end_prev, Meeting.ends_at > start_prev
        )
        res_prev = await db.scalars(query_prev)
        prev_meetings = list(res_prev.all())

        # Обчислення показників
        curr_count = len(curr_meetings)
        curr_duration_min = sum(
            int((m.ends_at - m.starts_at).total_seconds() / 60) for m in curr_meetings
        )
        curr_duration_hrs = curr_duration_min / 60.0

        prev_count = len(prev_meetings)
        prev_duration_min = sum(
            int((m.ends_at - m.starts_at).total_seconds() / 60) for m in prev_meetings
        )
        prev_duration_hrs = prev_duration_min / 60.0

        count_change = curr_count - prev_count
        duration_change_hrs = curr_duration_hrs - prev_duration_hrs

        # 4. Топ-5 найдовших зустрічей поточного тижня
        top_5_meetings = sorted(
            curr_meetings, key=lambda m: (m.ends_at - m.starts_at).total_seconds(), reverse=True
        )[:5]

        # 5. Генерація CSV у пам'яті
        output = io.StringIO()
        writer = csv.writer(output)

        # Секція 1: Загальні підсумки
        writer.writerow(["=== SUMMARY METRICS ==="])
        writer.writerow(["Metric", "Current Week", "Previous Week", "Change"])
        writer.writerow(["ISO Week", week, f"Previous ({start_prev.strftime('%G-W%V')})", "-"])
        writer.writerow(["Total Meetings", curr_count, prev_count, f"{count_change:+d}"])
        writer.writerow(
            [
                "Total Duration (hours)",
                f"{curr_duration_hrs:.2f}",
                f"{prev_duration_hrs:.2f}",
                f"{duration_change_hrs:+.2f}",
            ]
        )
        writer.writerow([])

        # Секція 2: Топ-5 найдовших зустрічей
        writer.writerow(["=== TOP 5 LONGEST MEETINGS ==="])
        writer.writerow(["Name", "Start Time (UTC)", "Duration (minutes)", "Participants Count"])

        for m in top_5_meetings:
            duration_min = int((m.ends_at - m.starts_at).total_seconds() / 60)
            participants_cnt = len(m.participants) if m.participants else 0

            writer.writerow(
                [m.name, m.starts_at.strftime("%Y-%m-%d %H:%M"), duration_min, participants_cnt]
            )

        return output.getvalue().encode("utf-8")

    finally:
        if close_db:
            await db.close()
