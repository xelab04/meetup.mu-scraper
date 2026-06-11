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

def get_env_var(env_var_name: str) -> str:
    try:
        return os.environ[env_var_name]
    except KeyError:
        print(f"job.py: {env_var_name} not found")
        time.sleep(5)
        sys.exit()

COMMUNITY=get_env_var("COMMUNITY")
DATABASE_URL=get_env_var("DATABASE_URL")
DATABASE_PORT=get_env_var("DATABASE_PORT")
DATABASE_USER=get_env_var("DATABASE_USER")
DATABASE_PASSWORD=get_env_var("DATABASE_PASSWORD")
DATABASE_DATABASE=get_env_var("DATABASE_DATABASE")


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
    url = "https://coders.mu/api/public/v1/meetups"
    response = requests.get(url)
    big_frontend_json = response.json()

    all_meetups = []

    for event in big_frontend_json:
        event_details = MEETUP(
            id=f"frontendmu-{event['id']}",
            community="frontendmu",
            title="FrontendMU " + event["title"],
            registration=f"https://frontend.mu/meetup/{event['slug']}",
            type="meetup",
            location=event['venue'],
            abstract="",
            date=datetime.strptime(event['date'], '%Y-%m-%d')
        )

        all_meetups.append(event_details)

    return all_meetups

def delete_frontendmu() -> int|None:
    url = "https://coders.mu/api/public/v1/meetups"
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

def pymug() -> list[MEETUP]:
    url = "https://www.pymug.com/events.json"
    response = requests.get(url)
    json = response.json()

    all_meetups = []

    for key in json:
        event = json[key]

        try:
            date = datetime.strptime(event["date"], '%B %d, %Y')
        except ValueError:
            try:
                date = datetime.strptime(event["date"], '%B, %Y')
            except ValueError:
                date = datetime(year=1990, month=1, day=1)

        new_meetup = MEETUP(
            id = key,
            community = "pymug",
            title = event["title"],
            registration = event["register"],
            type = "meetup",
            location = event["venue"],
            abstract = None,
            date = date
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

            pprint(all_events[-1])

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
    if COMMUNITY == "notMEETUPCOM":
        pymug_events = pymug()
        pprint(pymug_events)
        add_to_db(pymug_events)
        # delete_pymug()

        cnmu_events = cnmu()
        pprint(cnmu_events)
        add_to_db(cnmu_events)
        # delete cnmu

        frontend_events = frontendmu()
        pprint(frontend_events)
        add_to_db(frontend_events)
        delete_frontendmu()

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

if __name__ == "__main__":
    main()
