import os
import pdfplumber
import re

pdfpath = r"C:\Users\jebapriya.jayapal\Downloads\AI_11_ISC_2 1.pdf"

if os.path.exists(pdfpath):
    try:
        with pdfplumber.open(pdfpath) as pdf:
            pages_text = [re.sub(r"[^A-Za-z0-9 ]", "", page.extract_text() or "") for page in pdf.pages]

        print(f"Total pages extracted: {len(pages_text)}\n")
        print("Text from page 1:")
        print(pages_text[0])
        
        # Print all pages (optional)
        for i, text in enumerate(pages_text, 1):
            print(f"\n--- Page {i} ---\n{text}")

    except Exception as e:
        print("Error:", e)
else:
    print("File does not exist in the system")