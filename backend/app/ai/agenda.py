import json
import os

import boto3
from pydantic import BaseModel, Field

# Verified Model ID / Inference Profile ID
MODEL_ID = os.getenv("PARSER_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0")

# Отримуємо регіон із системної змінної AWS Lambda або беремо eu-central-1
AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")

brt_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)


class AgendaItem(BaseModel):
    title: str = Field(description="Title or topic of the agenda item")
    duration_minutes: int | None = Field(
        default=None, description="Duration in minutes, if specified"
    )


class AgendaParsedResponse(BaseModel):
    summary: str = Field(description="Brief summary of the entire meeting agenda")
    items: list[AgendaItem] = Field(description="List of agenda items parsed from text")


def parse_agenda_text(text: str) -> AgendaParsedResponse:
    """Parses raw agenda text into structured output using Amazon Bedrock and Claude."""
    system_prompt = (
        "You are an expert meeting agenda parsing assistant. "
        "Analyze the provided text and return ONLY a valid JSON object matching "
        "the exact structure below without any explanation, intro, or markdown formatting:\n"
        "{\n"
        '  "summary": "Short meeting overview",\n'
        '  "items": [\n'
        '    {"title": "Item topic", "duration_minutes": 15}\n'
        "  ]\n"
        "}"
    )

    messages = [
        {
            "role": "user",
            "content": [{"text": f"Parse the following agenda:\n\n{text}"}],
        }
    ]

    response = brt_client.converse(
        modelId="eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
        system=[{"text": system_prompt}],
        messages=messages,
        inferenceConfig={"maxTokens": 1000, "temperature": 0.0},
    )

    raw_output = response["output"]["message"]["content"][0]["text"].strip()

    # Strip code block wrappers if model returns ```json ... ```
    if raw_output.startswith("```"):
        lines = raw_output.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw_output = "\n".join(lines).strip()

    data = json.loads(raw_output)
    return AgendaParsedResponse(**data)
