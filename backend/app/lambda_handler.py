# pylint: disable=no-name-in-module,import-error
import json
import logging
import time

log = logging.getLogger()
log.setLevel(logging.INFO)


def handler(event, context):
    headers = {
        "content-type": "application/json",
        "access-control-allow-origin": "*",
        "access-control-allow-headers": "*",
        "access-control-allow-methods": "POST, OPTIONS",
    }

    request_context = event.get("requestContext", {})
    http_method = request_context.get("http", {}).get("method", event.get("httpMethod", ""))

    if http_method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": headers,
            "body": "",
        }

    try:
        from app.ai.agenda import parse_agenda_text

        raw_body = event.get("body", "") or ""
        if len(raw_body) > 10000:
            return {
                "statusCode": 413,
                "headers": headers,
                "body": json.dumps({"error": "Payload too large"}),
            }

        try:
            body = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({"error": "Invalid JSON body"}),
            }

        text = body.get("agenda_text") or body.get("text", "")

        started = time.monotonic()
        agenda = parse_agenda_text(text)
        _latency_ms = int((time.monotonic() - started) * 1000)

        agenda_dict = agenda.model_dump(mode="json")

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(
                {
                    "items": agenda_dict.get("items", []),
                    "summary": agenda_dict.get("summary", ""),
                    "agenda": agenda_dict,
                },
                ensure_ascii=False,
            ),
        }

    except Exception as e:
        log.error(f"Execution error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"error": str(e)}),
        }
