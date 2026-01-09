#!/usr/bin/env python3
"""
Visualize detected field positions on form images
Helps debug field positioning issues
"""

import sys
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def visualize_fields(image_path: str, fields_json: str, output_path: str = None):
    """
    Draw bounding boxes on form image to visualize field positions.

    Args:
        image_path: Path to form image
        fields_json: Path to JSON with field data
        output_path: Optional output path for annotated image
    """
    # Load image
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)

    # Load fields
    with open(fields_json, 'r') as f:
        data = json.load(f)

    # Determine page number from image filename
    image_name = Path(image_path).stem
    if 'page_' in image_name:
        page_num = int(image_name.split('_')[1])
    else:
        page_num = 1

    # Filter fields for this page
    page_fields = [f for f in data.get('fields', []) if f.get('page') == page_num]

    print(f"\nVisualizing {len(page_fields)} fields on page {page_num}")
    print(f"Image size: {img.width} x {img.height}")

    # Draw each field
    for i, field in enumerate(page_fields):
        bbox = field.get('bounding_box', {})
        label = field.get('label', 'Unknown')

        # Convert normalized coords to pixels
        left = bbox.get('left', 0) * img.width
        top = bbox.get('top', 0) * img.height
        width = bbox.get('width', 0) * img.width
        height = bbox.get('height', 0) * img.height

        # Calculate rectangle coordinates
        x1, y1 = left, top
        x2, y2 = left + width, top + height

        # Draw rectangle (red for better visibility)
        draw.rectangle([x1, y1, x2, y2], outline='red', width=2)

        # Draw field number
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12)
        except:
            font = ImageFont.load_default()

        draw.text((x1, y1 - 15), f"{i+1}. {label[:20]}", fill='red', font=font)

        print(f"  {i+1}. {label[:30]:30} -> x:{left:4.0f} y:{top:4.0f} w:{width:4.0f} h:{height:4.0f}")

    # Save annotated image
    if output_path is None:
        output_path = Path(image_path).parent / f"{Path(image_path).stem}_annotated.png"

    img.save(output_path)
    print(f"\n✓ Saved annotated image: {output_path}")

    return output_path

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python visualize_fields.py <image.png> <fields.json> [output.png]")
        print("\nExample:")
        print("  python visualize_fields.py inputs/images/page_1.png output.json")
        sys.exit(1)

    image_path = sys.argv[1]
    fields_json = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        visualize_fields(image_path, fields_json, output_path)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
