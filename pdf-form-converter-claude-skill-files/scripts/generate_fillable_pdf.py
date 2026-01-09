#!/usr/bin/env python3
"""
Generate Fillable PDF Script

Creates interactive PDF forms with detected fields while preserving original styling.
"""

import sys
import json
from pathlib import Path

try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject, TextStringObject, NumberObject, DictionaryObject, ArrayObject
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    import io
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--break-system-packages", 
                          "pypdf", "reportlab"])
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject, TextStringObject, NumberObject, DictionaryObject, ArrayObject
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    import io


def create_form_field(field_data: dict, page_height: float) -> DictionaryObject:
    """
    Create a PDF form field annotation object.
    
    Args:
        field_data: Dictionary containing field properties
        page_height: Height of the PDF page (for coordinate conversion)
        
    Returns:
        DictionaryObject representing the form field
    """
    
    bbox = field_data.get("bounding_box", {})
    field_type = field_data.get("field_type", "text")
    label = field_data.get("label", "Field")
    
    # Convert normalized coordinates to PDF coordinates
    # PDF coordinates are from bottom-left, normalized are from top-left
    left = bbox.get("left", 0) * 612  # Letter width in points
    top = bbox.get("top", 0) * page_height
    width = bbox.get("width", 0.2) * 612
    height = bbox.get("height", 0.02) * page_height
    
    # Convert top-left to bottom-left coordinates
    bottom = page_height - top - height
    right = left + width
    
    # Create field dictionary
    field = DictionaryObject()
    
    # Set field type
    if field_type == "checkbox":
        field.update({
            NameObject("/FT"): NameObject("/Btn"),
            NameObject("/Ff"): NumberObject(0),  # No flags for simple checkbox
        })
    elif field_type == "signature":
        field.update({
            NameObject("/FT"): NameObject("/Sig"),
        })
    else:
        # Text field (includes text, textarea, date, email, phone, number)
        field.update({
            NameObject("/FT"): NameObject("/Tx"),
        })
        
        # Multi-line for textarea
        if field_type == "textarea":
            field.update({
                NameObject("/Ff"): NumberObject(4096),  # Multiline flag
            })
    
    # Common properties
    field.update({
        NameObject("/T"): TextStringObject(label),  # Field name
        NameObject("/Rect"): ArrayObject([
            NumberObject(left),
            NumberObject(bottom),
            NumberObject(right),
            NumberObject(bottom + height)
        ]),
        NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Widget"),
        NameObject("/F"): NumberObject(4),  # Print flag
    })
    
    # Default appearance
    field.update({
        NameObject("/DA"): TextStringObject("0 0 0 rg /Helv 12 Tf"),  # Black text, Helvetica 12pt
    })
    
    return field


def generate_fillable_pdf(input_pdf: str, fields_json: str, output_pdf: str, 
                          styles_json: str = None) -> None:
    """
    Generate an interactive fillable PDF from detected fields.
    
    Args:
        input_pdf: Path to the original PDF
        fields_json: Path to JSON file with validated fields
        output_pdf: Path for output fillable PDF
        styles_json: Optional path to styles JSON for preservation
    """
    
    input_pdf = Path(input_pdf)
    fields_json = Path(fields_json)
    
    if not input_pdf.exists():
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")
    if not fields_json.exists():
        raise FileNotFoundError(f"Fields JSON not found: {fields_json}")
    
    # Load fields
    with open(fields_json, 'r') as f:
        fields_data = json.load(f)
    
    # Get fields list (handle different JSON structures)
    if "validated_fields" in fields_data:
        fields = fields_data["validated_fields"]
    elif "fields" in fields_data:
        fields = fields_data["fields"]
    else:
        raise ValueError("No fields found in JSON file")
    
    print(f"Loading input PDF: {input_pdf}")
    print(f"Fields to add: {len(fields)}")
    
    # Read the original PDF
    reader = PdfReader(str(input_pdf))
    writer = PdfWriter()
    
    # Copy pages and add form fields
    for page_num, page in enumerate(reader.pages, 1):
        print(f"\nProcessing page {page_num}...")
        
        # Get page height for coordinate conversion
        page_height = float(page.mediabox.height)
        
        # Get fields for this page
        page_fields = [f for f in fields if f.get("page", 1) == page_num]
        
        if page_fields:
            print(f"  Adding {len(page_fields)} form fields")
            
            # Add each field as an annotation
            for field_data in page_fields:
                field_obj = create_form_field(field_data, page_height)
                
                # Add field to page annotations
                if "/Annots" in page:
                    page[NameObject("/Annots")].append(field_obj)
                else:
                    page[NameObject("/Annots")] = ArrayObject([field_obj])
        
        # Add page to writer
        writer.add_page(page)
    
    # Set up the AcroForm dictionary
    if len(fields) > 0:
        print("\nSetting up PDF form structure...")
        
        # Create AcroForm dictionary
        acro_form = DictionaryObject()
        acro_form.update({
            NameObject("/Fields"): ArrayObject([]),
            NameObject("/NeedAppearances"): NameObject("/true"),
        })
        
        # Add all fields to the form
        for page in writer.pages:
            if "/Annots" in page:
                for annot in page["/Annots"]:
                    if isinstance(annot, DictionaryObject):
                        acro_form[NameObject("/Fields")].append(annot)
        
        # Add AcroForm to catalog
        writer._root_object.update({
            NameObject("/AcroForm"): acro_form
        })
    
    # Write the output PDF
    print(f"\nWriting fillable PDF: {output_pdf}")
    with open(output_pdf, 'wb') as f:
        writer.write(f)
    
    print(f"\n✓ Successfully created fillable PDF with {len(fields)} form fields")


def main():
    if len(sys.argv) < 4:
        print("Usage: python generate_fillable_pdf.py <input.pdf> <fields.json> --output <output.pdf> [--styles styles.json]")
        print("\nCreates an interactive fillable PDF from detected form fields.")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    fields_json = sys.argv[2]
    output_pdf = None
    styles_json = None
    
    # Parse arguments
    if "--output" in sys.argv:
        output_idx = sys.argv.index("--output")
        if output_idx + 1 < len(sys.argv):
            output_pdf = sys.argv[output_idx + 1]
    
    if "--styles" in sys.argv:
        styles_idx = sys.argv.index("--styles")
        if styles_idx + 1 < len(sys.argv):
            styles_json = sys.argv[styles_idx + 1]
    
    if not output_pdf:
        print("Error: --output parameter is required")
        sys.exit(1)
    
    try:
        generate_fillable_pdf(input_pdf, fields_json, output_pdf, styles_json)
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
