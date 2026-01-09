#!/usr/bin/env python3
"""
PDF Format Fixer
Checks and fixes PDF format issues for AWS Textract compatibility.
"""

import sys
from pathlib import Path
from pypdf import PdfReader, PdfWriter

def fix_pdf(input_path: str, output_path: str = None):
    """
    Re-encode PDF to ensure Textract compatibility.

    Args:
        input_path: Path to input PDF
        output_path: Path for fixed PDF (default: input_fixed.pdf)
    """
    input_path = Path(input_path)

    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_fixed.pdf"
    else:
        output_path = Path(output_path)

    print(f"Fixing PDF: {input_path}")
    print(f"Output: {output_path}")
    print("-" * 60)

    try:
        # Read the PDF
        reader = PdfReader(str(input_path))

        # Check for encryption
        if reader.is_encrypted:
            print("⚠ PDF is encrypted")
            try:
                reader.decrypt("")  # Try empty password
                print("✓ Decrypted with empty password")
            except:
                print("✗ Could not decrypt PDF")
                print("  Please provide an unencrypted version")
                return False

        # Get info
        num_pages = len(reader.pages)
        print(f"✓ PDF has {num_pages} pages")

        # Check page sizes
        for i, page in enumerate(reader.pages, 1):
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            print(f"  Page {i}: {width:.1f} x {height:.1f} pts")

        # Re-write PDF to fix format issues
        print("\nRe-encoding PDF...")
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        # Write to new file
        with open(output_path, 'wb') as f:
            writer.write(f)

        print(f"\n✓ Fixed PDF saved to: {output_path}")
        print("\nTry running Textract on the fixed PDF:")
        print(f"  python pdf-form-converter/scripts/textract_detection.py {output_path} --output-json test.json")

        return True

    except Exception as e:
        print(f"\n✗ Error fixing PDF: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_pdf.py <input.pdf> [output.pdf]")
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2] if len(sys.argv) > 2 else None

    success = fix_pdf(input_pdf, output_pdf)
    sys.exit(0 if success else 1)
