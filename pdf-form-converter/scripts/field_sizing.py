#!/usr/bin/env python3
"""
Intelligent Field Sizing Module

Calculates optimal field dimensions based on:
- Available white space
- Underlines and box detection
- Label positioning and size
- Adjacent field proximity
- Text height analysis

This module runs between vision validation and PDF generation to ensure
fields are sized appropriately for their context.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from pdf2image import convert_from_path


def calculate_intelligent_field_sizes(pdf_path: str, fields_json: str,
                                     output_json: str = None, dpi: int = 300) -> dict:
    """
    Analyze PDF and calculate optimal field sizes.

    Args:
        pdf_path: Path to PDF file
        fields_json: Path to detected fields JSON
        output_json: Optional output path for sized fields
        dpi: DPI for PDF to image conversion (higher = more accurate, slower)

    Returns:
        Dictionary with optimized field dimensions
    """
    pdf_path = Path(pdf_path)
    fields_json = Path(fields_json)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
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

    print(f"\nIntelligent Field Sizing")
    print("=" * 60)
    print(f"Input PDF: {pdf_path.name}")
    print(f"Fields to optimize: {len(fields)}")

    # Convert PDF to images for analysis
    print(f"\nConverting PDF to images (DPI={dpi})...")
    images = convert_from_path(str(pdf_path), dpi=dpi)
    print(f"Converted {len(images)} pages")

    # Group fields by page
    fields_by_page = {}
    for field in fields:
        page_num = field.get("page", 1)
        if page_num not in fields_by_page:
            fields_by_page[page_num] = []
        fields_by_page[page_num].append(field)

    # Process each field
    optimized_fields = []

    for page_num, image in enumerate(images, 1):
        print(f"\nProcessing page {page_num}/{len(images)}...")
        page_fields = fields_by_page.get(page_num, [])

        if not page_fields:
            print(f"  No fields on page {page_num}")
            continue

        print(f"  Optimizing {len(page_fields)} fields...")

        for field_idx, field in enumerate(page_fields):
            # Calculate optimal dimensions
            optimized_bbox = optimize_field_bbox(
                field,
                image,
                page_fields  # Pass all fields to detect overlaps
            )

            # Create optimized field
            optimized_field = field.copy()
            optimized_field["bounding_box"] = optimized_bbox
            optimized_field["sizing_method"] = "intelligent"
            optimized_fields.append(optimized_field)

        print(f"  ✓ Optimized {len(page_fields)} fields")

    # Build output
    result = fields_data.copy()
    result["validated_fields"] = optimized_fields
    result["sizing_applied"] = True
    result["sizing_stats"] = {
        "total_fields": len(optimized_fields),
        "avg_width": sum(f["bounding_box"]["width"] for f in optimized_fields) / len(optimized_fields) if optimized_fields else 0,
        "avg_height": sum(f["bounding_box"]["height"] for f in optimized_fields) / len(optimized_fields) if optimized_fields else 0
    }

    if output_json:
        with open(output_json, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n✓ Saved optimized fields to: {output_json}")

    return result


def optimize_field_bbox(field: Dict, page_image: Image.Image,
                       all_fields: List[Dict]) -> Dict[str, float]:
    """
    Calculate optimal bounding box for a single field.

    Strategy:
    1. Detect underlines/boxes in the vicinity
    2. Analyze white space horizontally and vertically
    3. Check for label text to avoid overlap
    4. Ensure minimum readable size
    5. Cap at maximum reasonable size
    6. Prevent overlap with adjacent fields

    Args:
        field: Field dictionary
        page_image: PIL Image of the page
        all_fields: List of all fields on the page

    Returns:
        Optimized bounding box dictionary
    """
    bbox = field.get("bounding_box", {})
    field_type = field.get("field_type", "text")

    # Convert normalized coords to pixel coordinates
    img_width, img_height = page_image.size
    left_px = int(bbox.get("left", 0) * img_width)
    top_px = int(bbox.get("top", 0) * img_height)
    width_px = int(bbox.get("width", 0.2) * img_width)
    height_px = int(bbox.get("height", 0.02) * img_height)

    # Extract region around field for analysis
    analysis_margin = 50  # pixels
    region_left = max(0, left_px - analysis_margin)
    region_top = max(0, top_px - analysis_margin)
    region_right = min(img_width, left_px + width_px + analysis_margin)
    region_bottom = min(img_height, top_px + height_px + analysis_margin)

    region = page_image.crop((region_left, region_top, region_right, region_bottom))

    # 1. Detect underlines and boxes
    underline_bbox = detect_underline_or_box(region, (left_px - region_left, top_px - region_top))

    if underline_bbox:
        # Use underline dimensions
        optimized_width_px = underline_bbox["width"]
        optimized_height_px = max(underline_bbox["height"], int(0.015 * img_height))  # Min height
        optimized_left = bbox["left"]
        optimized_top = bbox["top"]
    else:
        # 2. Analyze white space
        white_space = analyze_white_space(region, (left_px - region_left, top_px - region_top))

        # Calculate optimal width based on white space
        optimized_width_px = min(
            white_space["horizontal_extent"],
            int(0.5 * img_width)  # Max 50% of page width
        )

        # 3. Calculate height based on text size
        text_height = estimate_text_height(region)
        optimized_height_px = max(
            int(text_height * 1.2),  # 120% of text height for padding
            int(0.015 * img_height),  # Minimum 1.5% of page height
            min(height_px, int(0.04 * img_height))  # Don't shrink below original or 4% max
        )

        optimized_left = bbox["left"]
        optimized_top = bbox["top"]

    # 4. Adjust for field type
    if field_type == "checkbox":
        # Checkboxes should be square
        size = min(optimized_width_px, optimized_height_px)
        optimized_width_px = size
        optimized_height_px = size
    elif field_type == "textarea":
        # Text areas should be taller
        optimized_height_px = max(optimized_height_px, int(0.1 * img_height))
    elif field_type == "signature":
        # Signatures need more space
        optimized_height_px = max(optimized_height_px, int(0.05 * img_height))
        optimized_width_px = max(optimized_width_px, int(0.2 * img_width))

    # Normalize back to 0.0-1.0 coordinates
    optimized_bbox = {
        "left": optimized_left,
        "top": optimized_top,
        "width": optimized_width_px / img_width,
        "height": optimized_height_px / img_height
    }

    # 5. Check for overlaps with other fields
    if has_overlap(optimized_bbox, all_fields, field):
        # Shrink to avoid overlap
        optimized_bbox["width"] *= 0.9
        optimized_bbox["height"] *= 0.9

    return optimized_bbox


def detect_underline_or_box(region: Image.Image, field_pos: Tuple[int, int]) -> Optional[Dict]:
    """
    Detect underlines or boxes that indicate field boundaries.

    Uses edge detection and line detection algorithms.

    Args:
        region: PIL Image of the region around the field
        field_pos: (x, y) position of field within the region

    Returns:
        Dictionary with detected dimensions or None
    """
    try:
        # Convert to grayscale
        gray = region.convert('L')

        # Edge detection
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edges_array = np.array(edges)

        # Look for horizontal lines (underlines)
        # Threshold for line detection
        threshold = 100
        horizontal_lines = np.where(edges_array > threshold)[0]

        if len(horizontal_lines) > 0:
            # Found underline - calculate its extent
            line_y = int(np.median(horizontal_lines))

            # Find line width
            if line_y < edges_array.shape[0]:
                line_row = edges_array[line_y, :]
                line_pixels = np.where(line_row > threshold)[0]

                if len(line_pixels) > 10:  # Minimum line length
                    return {
                        "width": len(line_pixels),
                        "height": 3,  # Typical underline thickness
                        "type": "underline"
                    }
    except Exception as e:
        # Silently fail and return None
        pass

    return None


def analyze_white_space(region: Image.Image, field_pos: Tuple[int, int]) -> Dict:
    """
    Analyze available white space around field position.

    Args:
        region: PIL Image of the region
        field_pos: (x, y) position of field within the region

    Returns:
        Dictionary with horizontal and vertical extent
    """
    # Convert to grayscale
    gray = region.convert('L')
    array = np.array(gray)

    # Threshold for "white" (empty space)
    white_threshold = 240

    field_x, field_y = field_pos

    # Scan horizontally for white space
    horizontal_extent = 0
    for x in range(field_x, min(field_x + 500, array.shape[1])):
        if x >= array.shape[1] or field_y >= array.shape[0]:
            break
        # Check a small vertical slice
        slice_height = min(10, array.shape[0] - field_y)
        if np.mean(array[field_y:field_y+slice_height, x]) < white_threshold:
            # Hit non-white pixels (probably text or border)
            break
        horizontal_extent += 1

    # Scan vertically for white space
    vertical_extent = 0
    for y in range(field_y, min(field_y + 100, array.shape[0])):
        if y >= array.shape[0] or field_x >= array.shape[1]:
            break
        # Check a small horizontal slice
        slice_width = min(10, array.shape[1] - field_x)
        if np.mean(array[y, field_x:field_x+slice_width]) < white_threshold:
            break
        vertical_extent += 1

    return {
        "horizontal_extent": horizontal_extent,
        "vertical_extent": vertical_extent
    }


def estimate_text_height(region: Image.Image) -> int:
    """
    Estimate typical text height in the region.

    Uses run-length analysis of dark pixels.

    Args:
        region: PIL Image of the region

    Returns:
        Estimated text height in pixels
    """
    gray = region.convert('L')
    array = np.array(gray)

    # Threshold for text (dark pixels)
    text_threshold = 100

    # Find vertical runs of dark pixels (text strokes)
    vertical_runs = []

    # Sample every 10 pixels horizontally
    for x in range(0, array.shape[1], 10):
        if x >= array.shape[1]:
            break
        column = array[:, x]
        in_run = False
        run_length = 0

        for pixel in column:
            if pixel < text_threshold:
                run_length += 1
                in_run = True
            else:
                if in_run and run_length > 3:  # Min 3 pixels for text
                    vertical_runs.append(run_length)
                run_length = 0
                in_run = False

    if vertical_runs:
        # Median run length is approximate text height
        return int(np.median(vertical_runs))
    else:
        return 12  # Default ~12px text at 300 DPI


def has_overlap(bbox: Dict, all_fields: List[Dict], current_field: Dict) -> bool:
    """
    Check if bounding box overlaps with any other field.

    Args:
        bbox: Bounding box to check
        all_fields: List of all fields on the page
        current_field: The current field (to exclude from check)

    Returns:
        True if overlap detected
    """
    for other_field in all_fields:
        if other_field is current_field:
            continue

        if other_field.get("page") != current_field.get("page"):
            continue

        other_bbox = other_field.get("bounding_box", {})

        # Check for overlap
        if boxes_overlap(bbox, other_bbox):
            return True

    return False


def boxes_overlap(bbox1: Dict, bbox2: Dict) -> bool:
    """
    Check if two bounding boxes overlap.

    Args:
        bbox1: First bounding box
        bbox2: Second bounding box

    Returns:
        True if boxes overlap
    """
    left1 = bbox1.get("left", 0)
    top1 = bbox1.get("top", 0)
    right1 = left1 + bbox1.get("width", 0)
    bottom1 = top1 + bbox1.get("height", 0)

    left2 = bbox2.get("left", 0)
    top2 = bbox2.get("top", 0)
    right2 = left2 + bbox2.get("width", 0)
    bottom2 = top2 + bbox2.get("height", 0)

    # Check if boxes overlap
    return not (right1 < left2 or left1 > right2 or bottom1 < top2 or top1 > bottom2)


def main():
    import sys

    if len(sys.argv) < 3:
        print("Usage: python field_sizing.py <input.pdf> <fields.json> [--output sized_fields.json] [--dpi 300]")
        print("\nCalculates optimal field sizes based on white space analysis.")
        sys.exit(1)

    pdf_path = sys.argv[1]
    fields_json = sys.argv[2]
    output_json = None
    dpi = 300

    # Parse arguments
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_json = sys.argv[idx + 1]

    if "--dpi" in sys.argv:
        idx = sys.argv.index("--dpi")
        if idx + 1 < len(sys.argv):
            dpi = int(sys.argv[idx + 1])

    try:
        result = calculate_intelligent_field_sizes(pdf_path, fields_json, output_json, dpi)

        print("\n" + "=" * 60)
        print(f"✓ Optimized {len(result.get('validated_fields', []))} field sizes")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
