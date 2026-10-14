"""AWS Lambda handler for building weekly reports."""

import asyncio
import json
import logging
import os
from datetime import UTC
from typing import Any

import boto3

from app.reports.weekly import build_weekly_report

# Налаштовуємо логування у стандартному форматі CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_previous_iso_week() -> str:
    """Обчислює ISO-тиждень для минулого тижня у форматі YYYY-Www (наприклад, 2026-W40)."""
    from datetime import datetime, timedelta

    now = datetime.now(UTC)
    last_week = now - timedelta(days=7)
    year, week, _ = last_week.isocalendar()
    return f"{year}-W{week:02d}"


def detect_trigger_and_payload(event: dict[str, Any]) -> tuple[str, str | None]:
    """Розпізнає джерело виклику (SQS, Schedule або Direct) та витягує параметр week."""
    # 1. Подія від SQS (список Records)
    if isinstance(event, dict) and "Records" in event and len(event["Records"]) > 0:
        record = event["Records"][0]
        if record.get("eventSource") == "aws:sqs":
            try:
                body = json.loads(record.get("body", "{}"))
                trigger = body.get("source", "sqs")
                week = body.get("week")
                return trigger, week
            except (json.JSONDecodeError, TypeError):
                return "sqs", None

    # 2. Прямий виклик / EventBridge Scheduler
    if isinstance(event, dict):
        trigger = event.get("source", "schedule")
        week = event.get("week")
        return trigger, week

    return "unknown", None


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    AWS Lambda entry point для report-builder.
    У Dockerfile.lambda вказується: Command: ["app.reports.lambda_handler.handler"]
    """
    bucket_name = os.environ.get("REPORTS_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("Environment variable REPORTS_BUCKET_NAME is not set")

    # Створюємо boto3 s3 client усередині хендлера
    s3_client = boto3.client("s3")

    # Розпізнаємо тригер і розпаршуємо week
    trigger, week = detect_trigger_and_payload(event)

    # Якщо week відсутній або None, використовуємо попередній тиждень
    if not week:
        week = get_previous_iso_week()

    # --- ОБОВ'ЯЗКОВА ЛІНІЯ ЛОГУВАННЯ ДЛЯ ЗДАЧІ (Пункт 4) ---
    logger.info("report-builder triggered", extra={"trigger": trigger, "week": week})
    print(f"REPORT_BUILDER_LOG: trigger={trigger} week={week}")

    # Генеруємо звіт через асинхронну функцію
    report_bytes = asyncio.run(build_weekly_report(week))

    # Зберігаємо файл в S3
    s3_key = f"reports/{week}.csv"
    s3_client.put_object(
        Bucket=bucket_name,
        Key=s3_key,
        Body=report_bytes,
        ContentType="text/csv",
    )

    logger.info(f"Report successfully uploaded to s3://{bucket_name}/{s3_key}")

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"message": "Report built successfully", "key": s3_key, "trigger": trigger}
        ),
    }
