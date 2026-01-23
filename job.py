import requests
import icalendar
import mysql.connector
from dotenv import load_dotenv
from location import get_location
import os
import sys
import json
import time
from pprint import pprint
from datetime import datetime

load_dotenv()

try:
    DATABASE_URL=os.environ["DATABASE_URL"]
    DATABASE_PORT=os.environ["DATABASE_PORT"]
    DATABASE_USER=os.environ["DATABASE_USER"]
    DATABASE_PASSWORD=os.environ["DATABASE_PASSWORD"]
    DATABASE_DATABASE=os.environ["DATABASE_DATABASE"]

    OLLAMA_URL=os.environ["OLLAMA_URL"]
    OLLAMA_PORT=os.environ["OLLAMA_PORT"]
    # OLLAMA_MODEL='gemma3:1b'
    OLLAMA_MODEL=os.environ["OLLAMA_MODEL"]

    COMMUNITY = os.environ["COMMUNITY"]
except KeyError:
    print("Missing env vars")
    time.sleep(5)
    sys.exit(1)

class MEETUP:
    def __init__(self, id, community, title, registration, type, location, abstract, date):
        self.id = id
        self.community = community
        self.title = title
        self.registration = registration
        self.type = type
        self.location = location
        self.abstract = abstract
        self.date = date

    def __str__(self):
        dict = {
            "id": self.id,
            "community": self.community,
            "title": self.title,
            "registration": self.registration,
            "type": self.type,
            "location": self.location,
            "abstract": self.abstract,
            "date": self.date.strftime('%Y-%m-%d')
        }
        return json.dumps(dict, indent=4)

    def __repr__(self):
            return self.__str__()

def get_db_cursor():
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

    return conn, cursor

def frontendmu() -> list[MEETUP]:
    url = "https://raw.githubusercontent.com/frontendmu/frontend.mu/main/packages/frontendmu-data/data/meetups-raw.json"
    response = requests.get(url)
    big_frontend_json = response.json()

    all_meetups = []

    for event in big_frontend_json:
        event_details = MEETUP(
            id=f"frontendmu-{event['id']}",
            community="frontendmu",
            title="FrontendMU " + event["title"],
            registration=f"https://frontend.mu/meetup/{event['id']}",
            type="meetup",
            location=event['Venue'],
            abstract="",
            date=datetime.strptime(event['Date'], '%Y-%m-%d')
        )

        all_meetups.append(event_details)

    return all_meetups

def delete_frontendmu() -> int|None:
    url = "https://raw.githubusercontent.com/frontendmu/frontend.mu/main/packages/frontendmu-data/data/meetups-raw.json"
    response = requests.get(url)
    big_frontend_json = response.json()


    list_of_ids = [f"frontendmu-{event['id']}" for event in big_frontend_json]

    conn, cursor = get_db_cursor()
    placeholders = ','.join(['%s'] * len(list_of_ids))

    print(f"Deleting events: {list_of_ids}")

    query = f"DELETE FROM meetups WHERE community='frontendmu' AND meetup_id NOT IN ({placeholders})"
    cursor.execute(query, list_of_ids)

    # delete all frontendmu events from db where id is not in the list_of_existing_ids
    # cursor.execute("DELETE FROM meetups WHERE community='frontendmu' AND meetup_id NOT IN :ids", {"ids": list_of_ids})

    conn.commit()
    conn.close()

def cnmu() -> list[MEETUP]:
    url = "https://cloudnativemauritius.com/api/meetups"
    response = requests.get(url)
    data = response.json()

    all_meetups = []

    for record in data:
        new_meetup = MEETUP(
            id=f"cnmu-{record['id']}",
            community=record["community"],
            title=record["title"],
            registration=record["url"],
            type=record["type"],
            location=record["location"],
            abstract=record["abstract"],
            date=datetime.strptime(record["date"], '%Y-%m-%d')
        )
        all_meetups.append(new_meetup)

    return all_meetups

def get_all_events(community) -> list[MEETUP]:
    all_events = []

    with open('ical.vcs', 'rb') as f:
        calendar = icalendar.Calendar.from_ical(f.read())

    for component in calendar.walk():
        if component.name == "VEVENT":

            ai_location = get_location(component.get('description'))

            all_events.append(MEETUP(
                id=component.get('uid'),
                community=community,
                title=component.get('summary'),
                registration=component.get('url'),
                type="meetup",
                location=ai_location,
                # abstract=component.get('description'),
                abstract=None,
                date=component.get('dtstart').dt
            ))
    return all_events

def get_ical(url) -> None:
    response = requests.get(url)
    content = response.content

    with open("ical.vcs", "wb+") as filehandle:
        filehandle.write(content)

def add_to_db(list_of_meetups: list[MEETUP]) -> None:
    conn, cursor = get_db_cursor()

    for meetup in list_of_meetups:
        cursor.execute("SELECT COUNT(meetup_id) FROM meetups WHERE meetup_id = %s", (meetup.id, ))
        result = cursor.fetchone()

        # if the event is already present, just update it
        if result[0] != 0:
            cursor.execute("UPDATE meetups SET community=%s, title=%s, registration=%s, type=%s, location=%s, abstract=%s, date=%s WHERE meetup_id=%s",
                (meetup.community, meetup.title, meetup.registration, meetup.type, meetup.location, meetup.abstract, meetup.date, meetup.id))
        # if the event is completely new, create new entry
        else:
            cursor.execute("INSERT INTO meetups (meetup_id, community, title, registration, type, location, abstract, date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (meetup.id, meetup.community, meetup.title, meetup.registration, meetup.type, meetup.location, meetup.abstract, meetup.date))

    conn.commit()
    conn.close()

def main():
    if COMMUNITY == "cnmu":
        cnmu_events = cnmu()
        pprint(cnmu_events)
        add_to_db(cnmu_events)
        return 0

    if COMMUNITY == "frontendmu":
        frontend_events = frontendmu()
        pprint(frontend_events)
        add_to_db(frontend_events)
        delete_frontendmu()
        return 0

    # Get all events for all meetupcom communities
    if COMMUNITY == "MEETUPCOM":
        with open("communities.json", "r") as f:
            communities = json.load(f)

        for community in communities:
            get_ical(community["url"])
            all_events_for_community = get_all_events(community["name"])
            add_to_db(all_events_for_community)

            print(community["name"])
            pprint(all_events_for_community)
            print()


    # If we are getting for a single meetupcom community, which we never do
    else:
        with open("newcommunities.json", "r") as f:
            communities = json.load(f)

        get_ical(communities[COMMUNITY])
        all_event_json = get_all_events(COMMUNITY)
        add_to_db(all_event_json)

if __name__ == "__main__":
    main()
