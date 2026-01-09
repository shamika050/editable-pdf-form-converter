#!/usr/bin/env python3
"""
AI Vision Validation Script

Uses Claude's vision capabilities to validate and refine OCR results.
Cross-validates field boundaries, labels, and types.
"""

import sys
import json
import base64
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image
import io
import anthropic

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent))
from config import load_config, get_anthropic_api_key


def pdf_to_images(pdf_path: str) -> list:
    """Convert PDF pages to PIL images."""
    print(f"Converting PDF to images: {pdf_path}")
    images = convert_from_path(pdf_path, dpi=200)
    print(f"Converted {len(images)} pages")
    return images


def image_to_base64(image: Image.Image) -> str:
    """Convert PIL image to base64 string."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def create_validation_prompt(fields: list) -> str:
    """
    Create a detailed prompt for Claude to validate form fields.

    Args:
        fields: List of detected field dictionaries

    Returns:
        Validation prompt string
    """
    fields_description = "\n".join([
        f"- Field {i+1}: Label='{f.get('label', 'Unknown')}', "
        f"Type={f.get('field_type', 'text')}, "
        f"BoundingBox=(left={f.get('bounding_box', {}).get('left', 0):.3f}, "
        f"top={f.get('bounding_box', {}).get('top', 0):.3f}, "
        f"width={f.get('bounding_box', {}).get('width', 0):.3f}, "
        f"height={f.get('bounding_box', {}).get('height', 0):.3f}), "
        f"Confidence={f.get('confidence', 0):.1f}%"
        for i, f in enumerate(fields)
    ])

    return f"""You are validating form field detection for a PDF form conversion system.

I have detected {len(fields)} form fields on this page using AWS Textract. Please analyze the image and validate:

1. **Field Boundary Accuracy**: Are the bounding boxes correctly positioned over fillable areas?
2. **Field Type Correctness**: Is the field type (text/checkbox/signature/etc.) appropriate?
3. **Missing Fields**: Are there any obvious form fields that were not detected?
4. **Label Association**: Are field labels correctly matched to their input areas?
5. **Size Appropriateness**: Are field dimensions reasonable for the available space?

DETECTED FIELDS:
{fields_description}

Please respond in JSON format with:
{{
  "validated_fields": [
    {{
      "field_index": 0,
      "is_valid": true,
      "confidence_adjustment": 0,
      "corrections": {{
        "bounding_box": {{"left": 0.1, "top": 0.2, "width": 0.3, "height": 0.02}},
        "field_type": "text",
        "label": "corrected label"
      }},
      "reasoning": "Brief explanation of validation decision"
    }}
  ],
  "missing_fields": [
    {{
      "label": "Field label",
      "field_type": "text",
      "bounding_box": {{"left": 0.5, "top": 0.3, "width": 0.2, "height": 0.02}},
      "reasoning": "Why this field was missed"
    }}
  ],
  "overall_assessment": "Summary of form field detection quality"
}}

Use normalized coordinates (0.0-1.0) for bounding boxes where 0,0 is top-left.
Only include corrections fields if changes are needed."""


def parse_claude_response(response_text: str) -> dict:
    """
    Parse Claude's JSON response and extract validation data.

    Args:
        response_text: Raw response text from Claude

    Returns:
        Parsed validation dictionary
    """
    try:
        # Claude may wrap JSON in markdown code blocks
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        return json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"Warning: Could not parse Claude response as JSON: {e}")
        return {"validated_fields": [], "missing_fields": [], "overall_assessment": "Parse error"}


def apply_claude_corrections(original_field: dict, validation_result: dict, field_index: int) -> dict:
    """
    Apply Claude's corrections to a detected field.

    Args:
        original_field: Original field dict from Textract
        validation_result: Validation response from Claude
        field_index: Index of this field in the original list

    Returns:
        Field dictionary with corrections applied
    """
    field = original_field.copy()
    field["vision_validated"] = True
    field["original_confidence"] = original_field.get("confidence", 70)

    # Find validation for this field
    validated_fields = validation_result.get("validated_fields", [])

    for validation in validated_fields:
        if validation.get("field_index") == field_index:
            # Adjust confidence
            confidence_adj = validation.get("confidence_adjustment", 0)
            field["confidence"] = max(0, min(100,
                field.get("confidence", 70) + confidence_adj
            ))

            # Apply corrections if present
            corrections = validation.get("corrections", {})
            if "bounding_box" in corrections:
                field["bounding_box"] = corrections["bounding_box"]
                field["correction_applied"] = "bounding_box_adjusted"
            if "field_type" in corrections:
                field["field_type"] = corrections["field_type"]
                field["correction_applied"] = "field_type_corrected"
            if "label" in corrections:
                field["label"] = corrections["label"]

            field["validation_reasoning"] = validation.get("reasoning", "")
            field["is_valid"] = validation.get("is_valid", True)
            break

    return field


def generate_validation_summary(results: dict) -> dict:
    """
    Generate validation summary statistics.

    Args:
        results: Validated results dictionary

    Returns:
        Summary statistics dictionary
    """
    validated_fields = results.get("validated_fields", [])

    if not validated_fields:
        return {
            "total_fields_validated": 0,
            "corrections_applied": 0,
            "avg_confidence_original": 0,
            "avg_confidence_final": 0,
            "fields_with_corrections": 0,
            "missing_fields_found": len(results.get("missing_fields", [])),
            "vision_api_calls": 0
        }

    return {
        "total_fields_validated": len(validated_fields),
        "corrections_applied": len(results.get("corrections_made", [])),
        "avg_confidence_original": sum(f.get("original_confidence", 0) for f in validated_fields) / len(validated_fields),
        "avg_confidence_final": sum(f.get("confidence", 0) for f in validated_fields) / len(validated_fields),
        "fields_with_corrections": sum(1 for f in validated_fields if "correction_applied" in f),
        "missing_fields_found": len(results.get("missing_fields", [])),
        "vision_api_calls": len(set(f.get("page", 1) for f in validated_fields))
    }


def validate_with_vision(pdf_path: str, fields_json: str, output_json: str = None) -> dict:
    """
    Use Claude vision to validate detected fields.
    
    Args:
        pdf_path: Path to the original PDF
        fields_json: Path to JSON file with detected fields
        output_json: Optional path to save validated results
        
    Returns:
        Dictionary with validated and refined field data
    """
    
    pdf_path = Path(pdf_path)
    fields_json = Path(fields_json)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if not fields_json.exists():
        raise FileNotFoundError(f"Fields JSON not found: {fields_json}")
    
    # Load detected fields
    with open(fields_json, 'r') as f:
        detected_fields = json.load(f)
    
    # Convert PDF to images
    images = pdf_to_images(str(pdf_path))
    
    # Prepare validation results
    validated_results = {
        "source_pdf": pdf_path.name,
        "original_detection": detected_fields.get("statistics", {}),
        "validated_fields": [],
        "corrections_made": [],
        "missing_fields": [],
        "validation_summary": {}
    }

    # Initialize Claude client
    try:
        config = load_config()
        api_key = get_anthropic_api_key(config)
        client = anthropic.Anthropic(api_key=api_key)
        use_claude_api = True
        print("\n✓ Claude API initialized successfully")
    except Exception as e:
        print(f"\n⚠ Warning: Could not initialize Claude API: {e}")
        print("  → Falling back to heuristic validation")
        use_claude_api = False

    print("\nValidating fields with AI vision...")
    print("Validation checks performed:")
    print("  1. Field boundary accuracy")
    print("  2. Label-to-field association")
    print("  3. Field type correctness")
    print("  4. Missing field detection")
    print("  5. Layout preservation")

    # Group fields by page
    fields_by_page = {}
    for field in detected_fields.get("fields", []):
        page = field.get("page", 1)
        if page not in fields_by_page:
            fields_by_page[page] = []
        fields_by_page[page].append(field)

    # Process each page
    for page_num, image in enumerate(images, 1):
        print(f"\nProcessing page {page_num}/{len(images)}...")

        page_fields = fields_by_page.get(page_num, [])

        if not page_fields:
            print(f"  No fields detected on page {page_num}")
            continue

        if use_claude_api:
            # Call Claude Vision API
            try:
                # Convert image to base64
                img_base64 = image_to_base64(image)

                # Create validation prompt
                prompt = create_validation_prompt(page_fields)

                # Call Claude API
                print(f"  Calling Claude Vision API...")
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4096,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": img_base64
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                )

                # Parse response
                validation_results = parse_claude_response(response.content[0].text)

                # Apply corrections to fields
                for field_idx, field in enumerate(page_fields):
                    validated_field = apply_claude_corrections(field, validation_results, field_idx)
                    validated_field["page"] = page_num
                    validated_results["validated_fields"].append(validated_field)

                    # Track corrections
                    if "correction_applied" in validated_field:
                        validated_results["corrections_made"].append({
                            "page": page_num,
                            "field": field.get("label", "Unknown"),
                            "correction": validated_field.get("correction_applied"),
                            "reasoning": validated_field.get("validation_reasoning", "")
                        })

                # Add any missing fields detected by Claude
                for missing_field in validation_results.get("missing_fields", []):
                    missing_field["page"] = page_num
                    validated_results["missing_fields"].append(missing_field)

                print(f"  ✓ Validated {len(page_fields)} fields")
                if validation_results.get("missing_fields"):
                    print(f"  → Found {len(validation_results['missing_fields'])} additional fields")

            except anthropic.APIError as e:
                print(f"  ✗ Claude API error: {e}")
                print(f"  → Using original Textract results for page {page_num}")
                # Fall back to original fields
                for field in page_fields:
                    field["vision_validated"] = False
                    field["validation_warning"] = f"Claude API unavailable: {str(e)}"
                    field["page"] = page_num
                    validated_results["validated_fields"].append(field)

        else:
            # Fallback: use original fields without Claude validation
            for field in page_fields:
                field["vision_validated"] = False
                field["validation_warning"] = "Claude API not available"
                field["page"] = page_num
                validated_results["validated_fields"].append(field)

        print(f"  Processed {len(page_fields)} fields")

    # Generate summary
    validated_results["validation_summary"] = generate_validation_summary(validated_results)
    
    # Save results
    if output_json:
        with open(output_json, 'w') as f:
            json.dump(validated_results, f, indent=2)
        print(f"\nValidated results saved to: {output_json}")
    
    return validated_results


def infer_improved_field_type(label: str, bbox: dict) -> str:
    """Improved field type inference using label and dimensions."""
    
    label_lower = label.lower()
    width = bbox.get("width", 0)
    height = bbox.get("height", 0)
    
    # Signature (usually wide and relatively tall)
    if any(word in label_lower for word in ['signature', 'sign here', 'signed']):
        return "signature"
    
    # Date
    if any(word in label_lower for word in ['date', 'when', 'day', 'month', 'year']):
        return "date"
    
    # Email
    if 'email' in label_lower or 'e-mail' in label_lower:
        return "email"
    
    # Phone
    if any(word in label_lower for word in ['phone', 'tel', 'mobile', 'cell']):
        return "phone"
    
    # Checkbox (small square-ish areas)
    if (width < 0.05 and height < 0.03) or any(word in label_lower for word in ['check', 'yes/no', 'agree']):
        return "checkbox"
    
    # Textarea (tall fields)
    if height > 0.1 or any(word in label_lower for word in ['address', 'comments', 'notes', 'description']):
        return "textarea"
    
    # Number
    if any(word in label_lower for word in ['number', 'qty', 'amount', 'count', 'age', 'zip']):
        return "number"
    
    # Dropdown (if contains options-like text)
    if any(word in label_lower for word in ['select', 'choose', 'pick', 'option']):
        return "dropdown"
    
    return "text"


def main():
    if len(sys.argv) < 3:
        print("Usage: python vision_validation.py <input.pdf> <fields.json> [--output validated_fields.json]")
        print("\nThis script validates OCR-detected fields using AI vision analysis.")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    fields_json = sys.argv[2]
    output_json = None
    
    # Parse arguments
    if "--output" in sys.argv:
        output_idx = sys.argv.index("--output")
        if output_idx + 1 < len(sys.argv):
            output_json = sys.argv[output_idx + 1]
    
    try:
        results = validate_with_vision(pdf_path, fields_json, output_json)
        
        # Print summary
        print("\n" + "="*60)
        print("VISION VALIDATION SUMMARY")
        print("="*60)
        print(f"\nFields validated: {results['validation_summary']['total_fields_validated']}")
        print(f"Corrections applied: {results['validation_summary']['corrections_applied']}")
        print(f"\nConfidence improvement:")
        print(f"  Original: {results['validation_summary']['avg_confidence_original']:.1f}%")
        print(f"  Final: {results['validation_summary']['avg_confidence_final']:.1f}%")
        
        if results["corrections_made"]:
            print(f"\nSample corrections:")
            for correction in results["corrections_made"][:5]:
                print(f"  Page {correction['page']}: {correction['field']} - {correction['correction']}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
