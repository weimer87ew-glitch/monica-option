# main.py
import json
from flask import Flask, jsonify, render_template_string

STATUS_FILE = "status.json"

app = Flask(__name__)

# Simple HTML status page
HTML = """
<html>
  <head><title>Monica Option - Status</title></head>
  <body>
    <h1>Monica Option (Simulation)</h1>
    <pre>{{status}}</pre>
  </body>
</html>
"""

def read_status():
    try:
        with open(STATUS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"alive": False, "message": "No status yet."}

@app.route("/")
def index():
    status = read_status()
    return render_template_string(HTML, status=json.dumps(status, indent=2))

@app.route("/status")
def status_api():
    return jsonify(read_status())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
