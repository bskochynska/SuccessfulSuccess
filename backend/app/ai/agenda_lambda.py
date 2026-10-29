# pylint: disable=no-name-in-module,import-error
import json
import logging
import time

log = logging.getLogger()
log.setLevel(logging.INFO)

PRICES = {
    "anthropic.claude-opus-5-5": {"in": 4.0 / 1000000, "out": 20.0 / 1000000},
    "anthropic.claude-haiku-5-5": {"in": 0.10 / 1000000, "out": 0.50 / 1000000},
}


def cost_usd(model: str, usage: dict) -> float:
    p = PRICES.get(model, PRICES["anthropic.claude-opus-5-5"])
    return (usage.get("input_tokens", 0) * p["in"]) + (usage.get("output_tokens", 0) * p["out"])


def handler(event, context):
    headers = {
        "content-type": "application/json",
        "access-control-allow-origin": "*",
        "access-control-allow-headers": "*",
        "access-control-allow-methods": "POST, OPTIONS",
    }

    # 1. Швидка обробка OPTIONS без виклику зовнішніх імпортів
    request_context = event.get("requestContext", {})
    http_method = request_context.get("http", {}).get("method", event.get("httpMethod", ""))

    if http_method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": headers,
            "body": "",
        }

    try:
        # Імпортуємо парсер аженди
        from app.ai.agenda import parse_agenda_text

        # Обробка тіла запиту
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
        # Виклик парсера
        agenda = parse_agenda_text(text)
        usage = {"input_tokens": 0, "output_tokens": 0}

        latency_ms = int((time.monotonic() - started) * 1000)
        cost = cost_usd("anthropic.claude-opus-5-5", usage)

        log.info(
            json.dumps(
                {
                    "event": "agenda_parsed",
                    "model": "anthropic.claude-opus-5-5",
                    "prompt_version": "agenda-v1",
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "latency_ms": latency_ms,
                    "cost_usd": cost,
                }
            )
        )

        agenda_dict = agenda.model_dump(mode="json")

        # Формуємо відповідь із забезпеченням читабельності кирилиці (ensure_ascii=False)
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(
                {
                    "items": agenda_dict.get("items", []),
                    "summary": agenda_dict.get("summary", ""),
                    "agenda": agenda_dict,  # залишаємо для зворотної сумісності
                    "model": "anthropic.claude-opus-5-5",
                    "prompt_version": "agenda-v1",
                },
                ensure_ascii=False,  # Виправляє відображення кирилиці в JSON
            ),
        }

    except Exception as e:
        log.error(f"Execution error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"error": str(e)}),
        }
