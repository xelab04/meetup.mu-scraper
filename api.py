import job
from flask import Flask, jsonify
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
    OLLAMA_MODEL=os.environ["OLLAMA_MODEL"]

except KeyError:
    print("Missing env vars")
    time.sleep(5)
    sys.exit(1)

@app.route('/frontend', methods=['POST'])
def frontend():
    try:
        frontend_events = job.frontendmu()
        pprint(frontend_events)
        job.add_to_db(frontend_events)
        job.delete_frontendmu()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": str(e)}), 500

@app.route('/cloudnativemu', methods=['POST'])
def cloudnativemu():
    cnmu_events = job.cnmu()
    pprint(cnmu_events)
    job.add_to_db(cnmu_events)

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
