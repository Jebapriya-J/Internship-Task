import os, ocrmypdf, uvicorn, shutil, logging, warnings
from pathlib import Path
from pypdf import PdfReader
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
warnings.filterwarnings("ignore")
 
# ------------------- Config -------------------
app = FastAPI()
 
UPLOAD_DIR = Path("input")
OUTPUT_DIR = Path("output")
LOG_DIR = Path("logs")
 
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
 
ocrmypdf.configure_logging(verbosity=0)
ROTATE_THRESHOLD = 5.0
OCR_JOBS = 4

# ------------------- Log -------------------
logging.basicConfig(
    filename=LOG_DIR / "app.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(funcName)s | Line %(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)
logging.getLogger("ocrmypdf").setLevel(logging.ERROR) 
 
# ------------------- Validation -------------------
def validate_file(file: UploadFile):
    try:
        if not file:
            raise FileNotFoundError("Upload a valid PDF file")
        elif not file.filename.lower().endswith(".pdf"):
            raise ValueError("Only PDF files are allowed")
        else:
            return True
    except Exception as e:
        logger.error(f"validate_file: {e}")
        return False
 
# ------------------- Check -------------------
def pdf_has_text(pdf_path, pages_to_check=2):
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages[:pages_to_check]:
            text = page.extract_text()
            if text and text.strip():
                return True
        return False
    except Exception as e:
        logger.warning(f"Text check failed: {e}")
        return False
 
def save_uploaded_file(file: UploadFile, path: Path):
    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    logger.info(f"File saved: {path}")
 
# ------------------- OCR -------------------
def process_pdf(input_pdf, output_pdf):
    logger.info(f"Processing started: {input_pdf}")
 
    if not os.path.exists(input_pdf):
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")
 
    has_text = pdf_has_text(input_pdf)
    logger.info(f"PDF contains text: {has_text}")
 
    try:
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
        logger.info(f"Processing completed: {output_pdf}")
 
    except ocrmypdf.exceptions.PriorOcrFoundError:
        logger.warning("OCR already exists, copying input to output")
        os.replace(input_pdf, output_pdf)
 
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise
 
# ------------------- FastAPI-------------------
@app.post("/ocr/")
async def ocr_pdf(file: UploadFile = File(...)):
    input_path = UPLOAD_DIR / file.filename
    output_path = OUTPUT_DIR / f"ocr_{file.filename}"
    try:
        logger.info(f"Received upload: {file.filename}")
        valid = validate_file(file)
        logger.info(f"File validated: {valid}")
        if not valid:
            return {"status": "error", "message": "Invalid file uploaded"}
        save_uploaded_file(file, input_path)
        process_pdf(input_path, output_path)
        return FileResponse(
            path=output_path,
            media_type="application/pdf",
            filename=output_path.name
        )
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    uvicorn.run("main:app", host="172.17.200.196", port=8078)
