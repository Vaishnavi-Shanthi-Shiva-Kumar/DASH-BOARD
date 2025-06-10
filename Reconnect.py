from flask import Flask, send_from_directory, request, jsonify
import csv
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import threading
from datetime import datetime
from zoneinfo import ZoneInfo  # Built-in in Python 3.9+


# Initialize the Flask application with static file directories
app = Flask(__name__, static_folder='Assets', static_url_path='/Assets')

# Google Sheets setup using OAuth2 credentials
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("uPLC_sheet").worksheet("Barcode_Data")

# Track barcode values for the current session to avoid duplicates
session_barcodes = set()

# Route for the homepage, serves Index.html from the root directory
@app.route('/')
def home():
    return send_from_directory('.', 'Index.html')

# Route for serving other pages (like external HTML files), maps to /Pages/<filename>
@app.route('/Pages/<path:filename>')
def pages(filename):
    return send_from_directory('Pages', filename)

# Route for serving assets (images, JS, CSS) from the 'Assets' directory
@app.route('/Assets/<path:filename>')
def assets(filename):
    return send_from_directory('Assets', filename)

# Route for handling barcode submissions, accepts POST request
@app.route('/submit-barcode', methods=['POST'])
def submit_barcode():
    data = request.json  # Get the data from the incoming request
    barcode = data.get("barcode", "").strip()  # Extract the barcode and remove extra spaces
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    time = now.strftime("%H:%M:%S")  # Format time as HH:MM:SS
    date = now.strftime("%d-%m-%Y")  # Format date as DD-MM-YYYY

    # Barcode is considered valid if its length is greater than 10 characters
    is_valid = len(barcode) >= 10

    # Check for barcode duplication within the session
    if barcode in session_barcodes:
        return jsonify({
            "success": False,
            "message": "Barcode already scanned in this session."
        })

    # Add the barcode to the session set to prevent future duplicates
    session_barcodes.add(barcode)

    # Save the barcode and timestamp to a local CSV file for record-keeping
    with open("barcodes.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([time, date, barcode])

    # Save to Google Sheets
    new_row = [time, date, barcode]
    sheet.append_row(new_row)

    # Get the last row after the barcode is added (this would be the newly appended row)
    last_row = len(sheet.get_all_values())

    # Apply row color based on barcode validity
    if is_valid:
        # Light Green (#e5ffe5) if the barcode is valid
        sheet.format(f"A{last_row}:C{last_row}", {'backgroundColor': {'red': 0.9, 'green': 1, 'blue': 0.9}})
    else:
        # Light Red (#ffcccc) if the barcode is invalid
        sheet.format(f"A{last_row}:C{last_row}", {'backgroundColor': {'red': 1, 'green': 0.8, 'blue': 0.8}})

    # Send response to frontend
    return jsonify({
        "success": True,
        "barcode": barcode,
        "valid": is_valid,
        "time": time,
        "date": date
    })

# Route to get all barcode data with colored values in the frontend
@app.route('/get-barcodes', methods=['GET'])
def get_barcodes():
    # Fetch all barcode data from the sheet
    values = sheet.get_all_values()
    barcodes = []

    # Color logic for barcodes (green for valid, red for invalid)
    for row in values:
        barcode = row[2]
        is_valid = len(barcode) > 10
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

# Entry point for running the Flask application
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Get the port from environment or default to 5000
    app.run(debug=False, host='0.0.0.0', port=port)  # Run the Flask app, accessible on all IPs
