import job
from flask import Flask
import os
import sys
import time
from pprint import pprint

app = Flask(__name__)

try:
    DATABASE_URL=os.environ["DATABASE_URL"]
    DATABASE_PORT=os.environ["DATABASE_PORT"]
    DATABASE_USER=os.environ["DATABASE_USER"]
    DATABASE_PASSWORD=os.environ["DATABASE_PASSWORD"]
    DATABASE_DATABASE=os.environ["DATABASE_DATABASE"]

    OLLAMA_URL=os.environ["OLLAMA_URL"]
    OLLAMA_PORT=os.environ["OLLAMA_PORT"]
    OLLAMA_MODEL='gemma3:1b'

    COMMUNITY = os.environ["COMMUNITY"]
except KeyError:
    print("Missing env vars")
    time.sleep(5)
    sys.exit(1)

@app.route('/frontend', methods=['POST'])
def frontend():
    frontend_events = job.frontendmu()
    pprint(frontend_events)
    job.add_to_db(frontend_events)
    job.delete_frontendmu()

@app.route('/cloudnativemu', methods=['POST'])
def cloudnativemu():
    cnmu_events = job.cnmu()
    pprint(cnmu_events)
    job.add_to_db(cnmu_events)
