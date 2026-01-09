#!/usr/bin/env python3
"""
Generate Fillable PDF Script

Creates interactive PDF forms with detected fields while preserving original styling.
Uses pdfrw for better AcroForm support and visual fidelity.
"""

import sys
import json
from pathlib import Path

from pdfrw import PdfReader, PdfWriter, PdfDict, PdfArray, PdfName, PdfString, PdfObject


def create_form_field(field_data: dict, page_height: float, page_width: float) -> PdfDict:
    """
    Create a PDF form field annotation object using pdfrw.

    Creates transparent form fields that preserve original document appearance.

    Args:
        field_data: Dictionary containing field properties
        page_height: Height of the PDF page (for coordinate conversion)
        page_width: Width of the PDF page (for coordinate conversion)

    Returns:
        PdfDict representing the form field
    """

    bbox = field_data.get("bounding_box", {})
    field_type = field_data.get("field_type", "text")
    label = field_data.get("label", "Field")

    # Convert normalized coordinates to PDF points
    # PDF coordinates are from bottom-left, normalized are from top-left
    left = bbox.get("left", 0) * page_width
    top = bbox.get("top", 0) * page_height
    width = bbox.get("width", 0.2) * page_width
    height = bbox.get("height", 0.02) * page_height

    # Convert top-left to bottom-left coordinates
    bottom = page_height - top - height
    right = left + width

    # Create field annotation
    field = PdfDict()
    field.Type = PdfName.Annot
    field.Subtype = PdfName.Widget
    field.Rect = PdfArray([left, bottom, right, bottom + height])
    field.T = PdfString.encode(label)  # Field name
    field.F = 4  # Print flag

    # Set field type and properties
    if field_type == "checkbox":
        field.FT = PdfName.Btn
        field.Ff = 0  # No flags for simple checkbox
        # Checkbox appearance
        field.AS = PdfName.Off
        field.DV = PdfName.Off

    elif field_type == "signature":
        field.FT = PdfName.Sig
        field.Ff = 0

    else:
        # Text field (includes text, textarea, date, email, phone, number)
        field.FT = PdfName.Tx

        # Multi-line for textarea
        if field_type == "textarea":
            field.Ff = 4096  # Multiline flag
        else:
            field.Ff = 0

    # CRITICAL: Appearance settings for visual fidelity
    # Make fields transparent to preserve original styling
    field.DA = PdfString.encode("0 0 0 rg /Helv 12 Tf")  # Default appearance: black text, Helvetica 12pt

    # Border style - make invisible
    field.BS = PdfDict(
        W=0,  # Border width = 0 for invisibility
        S=PdfName.S  # Solid style
    )

    # Make background transparent (white = invisible on white background)
    field.MK = PdfDict(
        BC=PdfArray([1, 1, 1]),  # Border color (white/invisible)
        BG=PdfArray([1, 1, 1])   # Background color (white/transparent)
    )

    # Field value (empty initially)
    field.V = PdfString.encode("")

    return field


def generate_fillable_pdf(input_pdf: str, fields_json: str, output_pdf: str,
                          styles_json: str = None) -> None:
    """
    Generate an interactive fillable PDF from detected fields using pdfrw.

    Preserves original PDF appearance by adding transparent form field overlays.

    Args:
        input_pdf: Path to the original PDF
        fields_json: Path to JSON file with validated fields
        output_pdf: Path for output fillable PDF
        styles_json: Optional path to styles JSON for preservation (reserved for future use)
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

    # Read the original PDF with pdfrw (preserves all original content)
    template_pdf = PdfReader(str(input_pdf))

    # Group fields by page
    fields_by_page = {}
    for field in fields:
        page_num = field.get("page", 1)
        if page_num not in fields_by_page:
            fields_by_page[page_num] = []
        fields_by_page[page_num].append(field)

    # Create form fields for each page
    all_fields = []

    for page_num, page in enumerate(template_pdf.pages, 1):
        print(f"\nProcessing page {page_num}...")

        # Get page dimensions
        mediabox = page.MediaBox
        page_width = float(mediabox[2]) - float(mediabox[0])
        page_height = float(mediabox[3]) - float(mediabox[1])

        page_fields = fields_by_page.get(page_num, [])

        if page_fields:
            print(f"  Adding {len(page_fields)} form fields")

            # Create annotations array if it doesn't exist
            if not hasattr(page, 'Annots') or page.Annots is None:
                page.Annots = PdfArray()
            elif not isinstance(page.Annots, PdfArray):
                # Convert to array if it's a single annotation
                page.Annots = PdfArray([page.Annots])

            # Add each field
            for field_data in page_fields:
                field_obj = create_form_field(field_data, page_height, page_width)

                # Link field to page
                field_obj.P = page

                # Add to page annotations
                page.Annots.append(field_obj)

                # Add to master field list
                all_fields.append(field_obj)

    # Create AcroForm dictionary
    if len(all_fields) > 0:
        print("\nSetting up PDF AcroForm structure...")

        acroform = PdfDict()
        acroform.Fields = PdfArray(all_fields)
        acroform.NeedAppearances = PdfObject('true')  # Let PDF viewer render field appearances
        acroform.SigFlags = 3  # Enable signatures

        # Add AcroForm to catalog (merge with existing if present)
        if template_pdf.Root.AcroForm:
            # Merge with existing form
            existing_fields = template_pdf.Root.AcroForm.Fields or PdfArray()
            acroform.Fields = PdfArray(list(existing_fields) + all_fields)

        template_pdf.Root.AcroForm = acroform

    # Write output PDF (preserving original structure)
    print(f"\nWriting fillable PDF: {output_pdf}")
    PdfWriter(output_pdf, trailer=template_pdf).write()

    print(f"\n✓ Successfully created fillable PDF with {len(fields)} form fields")
    print("  → Fields are transparent overlays preserving original appearance")


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
