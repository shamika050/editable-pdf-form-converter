#!/usr/bin/env python3
"""
Run Textract on PNG images and generate fillable PDF
Complete pipeline: Textract → Vision Validation → Field Sizing → PDF Generation
"""

import sys
import json
import subprocess
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

sys.path.insert(0, str(Path(__file__).parent / "pdf-form-converter/scripts"))
from config import load_config, get_aws_credentials

def detect_from_images(image_dir: str, output_json: str):
    """
    Run Textract on PNG images.

    Args:
        image_dir: Directory containing page_1.png, page_2.png, etc.
        output_json: Output JSON file path
    """
    image_dir = Path(image_dir)
    image_files = sorted(image_dir.glob("page_*.png"))

    if not image_files:
        raise FileNotFoundError(f"No page_*.png files found in {image_dir}")

    print(f"Found {len(image_files)} image files")

    # Load config
    config = load_config()
    aws_creds = get_aws_credentials(config)

    # Initialize Textract client
    textract = boto3.client('textract', **aws_creds)

    all_fields = []
    total_confidence = 0
    field_count = 0

    for page_num, image_file in enumerate(image_files, 1):
        print(f"\nProcessing page {page_num}: {image_file.name}")

        # Read image bytes
        with open(image_file, 'rb') as f:
            image_bytes = f.read()

        print(f"  Image size: {len(image_bytes)/1024:.1f} KB")

        try:
            # Call Textract
            print("  Calling AWS Textract...")
            response = textract.analyze_document(
                Document={'Bytes': image_bytes},
                FeatureTypes=['FORMS']
            )

            print(f"  ✓ Textract succeeded")

            # Parse results
            blocks = response.get('Blocks', [])

            # Find KEY_VALUE_SET blocks (form fields)
            for block in blocks:
                if block.get('BlockType') == 'KEY_VALUE_SET':
                    entity_types = block.get('EntityTypes', [])

                    if 'KEY' in entity_types:
                        # This is a label/key
                        key_text = extract_text_from_relationships(block, blocks)
                        confidence = block.get('Confidence', 0)

                        # Find corresponding value block (the actual input area)
                        value_block = find_value_block(block, blocks)

                        if key_text and value_block:
                            # Use VALUE block's bounding box (the input area, not the label)
                            bbox = value_block.get('Geometry', {}).get('BoundingBox', {})

                            # If no value block geometry, skip this field
                            if not bbox:
                                print(f"    ⚠ Skipping '{key_text}' - no value area found")
                                continue

                            field = {
                                "label": key_text.strip(),
                                "field_type": infer_field_type(key_text),
                                "confidence": round(confidence, 1),
                                "page": page_num,
                                "bounding_box": {
                                    "left": float(bbox.get('Left', 0)),
                                    "top": float(bbox.get('Top', 0)),
                                    "width": float(bbox.get('Width', 0.2)),
                                    "height": float(bbox.get('Height', 0.02))
                                }
                            }

                            all_fields.append(field)
                            total_confidence += confidence
                            field_count += 1

            print(f"  Found {len([f for f in all_fields if f['page'] == page_num])} fields on this page")

        except ClientError as e:
            print(f"  ✗ Textract error: {e}")
            raise

    # Build output
    results = {
        "fields": all_fields,
        "statistics": {
            "total_fields": field_count,
            "avg_confidence": round(total_confidence / field_count, 1) if field_count > 0 else 0,
            "pages_processed": len(image_files)
        }
    }

    # Save to JSON
    output_json = Path(output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    with open(output_json, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Saved results to: {output_json}")
    print(f"  Total fields: {field_count}")
    print(f"  Avg confidence: {results['statistics']['avg_confidence']}%")

    return results

def extract_text_from_relationships(block, all_blocks):
    """Extract text from CHILD relationships."""
    text_parts = []
    relationships = block.get('Relationships', [])

    for relationship in relationships:
        if relationship.get('Type') == 'CHILD':
            for child_id in relationship.get('Ids', []):
                child_block = find_block_by_id(child_id, all_blocks)
                if child_block and child_block.get('BlockType') == 'WORD':
                    text_parts.append(child_block.get('Text', ''))

    return ' '.join(text_parts)

def find_block_by_id(block_id, all_blocks):
    """Find a block by its ID."""
    for block in all_blocks:
        if block.get('Id') == block_id:
            return block
    return None

def find_value_block(key_block, all_blocks):
    """Find the VALUE block corresponding to a KEY block."""
    relationships = key_block.get('Relationships', [])

    for relationship in relationships:
        if relationship.get('Type') == 'VALUE':
            for value_id in relationship.get('Ids', []):
                return find_block_by_id(value_id, all_blocks)
    return None

def infer_field_type(label: str) -> str:
    """Infer field type from label text."""
    label_lower = label.lower()

    if 'email' in label_lower or '@' in label_lower:
        return 'email'
    elif 'phone' in label_lower or 'mobile' in label_lower or 'tel' in label_lower:
        return 'phone'
    elif 'date' in label_lower or 'dob' in label_lower:
        return 'date'
    elif 'signature' in label_lower or 'sign' in label_lower:
        return 'signature'
    elif 'address' in label_lower or 'street' in label_lower:
        return 'textarea'
    elif 'check' in label_lower or label_lower.startswith('☐') or label_lower.startswith('□'):
        return 'checkbox'
    else:
        return 'text'

def run_pipeline(image_dir: str, output_json: str, original_pdf: str, output_pdf: str = None):
    """
    Run complete pipeline: Textract → Vision → Sizing → PDF Generation

    Args:
        image_dir: Directory containing page_*.png files
        output_json: Path for intermediate JSON (e.g., output.json)
        original_pdf: Path to original PDF file
        output_pdf: Path for output fillable PDF (optional, defaults to outputs/output_fillable.pdf)
    """
    print("=" * 60)
    print("PDF FORM CONVERTER - COMPLETE PIPELINE")
    print("=" * 60)

    # Set default output PDF path
    if output_pdf is None:
        output_json_path = Path(output_json)
        output_pdf = output_json_path.parent / f"{output_json_path.stem}_fillable.pdf"

    output_pdf = Path(output_pdf)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)

    scripts_dir = Path(__file__).parent / "pdf-form-converter/scripts"
    python_bin = Path(sys.executable)

    # Step 1: Textract field detection
    print("\n[Step 1/4] Running Textract field detection...")
    print("-" * 60)
    results = detect_from_images(image_dir, output_json)

    # Step 2: Vision validation (optional, gracefully degrades)
    print("\n[Step 2/4] Running vision validation...")
    print("-" * 60)
    validated_json = Path(output_json).parent / f"{Path(output_json).stem}_validated.json"

    try:
        subprocess.run([
            str(python_bin),
            str(scripts_dir / "vision_validation.py"),
            str(original_pdf),
            str(output_json),
            "--output", str(validated_json)
        ], check=True)
        print(f"✓ Vision validation complete: {validated_json}")
        current_json = validated_json
    except subprocess.CalledProcessError as e:
        print(f"⚠ Vision validation failed, using original Textract results")
        current_json = output_json

    # Step 3: Intelligent field sizing
    print("\n[Step 3/4] Running intelligent field sizing...")
    print("-" * 60)
    sized_json = Path(output_json).parent / f"{Path(output_json).stem}_sized.json"

    try:
        subprocess.run([
            str(python_bin),
            str(scripts_dir / "field_sizing.py"),
            str(original_pdf),
            str(current_json),
            "--output", str(sized_json)
        ], check=True)
        print(f"✓ Field sizing complete: {sized_json}")
        current_json = sized_json
    except subprocess.CalledProcessError as e:
        print(f"⚠ Field sizing failed, using previous results")

    # Step 4: Generate fillable PDF
    print("\n[Step 4/4] Generating fillable PDF...")
    print("-" * 60)
    subprocess.run([
        str(python_bin),
        str(scripts_dir / "generate_fillable_pdf.py"),
        str(original_pdf),
        str(current_json),
        "--output", str(output_pdf)
    ], check=True)

    print("\n" + "=" * 60)
    print("✓ PIPELINE COMPLETE")
    print("=" * 60)
    print(f"\nOutput fillable PDF: {output_pdf}")
    print(f"  Fields: {results['statistics']['total_fields']}")
    print(f"  Pages: {results['statistics']['pages_processed']}")
    print(f"  Avg confidence: {results['statistics']['avg_confidence']}%")
    print(f"\nOpen the PDF to test the interactive fields!")

    return output_pdf

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python textract_from_images.py <image_dir> <output.json> [--pdf <original.pdf>] [--output <output.pdf>]")
        print("\nExample (Textract only):")
        print("  python textract_from_images.py inputs/images output.json")
        print("\nExample (Full pipeline):")
        print("  python textract_from_images.py inputs/images output.json --pdf inputs/input_1.pdf --output outputs/fillable.pdf")
        sys.exit(1)

    image_dir = sys.argv[1]
    output_json = sys.argv[2]

    # Parse optional arguments
    original_pdf = None
    output_pdf = None

    if "--pdf" in sys.argv:
        pdf_idx = sys.argv.index("--pdf")
        if pdf_idx + 1 < len(sys.argv):
            original_pdf = sys.argv[pdf_idx + 1]

    if "--output" in sys.argv:
        output_idx = sys.argv.index("--output")
        if output_idx + 1 < len(sys.argv):
            output_pdf = sys.argv[output_idx + 1]

    try:
        if original_pdf:
            # Run full pipeline
            run_pipeline(image_dir, output_json, original_pdf, output_pdf)
        else:
            # Textract only
            detect_from_images(image_dir, output_json)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
