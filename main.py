import requests
from pprint import pprint
from datetime import datetime
from ollama import Client
import json
import os
from dotenv import load_dotenv

load_dotenv()


DATABASE_URL=os.environ["DATABASE_URL"]
DATABASE_PORT=os.environ["DATABASE_PORT"]
DATABASE_USER=os.environ["DATABASE_USER"]
DATABASE_PASSWORD=os.environ["DATABASE_PASSWORD"]
DATABASE_DATABASE=os.environ["DATABASE_DATABASE"]

OLLAMA_URL=os.environ["OLLAMA_URL"]
OLLAMA_PORT=os.environ["OLLAMA_PORT"]
OLLAMA_MODEL='gemma3:1b'



def parse_one_event(event_lines):
    """
    Takes all the lines for a single event.
    Parses it to get the fields needed.
    Returns all the fields as a dictionary/json.
    """

    def get_description(event_lines):
        start = [i for (i,line) in enumerate(event_lines) if line.startswith("DESCRIPTION:")][0]
        end = start+1
        while event_lines[end].startswith(" "):
            end += 1
        all_lines = "".join([l.strip("\n") for l in event_lines[start:end]])

        return all_lines


    title = [l for l in event_lines if l.startswith("SUMMARY:")][0].split(":")[1]

    url_line_index = [i for (i,line) in enumerate(event_lines) if line.startswith("URL;VALUE=URI:")][0]

    if event_lines[url_line_index+1].startswith(" "):
        url = (event_lines[url_line_index] + event_lines[url_line_index+1]).strip("URL;VALUE=URI:").replace(" ","")
    else:
        url = event_lines[url_line_index].strip("URL;VALUE=URI:").replace(" ","")
    meetup_type = "meetup"
    abstract = get_description(event_lines)
    location = get_location(abstract)

    dates = [l for l in event_lines if l.startswith("DTSTART;TZID=Indian/Mauritius:")][0].split(":")[1].split("T")[0]
    dates = datetime.strptime(dates, '%Y%m%d')

    return {
        "title": title,
        "url": url,
        "type": meetup_type,
        "location": location,
        "abstract": "",
        "date": dates
    }


def get_all_events(all_lines):
    """
    Takes all the lines from the ical, splits the lines into blocks (one block for each event).
    Then just returns a 2d array. Each element corresponds to one event.
    Each element has all the lines from the event's entry in the ical.
    """

    offset = 0
    event_lines = []
    while any(["VEVENT" in l for l in all_lines]):
        start = all_lines.index("BEGIN:VEVENT")
        end = all_lines.index("END:VEVENT")
        offset = end + 1
        event_lines.append(all_lines[start:end])

        all_lines = all_lines[offset::]

    print(len(event_lines))
    return event_lines


def get_location(description):
    """
    Takes the entire unformatted, fairly ugly-looking description and asks the AI slave to get the location for me. Not always accurate on TBC/TBD but whatever.

    """

    content = description + "\n" + "Keep your answer brief and limited to only the answer with no extra words. Only the company name. If it is not specified or TBC (to be confirmed) just say TBD. Where is the meetup taking place?"
    # content = description + "\n" + "Keep your answer brief and limited to only the answer with no extra words. Where is the meetup taking place? If unknown, just say 'TBD'"

    client = Client(
        host=f"{OLLAMA_URL}:{OLLAMA_PORT}",
    )

    response = client.chat(model=OLLAMA_MODEL, messages=[
        {
            'role': 'user',
            'content': content,
        },
    ])

    return response.message.content.strip("\n").strip(".")


def add_to_db(list_of_jsons):
    return NotImplementedError


def get_all_jsons(url):
    """
    Fetches the URL for the ical
    Uses get_all_events to get all the lines
    Uses parse_one_event on each event
    Adds jsons to list
    Returns list
    """

    response = requests.get(url)
    content = response.content

    with open("ical.vcs", "wb+") as filehandle:
        filehandle.write(content)

    with open("ical.vcs", "r") as filehandle:
        lines = [l.strip("\n") for l in filehandle.readlines()]

    offset = 0
    all_event_str = get_all_events(lines)
    all_event_json = []
    for event in all_event_str:
        all_event_json.append(parse_one_event(event))

    pprint(all_event_json)
    return all_event_json


def main():
    with open("communities.json", "r") as f:
        communities = json.load(f)
    for community in communities:
        get_all_jsons(community["url"])

if __name__ == "__main__":
    main()
