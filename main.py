import os
import sys
import json
from datetime import datetime
from functools import lru_cache
from typing import List, Dict
import uuid

import requests
from dotenv import load_dotenv
from loguru import logger
import mysql.connector
from ollama import Client

# ================================
# Config & Environment
# ================================
load_dotenv()

DATABASE_CONFIG = {
    "host": os.getenv("DATABASE_URL"),
    "port": int(os.getenv("DATABASE_PORT", 3306)),
    "user": os.getenv("DATABASE_USER"),
    "password": os.getenv("DATABASE_PASSWORD"),
    "database": os.getenv("DATABASE_DATABASE"),
}

OLLAMA_HOST = f"{os.getenv('OLLAMA_URL')}:{os.getenv('OLLAMA_PORT')}"
OLLAMA_MODEL = 'gemma3:1b'
COMMUNITY = os.getenv("COMMUNITY")

# ================================
# Logging to stdout
# ================================
logger.remove()
logger.add(sys.stdout, colorize=True,
           format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}")

# ================================
# Ollama Client & Location Cache
# ================================
ollama_client = Client(host=OLLAMA_HOST)

@lru_cache(maxsize=1024)
def get_location(description: str) -> str:
    """
    Uses Ollama AI to extract the location from a meetup description.
    Returns 'TBD' if unknown. Caches repeated calls.
    """
    prompt = (
        f"{description}\n"
        "Keep your answer brief and limited to only the answer with no extra words. "
        "Only the company name. If it is not specified or TBC, just say TBD. "
        "Where is the meetup taking place?"
    )
    try:
        response = ollama_client.chat(model=OLLAMA_MODEL, messages=[{"role": "user", "content": prompt}])
        return response.message.content.strip(".\n") or "TBD"
    except Exception as e:
        logger.warning(f"Ollama AI failed for description '{description[:30]}...': {e}")
        return "TBD"

# ================================
# iCal Parsing
# ================================
def parse_one_event(event_lines: List[str], name: str) -> Dict:
    """
    Parses a single VEVENT block from iCal into a dictionary.
    Uses iCal UID for unique event ID.
    """
    def get_value(prefix: str, default: str = "") -> str:
        return next((line.split(":", 1)[1].strip() for line in event_lines if line.startswith(prefix)), default)

    title = get_value("SUMMARY:", "No Title")
    description = get_value("DESCRIPTION:", "")
    date_str = get_value("DTSTART;TZID=Indian/Mauritius:", "19700101")
    url = get_value("URL;VALUE=URI:", "TBD")
    uid = get_value("UID:", str(uuid.uuid4()))  # fallback if UID missing

    event_date = datetime.strptime(date_str.split("T")[0], "%Y%m%d")
    location = get_location(description)
    event_id = f"{name}-{uid}"

    return {
        "id": event_id,
        "community": name,
        "title": title,
        "url": url,
        "type": "meetup",
        "location": location,
        "abstract": description,
        "date": event_date,
    }

def get_all_events(lines: List[str]) -> List[List[str]]:
    """
    Splits iCal lines into VEVENT blocks.
    """
    starts = [i for i, line in enumerate(lines) if line == "BEGIN:VEVENT"]
    ends = [i for i, line in enumerate(lines) if line == "END:VEVENT"]
    events = [lines[start:end + 1] for start, end in zip(starts, ends)]
    logger.info(f"Parsed {len(events)} VEVENTs from iCal")
    return events

# ================================
# Database Operations
# ================================
def add_to_db(events: List[Dict]):
    """
    Inserts or updates events in the database.
    """
    try:
        with mysql.connector.connect(**DATABASE_CONFIG) as conn:
            cursor = conn.cursor()
            for event in events:
                cursor.execute("DELETE FROM meetups WHERE registration = %s", (event["url"],))
                cursor.execute(
                    """
                    INSERT INTO meetups (id, community, title, registration, type, location, abstract, date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (event["id"], event["community"], event["title"], event["url"], event["type"],
                     event["location"], event["abstract"], event["date"])
                )
                logger.info(f"Inserted event: {event['title']}")
            conn.commit()
    except mysql.connector.Error as e:
        logger.error(f"Database error: {e}")

# ================================
# iCal Fetch & JSON Conversion
# ================================
def get_all_jsons(url: str, name: str) -> List[Dict]:
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch URL {url}: {e}")
        return []

    lines = [line.strip() for line in response.text.splitlines()]
    events_blocks = get_all_events(lines)
    return [parse_one_event(block, name) for block in events_blocks]

# ================================
# Community Parsers
# ================================
def frontend_mu() -> List[Dict]:
    url = "https://raw.githubusercontent.com/frontendmu/frontend.mu/main/packages/frontendmu-data/data/meetups-raw.json"
    data = requests.get(url).json()
    return [
        {
            "id": f"frontendmu-{event['id']}",
            "community": "frontendmu",
            "title": f"FrontendMU {event['title']}",
            "url": f"https://frontend.mu/meetup/{event['id']}",
            "type": "meetup",
            "location": event.get("Venue", "TBD"),
            "abstract": "",
            "date": datetime.strptime(event['Date'], "%Y-%m-%d"),
        }
        for event in data if event.get("accepting_rsvp", True)
    ]

def cnmu() -> List[Dict]:
    url = "https://cloudnativemauritius.com/api/meetups"
    data = requests.get(url).json()
    return [{**record, "id": f"cnmu-{record['id']}"} for record in data]

# ================================
# Main Flow
# ================================
def main():
    community_map = {
        "cnmu": cnmu,
        "frontendmu": frontend_mu
    }

    if COMMUNITY in community_map:
        add_to_db(community_map[COMMUNITY]())
    elif COMMUNITY == "MEETUPCOM":
        with open("communities.json") as f:
            communities = json.load(f)
        for community in communities:
            events = get_all_jsons(community["url"], community["name"])
            add_to_db(events)
    else:
        with open("newcommunities.json") as f:
            communities = json.load(f)
        events = get_all_jsons(COMMUNITY, communities[COMMUNITY])
        add_to_db(events)

if __name__ == "__main__":
    main()
