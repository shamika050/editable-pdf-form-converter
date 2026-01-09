#!/usr/bin/env python3
"""
AWS Textract Field Detection Script

Uses AWS Textract to detect form fields, labels, and structure in PDF documents.
"""

import sys
import json
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent))
from config import load_config, get_aws_credentials


def detect_form_fields(pdf_path: str, output_json: str = None) -> dict:
    """
    Use AWS Textract to detect form fields in a PDF.
    
    Args:
        pdf_path: Path to the input PDF
        output_json: Optional path to save results as JSON
        
    Returns:
        Dictionary containing detected fields and their properties
    """
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    # Load configuration
    config = load_config()
    aws_creds = get_aws_credentials(config)

    # Initialize Textract client
    textract = boto3.client('textract', **aws_creds)
    
    print(f"Reading PDF: {pdf_path}")
    
    # Read PDF bytes
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    print("Calling AWS Textract (AnalyzeDocument with FORMS analysis)...")
    
    try:
        # Call Textract
        response = textract.analyze_document(
            Document={'Bytes': pdf_bytes},
            FeatureTypes=['FORMS']
        )
    except NoCredentialsError:
        raise EnvironmentError("AWS credentials not configured properly")
    except ClientError as e:
        raise RuntimeError(f"AWS Textract error: {e}")
    
    # Parse results
    results = {
        "document_metadata": {
            "pages": response.get('DocumentMetadata', {}).get('Pages', 0)
        },
        "fields": [],
        "key_value_pairs": []
    }
    
    # Extract blocks
    blocks = response.get('Blocks', [])
    
    # Build a map of block IDs for relationship lookup
    block_map = {block['Id']: block for block in blocks}
    
    # Process KEY_VALUE_SET blocks (form fields)
    for block in blocks:
        if block['BlockType'] == 'KEY_VALUE_SET':
            entity_type = block.get('EntityTypes', [])
            
            if 'KEY' in entity_type:
                # This is a field label (key)
                key_text = get_text_from_block(block, block_map)
                value_text = ""
                confidence = block.get('Confidence', 0)
                
                # Find associated value
                if 'Relationships' in block:
                    for relationship in block['Relationships']:
                        if relationship['Type'] == 'VALUE':
                            for value_id in relationship['Ids']:
                                value_block = block_map.get(value_id)
                                if value_block:
                                    value_text = get_text_from_block(value_block, block_map)
                
                # Get bounding box
                bbox = block.get('Geometry', {}).get('BoundingBox', {})
                
                field_info = {
                    "label": key_text,
                    "value": value_text,
                    "confidence": confidence,
                    "page": block.get('Page', 1),
                    "bounding_box": {
                        "left": bbox.get('Left', 0),
                        "top": bbox.get('Top', 0),
                        "width": bbox.get('Width', 0),
                        "height": bbox.get('Height', 0)
                    },
                    "field_type": "text"  # Default, can be refined
                }
                
                # Infer field type from label
                field_info["field_type"] = infer_field_type(key_text)
                
                results["fields"].append(field_info)
                results["key_value_pairs"].append({
                    "key": key_text,
                    "value": value_text,
                    "confidence": confidence
                })
    
    # Add statistics
    results["statistics"] = {
        "total_fields": len(results["fields"]),
        "avg_confidence": sum(f["confidence"] for f in results["fields"]) / len(results["fields"]) if results["fields"] else 0,
        "field_types": {}
    }
    
    # Count field types
    for field in results["fields"]:
        field_type = field["field_type"]
        results["statistics"]["field_types"][field_type] = results["statistics"]["field_types"].get(field_type, 0) + 1
    
    # Save results
    if output_json:
        with open(output_json, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {output_json}")
    
    return results


def get_text_from_block(block, block_map):
    """Extract text from a block and its children."""
    text = ""
    if 'Relationships' in block:
        for relationship in block['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    child = block_map.get(child_id)
                    if child and child['BlockType'] == 'WORD':
                        text += child.get('Text', '') + " "
    return text.strip()


def infer_field_type(label: str) -> str:
    """Infer field type from label text."""
    label_lower = label.lower()
    
    # Signature detection
    if any(word in label_lower for word in ['signature', 'sign here', 'signed']):
        return "signature"
    
    # Date detection
    if any(word in label_lower for word in ['date', 'when', 'day', 'month', 'year']):
        return "date"
    
    # Email detection
    if 'email' in label_lower or 'e-mail' in label_lower:
        return "email"
    
    # Phone detection
    if any(word in label_lower for word in ['phone', 'tel', 'mobile', 'cell']):
        return "phone"
    
    # Checkbox detection
    if any(word in label_lower for word in ['check', 'yes/no', 'select', 'choose']):
        return "checkbox"
    
    # Multi-line text detection
    if any(word in label_lower for word in ['address', 'comments', 'notes', 'description', 'details']):
        return "textarea"
    
    # Number detection
    if any(word in label_lower for word in ['number', 'quantity', 'amount', 'count', 'age', 'zip', 'postal']):
        return "number"
    
    # Default to text
    return "text"


def main():
    if len(sys.argv) < 2:
        print("Usage: python textract_detection.py <input.pdf> [--output-json fields.json]")
        print("\nRequires AWS credentials:")
        print("  export AWS_ACCESS_KEY_ID=your_key")
        print("  export AWS_SECRET_ACCESS_KEY=your_secret")
        print("  export AWS_DEFAULT_REGION=us-east-1")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    output_json = None
    
    # Parse arguments
    if "--output-json" in sys.argv:
        output_idx = sys.argv.index("--output-json")
        if output_idx + 1 < len(sys.argv):
            output_json = sys.argv[output_idx + 1]
    
    try:
        results = detect_form_fields(input_pdf, output_json)
        
        # Print summary
        print("\n" + "="*60)
        print("TEXTRACT DETECTION RESULTS")
        print("="*60)
        print(f"\nTotal fields detected: {results['statistics']['total_fields']}")
        print(f"Average confidence: {results['statistics']['avg_confidence']:.1f}%")
        print(f"\nField type distribution:")
        for field_type, count in results['statistics']['field_types'].items():
            print(f"  {field_type}: {count}")
        
        if not output_json:
            print("\nNote: Use --output-json to save detailed results")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
