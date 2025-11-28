import pdfplumber
import json
import os

pdf_path = r"C:\Users\jebapriya.jayapal\Downloads\AI_11_ISC_2 1.pdf"
output_json = r"C:\Users\jebapriya.jayapal\Downloads\pdf_output.json"

try:
    # Validate PDF existence
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    pdf_data = []

    # Process PDF
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_dict = {
                "page_number": page.page_number,
                "width": page.width,
                "height": page.height,
                "text": page.extract_text(layout=True) or "",
                "chars": [
                    {
                        "text": c.get("text", ""),
                        "x0": round(c.get("x0", 0), 2),
                        "y0": round(c.get("y0", 0), 2),
                        "x1": round(c.get("x1", 0), 2),
                        "y1": round(c.get("y1", 0), 2),
                        "fontname": c.get("fontname", ""),
                        "size": c.get("size", 0)
                    }
                    for c in page.chars
                ]
            }
            pdf_data.append(page_dict)

    # Save JSON output
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(pdf_data, f, indent=2, ensure_ascii=False)

    print(f"Extraction complete. JSON saved to {output_json}")

except Exception as e:
    raise RuntimeError(f"An error occurred: {e}")
