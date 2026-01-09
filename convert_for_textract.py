#!/usr/bin/env python3
"""
Convert PDF to Textract-compatible format
Converts PDF to images and back to ensure compatibility.
"""

import sys
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pypdf import PdfReader
import io

def pdf_to_textract_compatible(input_pdf: str, output_pdf: str = None):
    """
    Convert PDF to Textract-compatible format by:
    1. Converting pages to high-quality images
    2. Creating a new PDF from those images

    This ensures Textract can process it as an image-based PDF.
    """
    input_path = Path(input_pdf)

    if output_pdf is None:
        output_pdf = input_path.parent / f"{input_path.stem}_textract.pdf"
    else:
        output_pdf = Path(output_pdf)

    print(f"Converting PDF to Textract-compatible format")
    print(f"Input: {input_path}")
    print(f"Output: {output_pdf}")
    print("-" * 60)

    try:
        # Get original PDF info
        reader = PdfReader(str(input_path))
        num_pages = len(reader.pages)
        print(f"✓ Original PDF has {num_pages} pages")

        # Convert to images at high DPI for quality
        print(f"Converting pages to images (DPI=200)...")
        images = convert_from_path(str(input_path), dpi=200)
        print(f"✓ Converted {len(images)} pages to images")

        # Create new PDF from images
        print("Creating new PDF from images...")

        # Use reportlab to create PDF
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader

        c = canvas.Canvas(str(output_pdf))

        for i, img in enumerate(images, 1):
            print(f"  Processing page {i}/{len(images)}...")

            # Get image size
            img_width, img_height = img.size

            # Calculate PDF page size (convert from pixels to points)
            # 72 points per inch, 200 DPI
            page_width = img_width * 72 / 200
            page_height = img_height * 72 / 200

            # Set page size
            c.setPageSize((page_width, page_height))

            # Save image to bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG', quality=95)
            img_buffer.seek(0)

            # Draw image on PDF
            c.drawImage(ImageReader(img_buffer), 0, 0,
                       width=page_width, height=page_height)

            # Next page
            c.showPage()

        # Save PDF
        c.save()

        print(f"\n✓ Created Textract-compatible PDF: {output_pdf}")
        print(f"\nNow try:")
        print(f"  venv/bin/python pdf-form-converter/scripts/textract_detection.py {output_pdf} --output-json test.json")

        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_for_textract.py <input.pdf> [output.pdf]")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2] if len(sys.argv) > 2 else None

    success = pdf_to_textract_compatible(input_pdf, output_pdf)
    sys.exit(0 if success else 1)
