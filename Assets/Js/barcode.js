let totalCount = 0;
let scannedCount = 0;

function startScanning() {
    const countInput = document.getElementById("itemCount");
    const barcodeInput = document.getElementById("barcode-input");
    const scanStatus = document.getElementById("scan-status");

    totalCount = parseInt(countInput.value);
    scannedCount = 0;

    if (!totalCount || totalCount < 1) {
        alert("❗ Please enter a valid item count.");
        return;
    }

    // Enable input & focus
    barcodeInput.disabled = false;
    barcodeInput.focus();
    scanStatus.textContent = `✅ Ready to scan 1 of ${totalCount}`;
}

function handleBarcodeInput(event) {
    if (event.key === "Enter") {
        const barcode = event.target.value.trim();
        event.target.value = "";

        if (!barcode) return;

        fetch("/submit-barcode", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ barcode })
        })
        .then(res => res.json())
        .then(res => {
            if (res.success) {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td>${res.time}</td>
                    <td>${res.date}</td>
                    <td style="background-color: ${res.valid ? 'lightgreen' : 'salmon'}">${res.barcode}</td>
                `;
                document.getElementById("barcode-body").appendChild(tr);

                if (res.valid) {
                    scannedCount++;
                    document.getElementById("scan-status").textContent = `✅ Scanned ${scannedCount} of ${totalCount}`;
                } else {
                    document.getElementById("scan-status").textContent = `❌ Invalid barcode (length < 10)`;
                }

                if (scannedCount >= totalCount) {
                    document.getElementById("barcode-input").disabled = true;
                    document.getElementById("scan-status").textContent = "✅ Scanning complete!";
                }
            } else {
                alert("❌ Failed to save barcode: " + (res.error || "Unknown Error"));
            }
        })
        .catch(err => {
            console.error("Barcode error:", err);
            alert("⚠️ Error communicating with server.");
        });
    }
}
