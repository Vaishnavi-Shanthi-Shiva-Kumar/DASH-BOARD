from flask import Flask, send_from_directory, request, jsonify
import csv
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import threading
import pytz

app = Flask(__name__, static_folder='Assets', static_url_path='/Assets')

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("UPLOAD_WIFI_ESP").worksheet("Barcode Data")

@app.route('/')
def home():
    return send_from_directory('.', 'Index.html')

@app.route('/Pages/<path:filename>')
def pages(filename):
    return send_from_directory('Pages', filename)

@app.route('/Assets/<path:filename>')
def assets(filename):
    return send_from_directory('Assets', filename)

# ===== Barcode Submission Endpoint =====
@app.route('/submit-barcode', methods=['POST'])
def submit_barcode():
    data = request.json
    barcode = data.get("barcode", "").strip()

    # Use Indian timezone for date and time
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz)
    time = now.strftime("%H:%M:%S")   # Time in 24-hour format
    date = now.strftime("%d-%m-%Y")   # Date in DD-MM-YYYY format

    # Barcode is valid if exactly 10 characters
    is_valid = len(barcode) >= 10

    # Append to local CSV file
    with open("barcodes.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([time, date, barcode])

    try:
        # Append to Google Sheet
        sheet.append_row([time, date, barcode])

        # Send success response to frontend
        return jsonify({
            "success": True,
            "barcode": barcode,
            "valid": is_valid,
            "time": time,
            "date": date
        })

    except Exception as e:
        # If there's a failure writing to the sheet
        print(f"Google Sheets error: {e}")
        return jsonify({"success": False, "message": "Failed to save to Google Sheets"})

# ===== Sheet lock to prevent simultaneous access errors =====
sheet_lock = threading.Lock()

# ===== GPIO Switch column mapping in the Google Sheet =====
switch_columns = {
    "GPIO1": 8,
    "GPIO2": 9,
    "GPIO3": 10,
    "GPIO4": 11
}

# ===== Get the current state of all switches from the sheet =====
@app.route('/get-switch-states', methods=['GET'])
def get_switch_states():
    with sheet_lock:
        try:
            values = sheet.get_all_values()
            if len(values) < 3:
                # If sheet is mostly empty, return all Low
                return jsonify({"success": True, "states": {s: "Low" for s in switch_columns.keys()}})

            last_row = values[-1]  # Last row in sheet
            states = {}

            # Extract GPIO states from columns H–K (8–11)
            for switch_name, col in switch_columns.items():
                val = last_row[col - 1] if len(last_row) >= col else "Low"
                states[switch_name] = val if val in ["High", "Low"] else "Low"

            return jsonify({"success": True, "states": states})

        except Exception as e:
            print(f"Switch read error: {e}")
            return jsonify({"success": False, "message": "Failed to get switch states"}), 500

# ===== Run the Flask app =====
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
