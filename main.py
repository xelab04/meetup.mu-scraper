import requests
from pprint import pprint
from datetime import datetime
from ollama import Client
import json
import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()


DATABASE_URL=os.environ["DATABASE_URL"]
DATABASE_PORT=os.environ["DATABASE_PORT"]
DATABASE_USER=os.environ["DATABASE_USER"]
DATABASE_PASSWORD=os.environ["DATABASE_PASSWORD"]
DATABASE_DATABASE=os.environ["DATABASE_DATABASE"]

OLLAMA_URL=os.environ["OLLAMA_URL"]
OLLAMA_PORT=os.environ["OLLAMA_PORT"]
OLLAMA_MODEL='gemma3:1b'

COMMUNITY = os.environ["COMMUNITY"]


def parse_one_event(event_lines, name):
    """
    Takes all the lines for a single event.
    Parses it to get the fields needed.
    Returns all the fields as a dictionary/json.

    name = name of community
    """

    def get_description(event_lines):
        # get the line where description starts
        start = [i for (i,line) in enumerate(event_lines) if line.startswith("DESCRIPTION:")][0]
        end = start+1
        # all description lines will be indented after
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
        "id": f"{name}-{url.strip('/').split('/')[-1]}",
        "community": name,
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
    try:
        response = client.chat(model=OLLAMA_MODEL, messages=[
            {
                'role': 'user',
                'content': content,
            },
        ])
    except:
        return None

    return response.message.content.strip("\n").strip(".")


def add_to_db(list_of_jsons):
    DB_CONFIG = {
        "host": DATABASE_URL,
        "port": DATABASE_PORT,
        "user": DATABASE_USER,
        "password": DATABASE_PASSWORD,
        "database": DATABASE_DATABASE
    }

    # Connect to MySQL
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    for event in list_of_jsons:
        # pprint(event)
        cursor.execute("DELETE FROM meetups WHERE registration = %s", (event["url"],))

        # Insert new entry
        print(f"Inserting event: {event['title']}")
        cursor.execute('''
            INSERT INTO meetups (community, title, registration, type, location, abstract, date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (event["community"], event["title"], event["url"], event["type"], event["location"], event["abstract"], event["date"]))

    conn.commit()
    conn.close()


def get_all_jsons(url, name):
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

    all_event_str = get_all_events(lines)
    all_event_json = []
    for event in all_event_str:
        all_event_json.append(parse_one_event(event, name))

    pprint(all_event_json)
    return all_event_json


def frontend_mu():
    # AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    url = "https://raw.githubusercontent.com/frontendmu/frontend.mu/main/packages/frontendmu-data/data/meetups-raw.json"
    response = requests.get(url)
    data = response.json()
    # Yay, we now have 260kB of JSON.
    # I shall scream.

    newjsons = []
    for event in data:
        # where event is a collection of json mess for one event
        if event["accepting_rsvp"] == False:
            # not accepting rsvp = i don't care.
            # maybe delete if already there?
            # idfk
            continue
        new_event_json = {
            "id": f"frontendmu-{event['id']}",
            "community": "frontendmu",
            "title": "FrontendMU " + event["title"],
            "url": f"https://frontend.mu/meetup/{event['id']}",
            "type": "meetup",
            "location": event['Venue'],
            "abstract": "",
            "date": datetime.strptime(event['Date'], '%Y-%m-%d')
        }

        newjsons.append(new_event_json)

        if event["id"] == 60:
            pprint(new_event_json)
    print(len(newjsons))
    return newjsons


def cnmu():
    # hehe i like this
    url = "https://cloudnativemauritius.com/api/meetups"
    response = requests.get(url)
    data = response.json()
    for record in data:
        record["id"] = f"cnmu-{record['id']}"
    print(data)

    return data

def main():
    if COMMUNITY == "cnmu":
        cnmu_events = cnmu()
        add_to_db(cnmu_events)
        return 0

    if COMMUNITY == "frontendmu":
        frontend_events = frontend_mu()
        add_to_db(frontend_events)
        return 0

    if COMMUNITY == "MEETUPCOM":
        with open("communities.json", "r") as f:
            communities = json.load(f)
        for community in communities:
            all_event_json = get_all_jsons(community["url"], community["name"])
            add_to_db(all_event_json)
    else:
        with open("newcommunities.json", "r") as f:
            communities = json.load(f)
        all_event_json = get_all_jsons(COMMUNITY, communities[COMMUNITY])
        add_to_db(all_event_json)

if __name__ == "__main__":
    main()
