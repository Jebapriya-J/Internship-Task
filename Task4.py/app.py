import os
import json
import pdfplumber
import re
from datetime import datetime
from flask import Flask, request, jsonify

# ------------------ Load Config ------------------
CONFIG_FILE = "config/config.json"

with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

UPLOAD_DIR = config["upload_directory"]
OUTPUT_DIR = config.get("output_directory", "output")
LOG_DIR = config.get("log_directory", "logs")
ICD_PATTERN = config.get("icd_pattern", r"[A-Z][0-9][0-9](?:\.[0-9A-Z]{1,4})?")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# ------------------ Logging ------------------
def log(message: str):
    logfile = os.path.join(LOG_DIR, "app.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

# ------------------ Extract ICD Codes & Words ------------------
def extract_icd_codes(pdf_path: str):
    try:
        results = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text(layout=True) or ""
                codes = re.findall(ICD_PATTERN, text)

                # Extract all words with coordinates
                words_with_coordinates = []
                for word in page.extract_words():
                    words_with_coordinates.append({
                        "text": word["text"],
                        "x0": word["x0"],     # left
                        "top": word["top"],   # top
                        "x1": word["x1"],     # right
                        "bottom": word["bottom"]  # bottom
                    })

                results.append({
                    "page": page.page_number,
                    "extracted_codes": list(set(codes)),
                    "text_sample": text[:150],
                    "words_with_coordinates": words_with_coordinates
                })
        log(f"ICD and word extraction complete: {pdf_path}")
        return results
    except Exception as e:
        log(f"ICD extraction failed: {e}")
        raise

# ------------------ Flask App ------------------
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "<h1>Flask ICD Extraction App</h1><p>Use POST /extract with JSON body containing 'filename'.</p>"

@app.route("/extract", methods=["POST"])
def extract():
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "JSON body required"}), 400

        filename = data.get("filename")
        if not filename or not filename.lower().endswith(".pdf"):
            return jsonify({"status": "error", "message": "Please provide a valid PDF filename"}), 400

        pdf_path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.isfile(pdf_path):
            return jsonify({"status": "error", "message": f"File not found in '{UPLOAD_DIR}': {filename}"}), 400

        # Extract ICD codes and words
        output = extract_icd_codes(pdf_path)

        # Save output JSON
        output_file = os.path.join(OUTPUT_DIR, f"{os.path.splitext(filename)[0]}_output.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=4)

        return jsonify({"status": "success", "output_file": output_file, "data": output})

    except Exception as e:
        log(f"API Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ------------------ Run App ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5467)



