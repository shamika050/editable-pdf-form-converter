#!/usr/bin/env python3
"""
PDF Structure Analysis Script

Analyzes PDF structure to understand layout, text regions, and preliminary field candidates.
"""

import sys
import json
from pathlib import Path

try:
    import pypdf
    from PIL import Image
    import pdf2image
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--break-system-packages", 
                          "pypdf", "pillow", "pdf2image"])
    import pypdf
    from PIL import Image
    import pdf2image


def analyze_pdf(pdf_path: str) -> dict:
    """Analyze PDF structure and return metadata."""
    
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    results = {
        "filename": pdf_path.name,
        "pages": [],
        "metadata": {},
        "statistics": {}
    }
    
    # Read PDF
    with open(pdf_path, 'rb') as f:
        reader = pypdf.PdfReader(f)
        
        # Extract metadata
        if reader.metadata:
            results["metadata"] = {
                "title": reader.metadata.get('/Title', ''),
                "author": reader.metadata.get('/Author', ''),
                "creator": reader.metadata.get('/Creator', ''),
                "producer": reader.metadata.get('/Producer', ''),
            }
        
        # Analyze each page
        total_text_length = 0
        for page_num, page in enumerate(reader.pages, 1):
            page_info = {
                "page_number": page_num,
                "width": float(page.mediabox.width),
                "height": float(page.mediabox.height),
                "rotation": page.get('/Rotate', 0),
            }
            
            # Extract text
            text = page.extract_text()
            page_info["text_length"] = len(text)
            page_info["has_text"] = len(text.strip()) > 0
            total_text_length += len(text)
            
            # Analyze text regions (simplified)
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            page_info["line_count"] = len(lines)
            
            # Detect potential form fields by looking for patterns
            potential_fields = []
            for i, line in enumerate(lines):
                # Look for colon patterns (Label:)
                if ':' in line and len(line) < 100:
                    potential_fields.append({
                        "type": "labeled_field",
                        "label": line.split(':')[0].strip(),
                        "line_number": i + 1
                    })
                # Look for checkbox patterns
                elif any(marker in line for marker in ['☐', '□', '[ ]', '(  )']):
                    potential_fields.append({
                        "type": "checkbox",
                        "text": line.strip(),
                        "line_number": i + 1
                    })
            
            page_info["potential_fields"] = potential_fields
            results["pages"].append(page_info)
        
        # Statistics
        results["statistics"] = {
            "total_pages": len(reader.pages),
            "total_text_length": total_text_length,
            "avg_text_per_page": total_text_length / len(reader.pages) if reader.pages else 0,
            "total_potential_fields": sum(len(p["potential_fields"]) for p in results["pages"])
        }
    
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_pdf.py <input.pdf> [--output output.json]")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    output_file = None
    
    # Parse arguments
    if "--output" in sys.argv:
        output_idx = sys.argv.index("--output")
        if output_idx + 1 < len(sys.argv):
            output_file = sys.argv[output_idx + 1]
    
    print(f"Analyzing PDF: {input_pdf}")
    
    try:
        results = analyze_pdf(input_pdf)
        
        # Output results
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nAnalysis saved to: {output_file}")
        else:
            print("\n" + "="*60)
            print("PDF ANALYSIS RESULTS")
            print("="*60)
            print(f"\nFilename: {results['filename']}")
            print(f"Pages: {results['statistics']['total_pages']}")
            print(f"Total potential fields detected: {results['statistics']['total_potential_fields']}")
            print(f"\nPage Details:")
            for page in results["pages"]:
                print(f"\n  Page {page['page_number']}:")
                print(f"    Dimensions: {page['width']:.1f} x {page['height']:.1f} pts")
                print(f"    Text lines: {page['line_count']}")
                print(f"    Potential fields: {len(page['potential_fields'])}")
                if page['potential_fields']:
                    print(f"    Field types: {', '.join(set(f['type'] for f in page['potential_fields']))}")
        
        return 0
        
    except Exception as e:
        print(f"Error analyzing PDF: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
