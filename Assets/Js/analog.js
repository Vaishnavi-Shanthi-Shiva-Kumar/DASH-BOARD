const SHEET_ID = "13mpVaEl2tTOTQwgd2WC_l9w4WTs817IjyoJhKplBR3U"; 
const API_KEY = "AIzaSyDqtptaogDoAfx5w0BXAakhkIOG2mK5r_g"; 
 
const WIFI_RANGE = "WifiData";  
const BARCODE_RANGE = "Barcode Data";  

// Function to fetch data from Google Sheets
async function fetchData() {
    try {
        const wifiResponse = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${WIFI_RANGE}?key=${API_KEY}`);
        const barcodeResponse = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${BARCODE_RANGE}?key=${API_KEY}`);

        const wifiData = await wifiResponse.json();
        const barcodeData = await barcodeResponse.json();

        console.log("Fetched WifiData:", wifiData);
        console.log("Fetched BarcodeData:", barcodeData);

        if (wifiData.values && wifiData.values.length > 2) {
            updateTables(wifiData.values, barcodeData.values);
        } else {
            console.error("No sufficient data received from Google Sheets");
        }
    } catch (error) {
        console.error("Error fetching data:", error);
    }
}

// Function to dynamically update tables
function updateTables(wifiData, barcodeData) {
    const rows = wifiData.slice(-50).reverse(); // Load last 50
    const barcodeRows = barcodeData.slice(-45).reverse(); // Last 5 barcode entries

    const analogBody = document.getElementById("analog-body");
    const digitalBody = document.getElementById("digital-body");
    const barcodeBody = document.getElementById("barcode-body");

    // Clear old table content
    analogBody.innerHTML = "";
    digitalBody.innerHTML = "";
    barcodeBody.innerHTML = "";

    // Loop through latest WifiData
    rows.forEach(row => {
        const time = row[0] || "--";
        const date = row[1] || "--";

        // Parse and clean computed value (CH1*CH2/CH3)
        const computedStr = row[6] || "0";
        const computedValue = parseFloat(computedStr.replace(/[^\d.]/g, ""));

        const colorStyle = computedValue > 15 ? 'style="color:red;font-weight:bold;"' : 'style="color:green;font-weight:bold;"';

        // Analog Table
        const analogRow = document.createElement("tr");
        analogRow.innerHTML = `
            <td>${time}</td>
            <td>${date}</td>
            <td>${row[2] || "--"}</td>  <!-- CH_1 -->
            <td>${row[3] || "--"}</td>  <!-- CH_2 -->
            <td>${row[4] || "--"}</td>  <!-- CH_3 -->
            <td>${row[5] || "--"}</td>  <!-- CH_4 -->
            <td ${colorStyle}>${computedStr}</td> <!-- Computed Value -->
        `;
        analogBody.appendChild(analogRow);

        // Digital Table
        const digitalRow = document.createElement("tr");
        digitalRow.innerHTML = `
            <td>${time}</td>
            <td>${date}</td>
            <td><label class="switch"><input type="checkbox" ${row[7] === "HIGH" ? "checked" : ""}><span class="slider"></span></label></td>
            <td><label class="switch"><input type="checkbox" ${row[8] === "HIGH" ? "checked" : ""}><span class="slider"></span></label></td>
            <td><label class="switch"><input type="checkbox" ${row[9] === "HIGH" ? "checked" : ""}><span class="slider"></span></label></td>
            <td><label class="switch"><input type="checkbox" ${row[10] === "HIGH" ? "checked" : ""}><span class="slider"></span></label></td>
        `;
        digitalBody.appendChild(digitalRow);

        // ✅ Attach event listeners to switches
        const switches = digitalRow.querySelectorAll("input[type='checkbox']");
        switches.forEach((sw, index) => {
            sw.addEventListener("change", () => {
                const state = sw.checked ? "HIGH" : "LOW";
                console.log(`GPIO${index + 1} changed to: ${state}`);

                // Find the exact row index in the sheet (you can track this via wifiData if needed)
                const sheetRowIndex = wifiData.length - rows.indexOf(row); // Adjusted to actual row index

                // Determine which column to update: GPIO1 = H = column 8 => A=1, H=8, etc.
                const columnLetter = String.fromCharCode(72 + index); // 72 = "H".charCodeAt(0)

                // Send update to Google Sheets
                updateGPIOStateInSheet(sheetRowIndex, columnLetter, state);
            });
        });
    });

    // Barcode Table with color logic
barcodeRows.forEach(row => {
    const barcodeRow = document.createElement("tr");
    row.forEach((value, index) => {
        const td = document.createElement("td");

        if (index === row.length - 1) { // Assuming barcode is in the last column
            td.innerText = value || "--";
            td.style.color = value && value.length >= 10 ? "green" : "red";
            td.style.fontWeight = "bold";
        } else {
            td.innerText = value || "--";
        }

        barcodeRow.appendChild(td);
    });
    barcodeBody.appendChild(barcodeRow);
});
    
}

async function updateGPIOStateInSheet(rowIndex, columnLetter, state, oauthToken) {
    // Adjust row to match Google Sheets row number (consider headers)
    const sheetRow = rowIndex + 2;  // assuming rowIndex is zero-based data index
  
    const range = `${columnLetter}${sheetRow}`;
    const body = {
      range: range,
      values: [[state]],
    };
  
    try {
      const response = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${range}?valueInputOption=USER_ENTERED`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${oauthToken}`,   // OAuth2 token required here
        },
        body: JSON.stringify(body),
      });
  
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(`Failed to update sheet: ${errData.error.message}`);
      }
      console.log(`Updated ${range} to ${state}`);
    } catch (error) {
      console.error("Error updating GPIO state:", error);
    }
  }
  

// Function to handle tab switching
function showTab(tabName) {
    document.querySelectorAll(".tab-content").forEach(tab => tab.classList.remove("active-content"));
    document.getElementById(tabName).classList.add("active-content");

    document.querySelectorAll(".tab").forEach(tab => tab.classList.remove("active"));
    document.querySelector(`.tab[onclick="showTab('${tabName}')"]`).classList.add("active");
}

// Auto-refresh every 5 seconds
setInterval(fetchData, 5000);
fetchData();
