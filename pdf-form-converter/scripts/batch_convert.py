#!/usr/bin/env python3
"""
Batch Conversion Script

Process multiple PDF forms efficiently with template learning capabilities.
"""

import sys
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import subprocess

def process_single_pdf(input_file: Path, output_dir: Path, template_data: dict = None) -> dict:
    """
    Process a single PDF file through the conversion pipeline.
    
    Args:
        input_file: Path to input PDF
        output_dir: Directory for output files
        template_data: Optional template data from previous conversion
        
    Returns:
        Dictionary with conversion results
    """
    
    print(f"\nProcessing: {input_file.name}")
    
    result = {
        "filename": input_file.name,
        "status": "success",
        "fields_detected": 0,
        "errors": []
    }
    
    try:
        # Create working directory for this file
        work_dir = output_dir / f".work_{input_file.stem}"
        work_dir.mkdir(exist_ok=True)
        
        # Step 1: Analyze PDF (optional for batch, but useful for stats)
        print(f"  [1/4] Analyzing structure...")
        analysis_file = work_dir / "analysis.json"
        analyze_cmd = [
            sys.executable,
            str(Path(__file__).parent / "analyze_pdf.py"),
            str(input_file),
            "--output", str(analysis_file)
        ]
        subprocess.run(analyze_cmd, check=True, capture_output=True)
        
        # Step 2: Field detection
        # If we have template data, we could use it to improve detection
        # For now, run standard detection
        print(f"  [2/4] Detecting fields...")
        fields_file = work_dir / "fields.json"
        
        # Check if Textract is available
        import os
        if os.getenv('AWS_ACCESS_KEY_ID'):
            # Use Textract
            detect_cmd = [
                sys.executable,
                str(Path(__file__).parent / "textract_detection.py"),
                str(input_file),
                "--output-json", str(fields_file)
            ]
        else:
            # Fallback to analysis-based detection
            print("    (AWS Textract not configured, using analysis-based detection)")
            # Use the analysis as fields
            with open(analysis_file, 'r') as f:
                analysis = json.load(f)
            
            # Convert analysis to fields format
            fields = {
                "fields": [],
                "statistics": {
                    "total_fields": 0
                }
            }
            
            for page in analysis.get("pages", []):
                for potential_field in page.get("potential_fields", []):
                    fields["fields"].append({
                        "label": potential_field.get("label", potential_field.get("text", "Field")),
                        "page": page["page_number"],
                        "field_type": potential_field.get("type", "text"),
                        "confidence": 70,  # Default confidence
                        "bounding_box": {
                            "left": 0.1,
                            "top": 0.1 + (len(fields["fields"]) * 0.05),
                            "width": 0.3,
                            "height": 0.03
                        }
                    })
            
            fields["statistics"]["total_fields"] = len(fields["fields"])
            
            with open(fields_file, 'w') as f:
                json.dump(fields, f, indent=2)
        
        # Load fields to get count
        with open(fields_file, 'r') as f:
            fields_data = json.load(f)
            result["fields_detected"] = fields_data.get("statistics", {}).get("total_fields", 0)
        
        if result["fields_detected"] == 0:
            result["status"] = "warning"
            result["errors"].append("No fields detected")
        
        # Step 3: Vision validation (skip in batch for speed unless requested)
        print(f"  [3/4] Validating fields...")
        validated_file = work_dir / "validated.json"
        validation_cmd = [
            sys.executable,
            str(Path(__file__).parent / "vision_validation.py"),
            str(input_file),
            str(fields_file),
            "--output", str(validated_file)
        ]
        subprocess.run(validation_cmd, check=True, capture_output=True)
        
        # Step 4: Generate fillable PDF
        print(f"  [4/4] Generating fillable PDF...")
        output_file = output_dir / f"{input_file.stem}_fillable.pdf"
        generate_cmd = [
            sys.executable,
            str(Path(__file__).parent / "generate_fillable_pdf.py"),
            str(input_file),
            str(validated_file),
            "--output", str(output_file)
        ]
        subprocess.run(generate_cmd, check=True, capture_output=True)
        
        result["output_file"] = str(output_file)
        print(f"  ✓ Complete: {result['fields_detected']} fields")
        
    except subprocess.CalledProcessError as e:
        result["status"] = "error"
        result["errors"].append(f"Pipeline error: {e.stderr.decode() if e.stderr else str(e)}")
        print(f"  ✗ Failed: {result['errors'][-1]}")
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(str(e))
        print(f"  ✗ Failed: {str(e)}")
    
    return result


def batch_convert(input_dir: str, output_dir: str, parallel: int = 1, 
                  template_learning: bool = False) -> dict:
    """
    Process multiple PDF files in batch.
    
    Args:
        input_dir: Directory containing input PDFs
        output_dir: Directory for output files
        parallel: Number of parallel processes
        template_learning: Use first form as template for subsequent forms
        
    Returns:
        Dictionary with batch processing results
    """
    
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all PDF files
    pdf_files = sorted(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        raise ValueError(f"No PDF files found in {input_dir}")
    
    print(f"="*60)
    print(f"BATCH PDF FORM CONVERSION")
    print(f"="*60)
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Files to process: {len(pdf_files)}")
    print(f"Parallel workers: {parallel}")
    print(f"Template learning: {'Enabled' if template_learning else 'Disabled'}")
    print(f"="*60)
    
    results = {
        "total_files": len(pdf_files),
        "processed": 0,
        "successful": 0,
        "warnings": 0,
        "failed": 0,
        "files": []
    }
    
    template_data = None
    
    if parallel > 1 and not template_learning:
        # Parallel processing
        with ProcessPoolExecutor(max_workers=parallel) as executor:
            futures = {
                executor.submit(process_single_pdf, pdf_file, output_dir, template_data): pdf_file
                for pdf_file in pdf_files
            }
            
            for future in as_completed(futures):
                result = future.result()
                results["files"].append(result)
                results["processed"] += 1
                
                if result["status"] == "success":
                    results["successful"] += 1
                elif result["status"] == "warning":
                    results["warnings"] += 1
                else:
                    results["failed"] += 1
    else:
        # Sequential processing (required for template learning)
        for pdf_file in pdf_files:
            result = process_single_pdf(pdf_file, output_dir, template_data)
            results["files"].append(result)
            results["processed"] += 1
            
            if result["status"] == "success":
                results["successful"] += 1
                
                # Update template data if template learning is enabled
                if template_learning and template_data is None:
                    # Use first successful conversion as template
                    print("\n  → Using this file as template for remaining conversions")
                    template_data = {"template": result}
            elif result["status"] == "warning":
                results["warnings"] += 1
            else:
                results["failed"] += 1
    
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python batch_convert.py <input_directory> [options]")
        print("\nOptions:")
        print("  --output-dir <dir>     Output directory (default: ./converted_forms)")
        print("  --parallel <N>         Number of parallel workers (default: 1)")
        print("  --template-learning    Use first form as template")
        print("  --report <file>        Save summary report to file")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = "./converted_forms"
    parallel = 1
    template_learning = False
    report_file = None
    
    # Parse arguments
    if "--output-dir" in sys.argv:
        idx = sys.argv.index("--output-dir")
        if idx + 1 < len(sys.argv):
            output_dir = sys.argv[idx + 1]
    
    if "--parallel" in sys.argv:
        idx = sys.argv.index("--parallel")
        if idx + 1 < len(sys.argv):
            parallel = int(sys.argv[idx + 1])
    
    if "--template-learning" in sys.argv:
        template_learning = True
        if parallel > 1:
            print("Note: Template learning requires sequential processing (parallel=1)")
            parallel = 1
    
    if "--report" in sys.argv:
        idx = sys.argv.index("--report")
        if idx + 1 < len(sys.argv):
            report_file = sys.argv[idx + 1]
    
    try:
        results = batch_convert(input_dir, output_dir, parallel, template_learning)
        
        # Print summary
        print("\n" + "="*60)
        print("BATCH CONVERSION SUMMARY")
        print("="*60)
        print(f"Total files: {results['total_files']}")
        print(f"Successful: {results['successful']}")
        print(f"Warnings: {results['warnings']}")
        print(f"Failed: {results['failed']}")
        print(f"="*60)
        
        # Show details of failed files
        failed_files = [f for f in results['files'] if f['status'] == 'error']
        if failed_files:
            print("\nFailed files:")
            for f in failed_files:
                print(f"  • {f['filename']}: {', '.join(f['errors'])}")
        
        # Save report
        if report_file:
            with open(report_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nDetailed report saved to: {report_file}")
        
        return 0 if results['failed'] == 0 else 1
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
