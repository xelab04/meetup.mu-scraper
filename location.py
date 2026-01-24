import os
import sys
import json
import re
import requests
from typing import Any, Dict

try:

    OLLAMA_URL=os.environ["OLLAMA_URL"]
    OLLAMA_PORT=os.environ["OLLAMA_PORT"]
    OLLAMA_MODEL=os.environ["OLLAMA_MODEL"]

except KeyError as e:
    print("Missing env vars")
    print(e)
    sys.exit(1)



def ical_unescape(value: str) -> str:
    """Unescape iCalendar text values (RFC 5545)."""

    return (
        value.replace(r"\n", "\n")
        .replace(r"\N", "\n")
        .replace(r"\,", ",")
        .replace(r"\;", ";")
        .replace(r"\\", "\\")
    )

def join_broken_lines(description: str) -> str:
    """Join lines that are broken according to iCalendar folding rules."""
    return re.sub(r'(\w)\s*\n\s*(\w)', r'\1\2', description)



JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {"venue_name": {"type": ["string", "null"]}},
    "required": ["venue_name"],
    "additionalProperties": False,
}

PROMPT = (
    'Extract venue name. Return JSON: {"venue_name": "X"} or {"venue_name": null}\n'
    "\n"
    "RULES (apply in order):\n"
    "\n"
    "1. CHECK FOR PLACEHOLDER AFTER LOCATION/VENUE\n"
    "   Look for the exact pattern:\n"
    "   - 'Location: TBD' or 'Location: TBA' or 'Location: To be determined'\n"
    "   - 'Venue: TBD' or 'Venue: TBA' or 'Venue: Unknown'\n"
    "   ONLY if TBD/TBA/etc comes IMMEDIATELY after 'Location:' or 'Venue:'\n"
    "   → Return: null\n"
    "   \n"
    "   Counter-example: 'Talk TBD' + 'Location: Coder Faculty' → NOT a placeholder (TBD is for talk, not location)\n"
    "\n"
    "2. EXPLICIT VENUE\n"
    "   Look for these exact phrases:\n"
    "   - 'Meetup will be at X'\n"
    "   - 'will be at X'\n"
    "   - 'held at X'\n"
    "   - 'Location: X' where X is a real venue name (not TBD/TBA/Unknown/Pending/N/A)\n"
    "   - 'Venue: X' where X is a real venue name\n"
    "   → Return: X (venue name only, remove city/address)\n"
    "   \n"
    "   Examples:\n"
    "   'Location: Coder Faculty' → 'Coder Faculty'\n"
    "   'Meetup will be at La Plage Factory in Port Louis' → 'La Plage Factory'\n"
    "\n"
    "3. COLLABORATION FALLBACK\n"
    "   If NO explicit venue found in rule 2, check for:\n"
    "   - 'collaborating with X'\n"
    "   - 'collaboration with X'\n"
    "   → Return: X\n"
    "   \n"
    "   Example: 'MSCC is collaborating with FRCI' + no explicit venue → 'FRCI'\n"
    "\n"
    "4. NO VENUE FOUND\n"
    "   If none of the above rules match → Return: null\n"
    "\n"
    "CRITICAL:\n"
    "- TBD/TBA only counts as placeholder if DIRECTLY after 'Location:' or 'Venue:'\n"
    "- Extract ONLY the venue name, strip city/address\n"
    "- NEVER return: TBD, TBA, Unknown, Pending, N/A as the venue_name value\n"
)


def call_ollama(text: str, timeout_s: int = 60) -> Dict[str, Any]:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You extract venue names precisely. Follow instructions exactly.",
            },
            {"role": "user", "content": PROMPT + "\nTEXT:\n" + text},
        ],
        "format": JSON_SCHEMA,
        "options": {"temperature": 0},
        "stream": False,
    }

    r = requests.post(f"{OLLAMA_URL}:{OLLAMA_PORT}/api/chat", json=payload, timeout=timeout_s)
    r.raise_for_status()

    content = r.json().get("message", {}).get("content", "").strip()
    try:
        return json.loads(content) if content else {"venue_name": None}
    except json.JSONDecodeError:
        return {"venue_name": None}



def get_location(description) -> str|None:

    cleaned = ical_unescape(join_broken_lines(description.strip()))

    result = call_ollama(cleaned)

    return result.get("venue_name")
