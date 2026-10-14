import json
import logging
import os
from email.message import EmailMessage

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")
ses_client = boto3.client("sesv2")

SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL")


def handler(event, context):
    """
    AWS Lambda handler для надсилання звіту на email.
    Викликається подібним до s3:ObjectCreated тригером.
    """
    if not SENDER_EMAIL or not RECIPIENT_EMAIL:
        raise ValueError("Environment variables SENDER_EMAIL and RECIPIENT_EMAIL must be set")

    # 1. Парсинг події від S3
    s3_record = event["Records"][0]["s3"]
    bucket_name = s3_record["bucket"]["name"]
    object_key = s3_record["object"]["key"]

    # --- ОБОВ'ЯЗКОВА ЛІНІЯ ЛОГУВАННЯ ДЛЯ ЗДАЧІ (Пункт 4) ---
    logger.info("report-mailer triggered", extra={"trigger": "s3", "bucket": bucket_name, "key": object_key})
    print(f"REPORT_MAILER_LOG: trigger=s3 bucket={bucket_name} key={object_key}")

    # Перевірка безпеки: обробляємо тільки CSV-файли з каталогу reports/
    if not object_key.startswith("reports/") or not object_key.endswith(".csv"):
        logger.warning(f"Ignoring object outside reports/ prefix: {object_key}")
        return {"statusCode": 200, "body": "Ignored non-report file"}

    # 2. Завантаження CSV-файлу з S3
    response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
    file_content = response["Body"].read()

    filename = os.path.basename(object_key)  # наприклад "2026-W40.csv"

    # 3. Формування листа з вкладенням (MIME)
    msg = EmailMessage()
    msg["Subject"] = f"Weekly Meetings Report - {filename.replace('.csv', '')}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg.set_content(
        f"Hello,\n\nPlease find attached the weekly meetings report ({filename}).\n\nBest regards,\nAutomated Reporting System"
    )

    # Прикріплюємо CSV файл
    msg.add_attachment(
        file_content,
        maintype="text",
        subtype="csv",
        filename=filename,
    )

    # 4. Відправка листа через Amazon SES (Raw email)
    ses_client.send_email(
        FromEmailAddress=SENDER_EMAIL,
        Destination={"ToAddresses": [RECIPIENT_EMAIL]},
        Content={"Raw": {"Data": msg.as_bytes()}},
    )

    logger.info(f"Report email successfully sent to {RECIPIENT_EMAIL} with attachment {filename}")

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Email sent successfully", "file": filename}),
    }
