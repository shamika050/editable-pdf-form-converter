#!/usr/bin/env python3
"""
Main PDF Form Conversion Pipeline

Orchestrates the complete conversion workflow:
1. AWS Textract field detection
2. Intelligent field sizing
3. Claude vision validation
4. Fillable PDF generation with pdfrw
5. Quality validation

Usage:
    python convert_pdf_form.py input.pdf --output fillable.pdf
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any
import time


def run_conversion_pipeline(input_pdf: str, output_pdf: str,
                           skip_validation: bool = False,
                           skip_sizing: bool = False,
                           keep_intermediates: bool = False) -> Dict[str, Any]:
    """
    Run complete PDF form conversion pipeline.

    Args:
        input_pdf: Path to input PDF
        output_pdf: Path for output fillable PDF
        skip_validation: Skip Claude vision validation (faster but less accurate)
        skip_sizing: Skip intelligent field sizing
        keep_intermediates: Keep intermediate JSON files for debugging

    Returns:
        Dictionary with pipeline results and metrics
    """
    input_pdf = Path(input_pdf)
    output_pdf = Path(output_pdf)

    if not input_pdf.exists():
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")

    # Create working directory
    work_dir = Path(f".conversion_{input_pdf.stem}")
    work_dir.mkdir(exist_ok=True)

    scripts_dir = Path(__file__).parent

    print("=" * 70)
    print("PDF FORM CONVERSION PIPELINE")
    print("=" * 70)
    print(f"Input: {input_pdf}")
    print(f"Output: {output_pdf}")
    print("=" * 70)

    results = {
        "input_file": str(input_pdf),
        "output_file": str(output_pdf),
        "steps": {},
        "total_time": 0
    }

    start_time = time.time()

    # STEP 1: Textract field detection
    print("\n[1/5] AWS Textract Field Detection...")
    fields_file = work_dir / "textract_fields.json"

    step_start = time.time()
    try:
        result = subprocess.run([
            sys.executable,
            str(scripts_dir / "textract_detection.py"),
            str(input_pdf),
            "--output-json", str(fields_file)
        ], check=True, capture_output=True, text=True)

        print(result.stdout)

        with open(fields_file) as f:
            fields_data = json.load(f)

        results["steps"]["textract"] = {
            "duration": time.time() - step_start,
            "fields_detected": fields_data.get("statistics", {}).get("total_fields", 0),
            "status": "success"
        }
        print(f"  ✓ Detected {results['steps']['textract']['fields_detected']} fields")

    except subprocess.CalledProcessError as e:
        print(f"  ✗ Textract failed: {e}")
        print(e.stderr)
        results["steps"]["textract"] = {
            "duration": time.time() - step_start,
            "status": "failed",
            "error": str(e)
        }
        raise

    # STEP 2: Claude vision validation
    if not skip_validation:
        print("\n[2/5] Claude Vision API Validation...")
        validated_file = work_dir / "validated_fields.json"

        step_start = time.time()
        try:
            result = subprocess.run([
                sys.executable,
                str(scripts_dir / "vision_validation.py"),
                str(input_pdf),
                str(fields_file),
                "--output", str(validated_file)
            ], check=True, capture_output=True, text=True)

            print(result.stdout)

            with open(validated_file) as f:
                validated_data = json.load(f)

            results["steps"]["validation"] = {
                "duration": time.time() - step_start,
                "corrections": len(validated_data.get("corrections_made", [])),
                "status": "success"
            }
            print(f"  ✓ Applied {results['steps']['validation']['corrections']} corrections")

            current_fields_file = validated_file

        except subprocess.CalledProcessError as e:
            print(f"  ⚠ Vision validation failed: {e}")
            print(f"  → Continuing with Textract-only results")
            current_fields_file = fields_file
            results["steps"]["validation"] = {
                "duration": time.time() - step_start,
                "status": "failed",
                "error": str(e)
            }
    else:
        print("\n[2/5] Skipping Claude Vision Validation (--skip-validation)")
        current_fields_file = fields_file
        results["steps"]["validation"] = {"status": "skipped"}

    # STEP 3: Intelligent field sizing
    if not skip_sizing:
        print("\n[3/5] Intelligent Field Sizing...")
        sized_file = work_dir / "sized_fields.json"

        step_start = time.time()
        try:
            result = subprocess.run([
                sys.executable,
                str(scripts_dir / "field_sizing.py"),
                str(input_pdf),
                str(current_fields_file),
                "--output", str(sized_file)
            ], check=True, capture_output=True, text=True)

            print(result.stdout)

            results["steps"]["sizing"] = {
                "duration": time.time() - step_start,
                "status": "success"
            }
            print(f"  ✓ Optimized field dimensions")

            current_fields_file = sized_file

        except subprocess.CalledProcessError as e:
            print(f"  ⚠ Field sizing failed: {e}")
            print(f"  → Continuing with unsized fields")
            results["steps"]["sizing"] = {
                "duration": time.time() - step_start,
                "status": "failed",
                "error": str(e)
            }
    else:
        print("\n[3/5] Skipping Intelligent Field Sizing (--skip-sizing)")
        results["steps"]["sizing"] = {"status": "skipped"}

    # STEP 4: Generate fillable PDF
    print("\n[4/5] Generating Fillable PDF with pdfrw...")
    step_start = time.time()
    try:
        result = subprocess.run([
            sys.executable,
            str(scripts_dir / "generate_fillable_pdf.py"),
            str(input_pdf),
            str(current_fields_file),
            "--output", str(output_pdf)
        ], check=True, capture_output=True, text=True)

        print(result.stdout)

        results["steps"]["generation"] = {
            "duration": time.time() - step_start,
            "status": "success"
        }
        print(f"  ✓ Created fillable PDF")

    except subprocess.CalledProcessError as e:
        print(f"  ✗ PDF generation failed: {e}")
        print(e.stderr)
        results["steps"]["generation"] = {
            "duration": time.time() - step_start,
            "status": "failed",
            "error": str(e)
        }
        raise

    # STEP 5: Quality validation
    print("\n[5/5] Quality Validation...")
    validation_report = work_dir / "quality_report.json"

    step_start = time.time()
    try:
        result = subprocess.run([
            sys.executable,
            str(scripts_dir / "validate_conversion.py"),
            str(input_pdf),
            str(output_pdf),
            "--detailed-report",
            "--output", str(validation_report)
        ], check=True, capture_output=True, text=True)

        print(result.stdout)

        with open(validation_report) as f:
            quality_data = json.load(f)

        results["steps"]["quality_check"] = {
            "duration": time.time() - step_start,
            "score": quality_data.get("overall_quality", {}).get("score", 0),
            "status": "success"
        }
        print(f"  ✓ Quality score: {results['steps']['quality_check']['score']:.1f}%")

    except subprocess.CalledProcessError as e:
        print(f"  ⚠ Quality validation failed: {e}")
        results["steps"]["quality_check"] = {
            "duration": time.time() - step_start,
            "status": "failed",
            "error": str(e)
        }

    # Cleanup intermediate files if requested
    if not keep_intermediates:
        print("\nCleaning up intermediate files...")
        for file in work_dir.glob("*.json"):
            file.unlink()
        try:
            work_dir.rmdir()
        except:
            pass  # Directory might not be empty

    # Total time
    results["total_time"] = time.time() - start_time

    print("\n" + "=" * 70)
    print(f"✓ CONVERSION COMPLETE - Total time: {results['total_time']:.1f}s")
    print(f"  Output: {output_pdf}")
    if keep_intermediates:
        print(f"  Intermediate files: {work_dir}/")
    print("=" * 70)

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_pdf_form.py <input.pdf> [options]")
        print("\nOptions:")
        print("  --output <file>        Output PDF path (default: <input>_fillable.pdf)")
        print("  --skip-validation      Skip Claude vision validation (faster)")
        print("  --skip-sizing          Skip intelligent field sizing")
        print("  --keep-intermediates   Keep intermediate JSON files")
        print("\nExample:")
        print("  python convert_pdf_form.py application.pdf --output fillable_app.pdf")
        sys.exit(1)

    input_pdf = sys.argv[1]

    # Default output name
    output_pdf = Path(input_pdf).stem + "_fillable.pdf"
    skip_validation = False
    skip_sizing = False
    keep_intermediates = False

    # Parse arguments
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_pdf = sys.argv[idx + 1]

    if "--skip-validation" in sys.argv:
        skip_validation = True

    if "--skip-sizing" in sys.argv:
        skip_sizing = True

    if "--keep-intermediates" in sys.argv:
        keep_intermediates = True

    try:
        results = run_conversion_pipeline(
            input_pdf,
            output_pdf,
            skip_validation,
            skip_sizing,
            keep_intermediates
        )

        # Print summary
        print("\n" + "=" * 70)
        print("CONVERSION SUMMARY")
        print("=" * 70)
        for step_name, step_data in results["steps"].items():
            status = step_data.get("status", "unknown")
            duration = step_data.get("duration", 0)
            icon = "✓" if status == "success" else "⚠" if status == "failed" else "○"
            print(f"{icon} {step_name.capitalize()}: {status} ({duration:.1f}s)")

        return 0

    except Exception as e:
        print(f"\n✗ CONVERSION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
