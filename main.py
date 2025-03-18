url = "https://www.meetup.com/mauritiussoftwarecraftsmanshipcommunity/events/ical/"

import requests
from pprint import pprint
from datetime import datetime
from ollama import Client

def parse_one_event(event_lines):
    def get_description(event_lines):
        start = [i for (i,line) in enumerate(event_lines) if line.startswith("DESCRIPTION:")][0]
        end = start+1
        while event_lines[end].startswith(" "):
            end += 1
        all_lines = "".join([l.strip("\n") for l in event_lines[start:end]])

        return all_lines


    title = [l for l in event_lines if l.startswith("SUMMARY:")][0].split(":")[1]

    url_line_index = [i for (i,line) in enumerate(event_lines) if line.startswith("URL;VALUE=URI:")][0]
    url = (event_lines[url_line_index] + event_lines[url_line_index+1]).strip("URL;VALUE=URI:").replace(" ","")
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
    content = description + "\n" + "Keep your answer brief and limited to only the answer with no extra words. Where is the meetup taking place? If unknown, just say 'TBD'"

    client = Client(
        host='http://localhost:11434',
    )

    response = client.chat(model='gemma3:1b', messages=[
        {
            'role': 'user',
            'content': content,
        },
    ])

    return response.message.content.strip("\n").strip(".")


def main():
    """
    response = requests.get(url)
    content = response.content

    with open("ical.vcs", "wb+") as filehandle:
        filehandle.write(content)
    """

    with open("ical.vcs", "r") as filehandle:
        lines = [l.strip("\n") for l in filehandle.readlines()]

    offset = 0
    all_events = get_all_events(lines)
    for event in all_events:
        pprint(parse_one_event(event))
    


if __name__ == "__main__":
    main()

