from flask import Flask, send_from_directory, request, jsonify
import csv
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import threading

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

@app.route('/submit-barcode', methods=['POST'])
def submit_barcode():
    data = request.json
    barcode = data.get("barcode", "").strip()
    now = datetime.now()
    time = now.strftime("%H:%M:%S")
    date = now.strftime("%d-%m-%Y")

    # Barcode is valid if it has exactly 10 characters
    is_valid = len(barcode) > 10

    # Save to CSV
    with open("barcodes.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([time, date, barcode])

    # Save to Google Sheets
    sheet.append_row([time, date, barcode])

    # Send response to frontend
    return jsonify({
        "success": True,
        "barcode": barcode,
        "valid": is_valid,
        "time": time,
        "date": date
    })

sheet_lock = threading.Lock()

# Map switch names to Google Sheet column numbers (H=8, I=9, J=10, K=11)
switch_columns = {
    "GPIO1": 8,
    "GPIO2": 9,
    "GPIO3": 10,
    "GPIO4": 11
}

def get_last_row():
    # Get the last row number with data
    return len(sheet.get_all_values())

@app.route('/update-switch', methods=['POST'])
def update_switch():
    data = request.json
    switch_name = data.get("switch")
    state = data.get("state")  # Expected "High" or "Low"
    
    if switch_name not in switch_columns or state not in ["High", "Low"]:
        return jsonify({"success": False, "message": "Invalid switch or state"}), 400
    
    col = switch_columns[switch_name]
    with sheet_lock:
        try:
            last_row = get_last_row()
            if last_row < 3:
                # If sheet has no data rows, append a new row with date/time placeholders and switch state
                now = datetime.now()
                date = now.strftime("%d-%m-%Y")
                time = now.strftime("%H:%M:%S")
                # Make a row with empty cells for all columns, except date/time and this switch column
                row = [""] * (col + 1)
                row[0] = date
                row[1] = time
                row[col - 1] = state  # Adjusting 1-based index (sheet columns are 1-based)
                sheet.append_row(row)
            else:
                # Update the last row's switch column
                sheet.update_cell(last_row, col, state)
        except Exception as e:
            print(f"Error updating switch state in sheet: {e}")
            return jsonify({"success": False, "message": "Google Sheets update failed"}), 500

    return jsonify({"success": True, "message": f"{switch_name} set to {state}"})


@app.route('/get-switch-states', methods=['GET'])
def get_switch_states():
    with sheet_lock:
        try:
            values = sheet.get_all_values()
            if len(values) < 3:
                # No data
                return jsonify({"success": True, "states": {s: "Low" for s in switch_columns.keys()}})
            
            last_row = values[-1]
            # Extract switch states from last row columns
            states = {}
            for switch_name, col in switch_columns.items():
                # col - 1 for zero based index in Python list
                val = last_row[col - 1] if len(last_row) >= col else "Low"
                states[switch_name] = val if val in ["High", "Low"] else "Low"

            return jsonify({"success": True, "states": states})
        except Exception as e:
            print(f"Error fetching switch states: {e}")
            return jsonify({"success": False, "message": "Failed to get switch states"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
