from pypdf import PdfReader, PdfWriter
import subprocess
import os

input_pdf = r"C:\Users\jebapriya.jayapal\Documents\Intern\OCRMYPDF\input\1st Amendment.pdf"
rotated_pdf = "output/rotated.pdf"

def validate_pdf(file_path):
    try:
        if not os.path.isfile(file_path):
            return None, "File not found"
        if not file_path.lower().endswith(".pdf"):
            return None, "Insert valid PDF file"
        return str(file_path), None
    except Exception as e:
        return None, f"Internal validation error: {e}"

def rotate_pdf(input_pdf, output_pdf):
    try:
        reader = PdfReader(input_pdf)
        writer = PdfWriter()

        if not reader.pages:
            print("Error: Input PDF has no pages.")
            return False

        for page in reader.pages:
            page.rotate(90)
            writer.add_page(page)

        with open(output_pdf, "wb") as f:
            writer.write(f)

        print(f"PDF rotated successfully and saved to: {output_pdf}")
        return True
    except Exception as e:
        print(f"An unexpected error occurred during PDF rotation: {e}")
        return False

rotate_pdf(input_pdf, rotated_pdf)

