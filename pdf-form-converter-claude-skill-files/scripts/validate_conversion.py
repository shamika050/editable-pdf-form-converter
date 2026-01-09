#!/usr/bin/env python3
"""
Conversion Validation Script

Validates the quality of PDF form conversion by comparing original and converted PDFs.
"""

import sys
import json
from pathlib import Path

try:
    from pypdf import PdfReader
    from pdf2image import convert_from_path
    from PIL import Image
    import numpy as np
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--break-system-packages", 
                          "pypdf", "pdf2image", "pillow", "numpy"])
    from pypdf import PdfReader
    from pdf2image import convert_from_path
    from PIL import Image
    import numpy as np


def extract_form_fields(pdf_path: str) -> list:
    """Extract form fields from a PDF."""
    reader = PdfReader(str(pdf_path))
    fields = []
    
    # Check if PDF has form fields
    if reader.get_form_text_fields() is not None:
        form_fields = reader.get_form_text_fields()
        fields.extend(form_fields.keys())
    
    # Extract field annotations from pages
    for page_num, page in enumerate(reader.pages, 1):
        if "/Annots" in page:
            for annot in page["/Annots"]:
                try:
                    annot_obj = annot.get_object()
                    if "/T" in annot_obj:  # Field name
                        field_name = annot_obj["/T"]
                        fields.append({
                            "name": str(field_name),
                            "page": page_num,
                            "type": annot_obj.get("/FT", "Unknown")
                        })
                except:
                    pass
    
    return fields


def compare_visually(original_pdf: str, converted_pdf: str) -> dict:
    """
    Compare PDFs visually using image conversion.
    Returns similarity metrics.
    """
    print("Converting PDFs to images for visual comparison...")
    
    # Convert to images
    original_images = convert_from_path(original_pdf, dpi=150)
    converted_images = convert_from_path(converted_pdf, dpi=150)
    
    if len(original_images) != len(converted_images):
        return {
            "error": "Page count mismatch",
            "original_pages": len(original_images),
            "converted_pages": len(converted_images)
        }
    
    similarities = []
    
    for page_num, (orig_img, conv_img) in enumerate(zip(original_images, converted_images), 1):
        # Resize to same dimensions if needed
        if orig_img.size != conv_img.size:
            conv_img = conv_img.resize(orig_img.size)
        
        # Convert to numpy arrays
        orig_array = np.array(orig_img)
        conv_array = np.array(conv_img)
        
        # Calculate similarity (simple MSE-based)
        mse = np.mean((orig_array - conv_array) ** 2)
        max_pixel_value = 255.0
        psnr = 20 * np.log10(max_pixel_value / np.sqrt(mse)) if mse > 0 else 100
        
        # Similarity score (0-100)
        similarity = min(100, psnr / 50 * 100)
        
        similarities.append({
            "page": page_num,
            "similarity": similarity,
            "psnr": psnr
        })
    
    avg_similarity = sum(s["similarity"] for s in similarities) / len(similarities)
    
    return {
        "page_similarities": similarities,
        "average_similarity": avg_similarity
    }


def validate_conversion(original_pdf: str, converted_pdf: str, 
                       detailed_report: bool = False) -> dict:
    """
    Validate PDF form conversion quality.
    
    Args:
        original_pdf: Path to original PDF
        converted_pdf: Path to converted fillable PDF
        detailed_report: Whether to generate detailed analysis
        
    Returns:
        Dictionary containing validation results
    """
    
    original_pdf = Path(original_pdf)
    converted_pdf = Path(converted_pdf)
    
    if not original_pdf.exists():
        raise FileNotFoundError(f"Original PDF not found: {original_pdf}")
    if not converted_pdf.exists():
        raise FileNotFoundError(f"Converted PDF not found: {converted_pdf}")
    
    print(f"Validating conversion...")
    print(f"  Original: {original_pdf.name}")
    print(f"  Converted: {converted_pdf.name}")
    
    results = {
        "original_file": str(original_pdf),
        "converted_file": str(converted_pdf),
        "validation_checks": {}
    }
    
    # Check 1: Page count
    print("\n1. Checking page count...")
    orig_reader = PdfReader(str(original_pdf))
    conv_reader = PdfReader(str(converted_pdf))
    
    orig_pages = len(orig_reader.pages)
    conv_pages = len(conv_reader.pages)
    
    results["validation_checks"]["page_count"] = {
        "original": orig_pages,
        "converted": conv_pages,
        "match": orig_pages == conv_pages,
        "status": "✓ Pass" if orig_pages == conv_pages else "✗ Fail"
    }
    
    # Check 2: Form fields
    print("2. Checking form fields...")
    conv_fields = extract_form_fields(converted_pdf)
    
    results["validation_checks"]["form_fields"] = {
        "count": len(conv_fields),
        "has_fields": len(conv_fields) > 0,
        "status": "✓ Pass" if len(conv_fields) > 0 else "✗ Fail - No form fields found"
    }
    
    if conv_fields:
        # Group by type
        field_types = {}
        for field in conv_fields:
            if isinstance(field, dict):
                field_type = str(field.get("type", "Unknown"))
                field_types[field_type] = field_types.get(field_type, 0) + 1
        
        results["validation_checks"]["form_fields"]["types"] = field_types
    
    # Check 3: Visual similarity (if detailed report requested)
    if detailed_report:
        print("3. Performing visual similarity analysis...")
        visual_comparison = compare_visually(str(original_pdf), str(converted_pdf))
        results["validation_checks"]["visual_similarity"] = visual_comparison
        
        similarity_score = visual_comparison.get("average_similarity", 0)
        if similarity_score >= 95:
            status = "✓ Excellent"
        elif similarity_score >= 85:
            status = "✓ Good"
        elif similarity_score >= 70:
            status = "⚠ Fair"
        else:
            status = "✗ Poor"
        
        results["validation_checks"]["visual_similarity"]["status"] = status
    
    # Overall quality score
    checks_passed = sum(1 for check in results["validation_checks"].values() 
                       if isinstance(check, dict) and check.get("status", "").startswith("✓"))
    total_checks = len(results["validation_checks"])
    quality_score = (checks_passed / total_checks * 100) if total_checks > 0 else 0
    
    results["overall_quality"] = {
        "score": quality_score,
        "checks_passed": checks_passed,
        "total_checks": total_checks,
        "rating": "Excellent" if quality_score >= 90 else 
                 "Good" if quality_score >= 75 else
                 "Fair" if quality_score >= 60 else "Poor"
    }
    
    return results


def main():
    if len(sys.argv) < 3:
        print("Usage: python validate_conversion.py <original.pdf> <converted.pdf> [--detailed-report] [--output report.json]")
        print("\nValidates the quality of PDF form conversion.")
        sys.exit(1)
    
    original_pdf = sys.argv[1]
    converted_pdf = sys.argv[2]
    detailed_report = "--detailed-report" in sys.argv
    output_file = None
    
    # Parse arguments
    if "--output" in sys.argv:
        output_idx = sys.argv.index("--output")
        if output_idx + 1 < len(sys.argv):
            output_file = sys.argv[output_idx + 1]
    
    try:
        results = validate_conversion(original_pdf, converted_pdf, detailed_report)
        
        # Print summary
        print("\n" + "="*60)
        print("VALIDATION RESULTS")
        print("="*60)
        
        for check_name, check_data in results["validation_checks"].items():
            print(f"\n{check_name.replace('_', ' ').title()}:")
            if isinstance(check_data, dict):
                for key, value in check_data.items():
                    if key != "page_similarities" and key != "types":
                        print(f"  {key}: {value}")
                
                if "types" in check_data:
                    print("  Field types:")
                    for field_type, count in check_data["types"].items():
                        print(f"    {field_type}: {count}")
        
        print(f"\n{'='*60}")
        print(f"Overall Quality: {results['overall_quality']['rating']} ({results['overall_quality']['score']:.1f}%)")
        print(f"Checks passed: {results['overall_quality']['checks_passed']}/{results['overall_quality']['total_checks']}")
        print(f"{'='*60}")
        
        # Save report
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nDetailed report saved to: {output_file}")
        
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
