from flask import Flask, send_from_directory, request, jsonify
import csv
from datetime import datetime
from zoneinfo import ZoneInfo  # Requires Python 3.9+
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import threading

# Flask app setup
app = Flask(__name__, static_folder='Assets', static_url_path='/Assets')

# Google Sheets API setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("UPLOAD_WIFI_ESP").worksheet("Barcode Data")

# Session barcode tracking (prevent duplicates during a session)
session_barcodes = set()

# Flask Routes

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
    global session_barcodes

    data = request.json
    barcode = data.get("barcode", "").strip()

    # System time with Indian timezone
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    time = now.strftime("%H:%M:%S")
    date = now.strftime("%d-%m-%Y")

    # Barcode validity: must be exactly 10 characters
    is_valid = len(barcode) >= 10

    # Check for barcode duplication within the session
    if barcode in session_barcodes:
        return jsonify({
            "success": False,
            "message": "Barcode already scanned in this session."
        })

    # Add the barcode to session to prevent future duplicates
    session_barcodes.add(barcode)

    # Save to local CSV
    with open("barcodes.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([time, date, barcode])

    # Save to Google Sheets
    new_row = [time, date, barcode]
    sheet.append_row(new_row)

    # Get the last row index
    last_row = len(sheet.get_all_values())

    # Color-code the row based on validity
    if is_valid:
        sheet.format(f"A{last_row}:C{last_row}", {
            'backgroundColor': {'red': 0.9, 'green': 1, 'blue': 0.9}  # Light green
        })
    else:
        sheet.format(f"A{last_row}:C{last_row}", {
            'backgroundColor': {'red': 1, 'green': 0.8, 'blue': 0.8}  # Light red
        })

    return jsonify({
        "success": True,
        "barcode": barcode,
        "valid": is_valid,
        "time": time,
        "date": date
    })

@app.route('/get-barcodes', methods=['GET'])
def get_barcodes():
    values = sheet.get_all_values()
    barcodes = []

    for row in values:
        if len(row) < 3:
            continue
        barcode = row[2]
        is_valid = len(barcode) == 10
        color = 'green' if is_valid else 'red'
        barcodes.append({
            'time': row[0],
            'date': row[1],
            'barcode': barcode,
            'color': color
        })

    return jsonify({
        "success": True,
        "barcodes": barcodes
    })

@app.route('/reset-session', methods=['POST'])
def reset_session():
    global session_barcodes
    session_barcodes.clear()
    return jsonify({"success": True, "message": "Session barcodes cleared."})

# Run Flask app
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
