import json
import os

import boto3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/agenda", tags=["agenda"])

MODEL_ID = os.getenv("PARSER_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
brt_client = boto3.client("bedrock-runtime", region_name="us-east-1")


class AgendaItem(BaseModel):
    title: str
    duration_minutes: int | None = None


class AgendaParsedResponse(BaseModel):
    summary: str
    items: list[AgendaItem]


class AgendaParseRequest(BaseModel):
    text: str


def parse_agenda_text(text: str) -> AgendaParsedResponse:
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
        modelId=MODEL_ID,
        system=[{"text": system_prompt}],
        messages=messages,
        inferenceConfig={"maxTokens": 1000, "temperature": 0.0},
    )

    raw_output = response["output"]["message"]["content"][0]["text"].strip()

    if raw_output.startswith("```"):
        lines = raw_output.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw_output = "\n".join(lines).strip()

    data = json.loads(raw_output)
    return AgendaParsedResponse(**data)


@router.post("/parse", response_model=AgendaParsedResponse)
def parse_agenda_endpoint(payload: AgendaParseRequest):
    """Parses raw agenda text into structured JSON."""
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Agenda text cannot be empty.")

    try:
        return parse_agenda_text(payload.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse agenda: {str(e)}") from e
