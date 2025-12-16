import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from flask import Flask, request, send_file, jsonify
from pypdf import PdfReader, PdfWriter

# ------------------ CONFIG ------------------
UPLOAD_DIR = "input"
OUTPUT_DIR = "output"
LOG_DIR = "logs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

ROTATED_PDF = os.path.join(OUTPUT_DIR, "rotated.pdf")
FINAL_PDF = os.path.join(OUTPUT_DIR, "output.pdf")

# ------------------ Logging ------------------
def log(message: str):
    logfile = os.path.join(LOG_DIR, "app.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

# ------------------ PDF FUNCTIONS ------------------
def validate(file) -> str:
    ext = os.path.splitext(file.filename)[1].lower()
    if ext != ".pdf":
        raise ValueError("Only PDF files are allowed")
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(file_path)
    return file_path

def rotate(input_pdf: str, output_pdf: str, angle=90):
    reader = PdfReader(input_pdf)
    if not reader.pages:
        raise RuntimeError("PDF has no pages")
    writer = PdfWriter()
    for page in reader.pages:
        page.rotate(angle)
        writer.add_page(page)
    with open(output_pdf, "wb") as f:
        writer.write(f)

def ocr_pdf(input_pdf: str, output_pdf: str):
    subprocess.run(["ocrmypdf", "--force-ocr", input_pdf, output_pdf], check=True)

# ------------------ Flask App ------------------
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "<h1>Flask PDF Processing App</h1><p>Use POST /process-pdf with form-data containing 'file'.</p>"

@app.route("/process-pdf/", methods=["POST"])
def process_pdf_route():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file provided"}), 400
    file = request.files["file"]
    try:
        input_pdf = validate(file)
        log(f"File validated: {input_pdf}")

        # Use a temporary path for rotation
        temp_rotated_pdf = os.path.join(OUTPUT_DIR, "temp_rotated.pdf")
        rotate(input_pdf, temp_rotated_pdf)
        log(f"PDF rotated (temporary): {temp_rotated_pdf}")

        # OCR to final PDF
        ocr_pdf(temp_rotated_pdf, FINAL_PDF)
        log(f"OCR applied: {FINAL_PDF}")

        # Clean up temporary rotated PDF
        if os.path.exists(temp_rotated_pdf):
            os.remove(temp_rotated_pdf)

        return send_file(
            FINAL_PDF,
            as_attachment=True,
            download_name="processed.pdf",
            mimetype="application/pdf"
        )

    except subprocess.CalledProcessError:
        log("OCR processing failed")
        return jsonify({"status": "error", "message": "OCR processing failed"}), 500

    except ValueError as ve:
        log(f"Validation error: {ve}")
        return jsonify({"status": "error", "message": str(ve)}), 400

    except Exception as e:
        log(f"Processing error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ------------------ Run App ------------------
if __name__ == "__main__":
    host = "0.0.0.0"
    port = 9880
    app.run(host=host, port=port, debug=True)
