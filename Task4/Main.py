from fastapi import FastAPI, File, UploadFile, BackgroundTasks
import os
import logging
import uvicorn
from pathlib import Path
import shutil
import pdfplumber
import re
import json

# ------------------ CONFIG SETUP ------------------
app = FastAPI()

UPLOAD_DIR = Path("input")
OUTPUT_DIR = Path("output")
LOG_DIR = Path("logs")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "app.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(funcName)s | Line %(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ------------------ ICD REGEX ------------------
# Matches "ICD-10-CM: E11.29, R80.9" or "ICD-9-CM: 250.40, 791.0"
ICD_PATTERN = r"ICD-(?:10|9)-CM:?\s*\[?([A-Z\d]\d{1,2}(?:\.\d+)?(?:\s*,\s*[A-Z\d]\d{1,2}(?:\.\d+)?)*)\]?"

# ------------------ FILE VALIDATION ------------------
def save_pdf_to_disk(file: UploadFile):
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext != ".pdf":
            return None, "Insert valid PDF file"

        file_path = UPLOAD_DIR / file.filename
        with file_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)

        return str(file_path), None
    except Exception as e:
        logger.error(f"Error saving file: {e}", exc_info=True)
        return None, "Internal file save error"

# ------------------ EXTRACT ICD CODES & COORDINATES ------------------
def extract_icd_codes(pdf_path: str):
    results = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                try:
                    page_text = page.extract_text() or ""

                    # Extract all ICD blocks
                    matches = re.findall(ICD_PATTERN, page_text, flags=re.IGNORECASE | re.MULTILINE)

                    # Flatten all codes continuously
                    extracted_codes = []
                    for block in matches:
                        codes = [c.strip() for c in block.replace("\n", " ").split(",") if c.strip()]
                        extracted_codes.extend(codes)

                    # Remove duplicates
                    extracted_codes = list(dict.fromkeys(extracted_codes))  # preserves order

                    # Extract coordinates for each code
                    words = page.extract_words(use_text_flow=True)
                    icd_coordinates = []
                    def normalize(text):
                        return re.sub(r"[^A-Z0-9\.]", "", text.upper())

                    norm_codes = [normalize(c) for c in extracted_codes]

                    for w in words:
                        w_text_norm = normalize(w["text"])
                        if w_text_norm in norm_codes:
                            icd_coordinates.append({
                                "code": w["text"].strip(),
                                "x0": round(w["x0"], 2),
                                "x1": round(w["x1"], 2),
                                "top": round(w["top"], 2),
                                "bottom": round(w["bottom"], 2)
                            })

                    results.append({
                        "page_number": page.page_number,
                        "icd_codes": icd_coordinates,  # all codes continuously with coordinates
                        "text": page_text.replace("\n", " ").strip()
                    })

                except Exception as e:
                    logger.error(f"Page {page.page_number} extraction error: {e}", exc_info=True)
                    results.append({
                        "page_number": page.page_number,
                        "icd_codes": [],
                        "text": "",
                        "error": "Failed to read this page"
                    })

    except Exception as e:
        logger.error(f"PDF processing error: {e}", exc_info=True)
        return []

    return results

# ------------------ BACKGROUND TASK PROCESSOR ------------------
def background_process(pdf_path: str, json_path: str):
    try:
        output_file = Path(json_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        extracted_data = extract_icd_codes(pdf_path)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(extracted_data, f, indent=4)

        logger.info(f"Task completed successfully: {output_file}")

    except Exception as e:
        logger.error(f"Background task failed: {e}", exc_info=True)

# ------------------ FASTAPI UPLOAD ROUTE ------------------
@app.post("/upload-pdf/")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    pdf_path, error = save_pdf_to_disk(file)
    if error:
        return {"status": "error", "message": error}

    output_file = OUTPUT_DIR / f"{Path(pdf_path).stem}.json"
    background_tasks.add_task(background_process, pdf_path, output_file)

    return {
        "status": "queued",
        "message": "Your file is being processed",
        "output_json": str(output_file)
    }

# ------------------ RUN APP ------------------
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8450)
