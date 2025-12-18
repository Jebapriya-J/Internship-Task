from flask import Flask, request, jsonify, send_file
import os
import shutil
import logging
import warnings
from pathlib import Path
import ocrmypdf
import pikepdf
 
warnings.filterwarnings("ignore")
 
# ------------------------ Config ------------------------
app = Flask(__name__)
 
UPLOAD_DIR = Path("input")
OUTPUT_DIR = Path("output")
LOG_DIR = Path("logs")
 
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
ocrmypdf.configure_logging(verbosity=0)
ROTATE_THRESHOLD = 5.0
OCR_JOBS = 4
 
# ------------------------------------ Logging ---------------------------
logging.basicConfig(
    filename=LOG_DIR / "app.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(funcName)s | Line %(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logging.getLogger().setLevel(logging.INFO)
 
logging.getLogger("werkzeug").propagate = False
logging.getLogger("ocrmypdf").setLevel(logging.INFO)
logging.getLogger("pikepdf").setLevel(logging.ERROR)
logging.getLogger("pdfminer").setLevel(logging.ERROR)
logging.getLogger("PIL").setLevel(logging.ERROR)
logging.getLogger("ghostscript").setLevel(logging.ERROR)
logging.getLogger("tesseract").setLevel(logging.ERROR)
 
# ---------------------------- Validation -----------------
def validate_file(file):
    try:
        if not file:
            raise ValueError("No file uploaded")
        if not file.filename.lower().endswith(".pdf"):
            raise ValueError("Only PDF files allowed")
        return True
    except Exception as e:
        logging.error(f"Validation failed: {e}")
        return False
 
# ------------------------------ Save file -------------------------
def save_uploaded_file(file, path):
    file.save(path)
    logging.info(f"File saved: {path}")
 
# ---------------------------------- OCR -----------------------------
def is_signed_pdf(pdf_path):
    try:
        with pikepdf.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                if "/Annots" in page:
                    annots = page["/Annots"]
                    for annot in annots:
                        obj = annot.get_object()
                        if obj.get("/FT") == "/Sig":
                            return True
        return False
    except Exception as e:
        logging.warning(f"Signature check failed: {e}")
        return False
 
# ------------------- OCR -------------------
def process_pdf(input_pdf, output_pdf):
    logging.info(f"Processing started: {input_pdf}")
    print(f"OCR Process Started")
 
    if not os.path.exists(input_pdf):
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")
 
    signed = is_signed_pdf(input_pdf)
    logging.info(f"PDF is digitally signed: {signed}")
 
    try:
        if signed:
            logging.info("Signed PDF detected. Skipping OCR.")
            shutil.copy(input_pdf, output_pdf)
            return "signed_pdf"
 
        # Normal OCR processing
        ocrmypdf.ocr(
            input_pdf,
            output_pdf,
            language="eng",
            force_ocr=True,
            skip_text=False,
            rotate_pages=True,
            rotate_pages_threshold=ROTATE_THRESHOLD,
            deskew=True,
            optimize=0,
            jobs=OCR_JOBS,
            redo_ocr=False,
            oversample=300,
            progress_bar=False,
            verbose=0,
        )
        logging.info(f"OCR completed: {output_pdf}")
        print(f"OCR process completed.")
        return "ocr_applied"
 
    except ocrmypdf.exceptions.PriorOcrFoundError:
        logging.warning("OCR already exists, copying input to output")
        os.replace(input_pdf, output_pdf)
        return "already_ocr"
 
    except Exception as e:
        logging.error(f"OCR failed: {e}")
        raise
 
# ------------------------------ Flask ---------------------------
@app.route("/ocr", methods=["POST"])
def ocr_pdf():
    file = request.files.get("file")
 
    if not validate_file(file):
        return jsonify({"status": "error", "message": "Invalid PDF"}), 400
 
    input_path = UPLOAD_DIR / file.filename
    output_path = OUTPUT_DIR / f"ocr_{file.filename}"
 
    try:
        logging.info(f"Received file: {file.filename}")
        save_uploaded_file(file, input_path)
        result = process_pdf(input_path, output_path)
 
        return send_file(
            output_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=output_path.name
        )
 
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
 
if __name__ == "__main__":
    app.run(host="172.17.200.196", port=9890)