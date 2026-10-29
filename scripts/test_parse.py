import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.api.v1.agenda import parse_agenda_text  # pylint: disable=import-error

sample_agenda = """
Sprint Planning Meeting
1. Architecture Review - 20 mins
2. Bedrock Integration - 15 mins
3. QA & Testing Strategy - 10 mins
"""

if __name__ == "__main__":
    result = parse_agenda_text(sample_agenda)
    print("\nParsed Result:")
    print(result.model_dump_json(indent=2))
