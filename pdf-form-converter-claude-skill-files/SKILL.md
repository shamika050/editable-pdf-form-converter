---
name: pdf-form-converter
description: "Convert flat/scanned PDF documents into interactive fillable PDF forms using OCR-based field detection with AWS Textract and AI vision validation. Use when users need to: (1) Transform static PDFs into editable forms, (2) Detect and convert form fields (text inputs, checkboxes, signatures) automatically, (3) Digitize paper-based forms for electronic completion, (4) Validate form field detection accuracy, or (5) Batch convert multiple similar forms while preserving original styling and layout."
---

# PDF Form Converter

## Overview

Convert static PDF documents into interactive fillable forms through automated field detection using OCR (AWS Textract) and AI vision validation. Preserve original document styling while creating editable form elements.

## Workflow Decision Tree

Follow this decision tree to determine the appropriate conversion approach:

1. **Single form conversion with standard layout?**
   → Use Standard Conversion Workflow

2. **Complex form with tables, nested fields, or unusual layout?**
   → Use Advanced Conversion with Enhanced Validation

3. **Multiple similar forms to process?**
   → Use Batch Conversion Workflow

4. **Need to validate existing converted form?**
   → Use Validation-Only Workflow

5. **Form has accessibility requirements?**
   → Use Standard Conversion + Accessibility Enhancement

## Standard Conversion Workflow

For typical forms with standard layouts (employment applications, intake forms, contact sheets).

### Step 1: Analyze Source PDF

First, analyze the source PDF to understand its structure:

```python
python scripts/analyze_pdf.py <input.pdf>
```

This script outputs:
- Page count and dimensions
- Detected text regions
- Visual layout analysis
- Preliminary field candidates

### Step 2: OCR Field Detection

Run AWS Textract to detect form fields, labels, and structure:

```python
python scripts/textract_detection.py <input.pdf> --output-json fields.json
```

This generates:
- Field locations (bounding boxes)
- Associated labels
- Field types (text, checkbox, signature)
- Confidence scores

**Note:** Requires AWS credentials configured. Set environment variables:
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

### Step 3: AI Vision Validation

Use Claude's vision capabilities to validate and refine OCR results:

```python
python scripts/vision_validation.py <input.pdf> fields.json --output validated_fields.json
```

This script:
- Sends PDF pages as images to Claude
- Cross-validates field boundaries
- Corrects misaligned detections
- Identifies missed fields
- Improves label-to-field matching

### Step 4: Generate Interactive PDF

Create the fillable PDF with detected fields:

```python
python scripts/generate_fillable_pdf.py <input.pdf> validated_fields.json --output fillable_form.pdf
```

This produces an interactive PDF with:
- Text input fields
- Checkboxes and radio buttons
- Dropdown menus
- Signature fields
- Preserved styling and layout

### Step 5: Quality Check

Verify the conversion quality:

```python
python scripts/validate_conversion.py <original.pdf> <fillable_form.pdf>
```

This compares original and converted PDFs, reporting:
- Field alignment accuracy
- Missing or extra fields
- Style preservation score
- Overall conversion quality

## Advanced Conversion with Enhanced Validation

For complex forms with intricate layouts, tables, or nested structures.

### Enhanced Detection Strategy

1. **Run multi-pass OCR** with different confidence thresholds
2. **Apply table detection** for forms with tabular sections
3. **Use semantic analysis** to group related fields
4. **Validate with multiple vision passes** for high-stakes forms

```python
# Multi-pass detection for complex forms
python scripts/advanced_detection.py <input.pdf> \
  --multipass \
  --detect-tables \
  --semantic-grouping \
  --output complex_fields.json
```

### Manual Field Refinement

For critical forms requiring perfect accuracy:

```python
# Generate field mapping file for manual review/editing
python scripts/export_field_map.py validated_fields.json --output field_map.yaml

# After manual edits, regenerate PDF
python scripts/generate_fillable_pdf.py <input.pdf> field_map.yaml --output final_form.pdf
```

See `references/field_mapping_spec.md` for field mapping YAML format.

## Batch Conversion Workflow

Process multiple similar forms efficiently.

### Batch Processing

```python
python scripts/batch_convert.py <input_directory> \
  --output-dir converted_forms \
  --template-learning \
  --parallel 4
```

The `--template-learning` flag uses the first form as a template to improve detection on subsequent forms with similar layouts.

**Batch options:**
- `--parallel N`: Process N forms simultaneously
- `--validation-level [basic|full]`: Trade speed for accuracy
- `--preserve-structure`: Maintain directory structure in output
- `--report`: Generate conversion summary report

## Validation-Only Workflow

Validate existing converted forms without re-conversion.

```python
python scripts/validate_conversion.py \
  <original.pdf> \
  <converted.pdf> \
  --detailed-report \
  --visual-diff \
  --output validation_report.pdf
```

Generates report with:
- Side-by-side comparison
- Highlighted discrepancies
- Field accuracy metrics
- Recommendations for improvement

## Field Type Configuration

Configure how different field types are detected and created.

### Common Field Types

**Text Fields:**
- Single-line text inputs
- Multi-line text areas
- Numeric fields (with validation)
- Date fields (with date picker)
- Email fields (with validation)

**Selection Fields:**
- Checkboxes (single or grouped)
- Radio buttons (mutually exclusive groups)
- Dropdown menus (from detected options)

**Signature Fields:**
- Digital signature areas
- Initial fields
- Date-signed fields

### Field Properties

Configure field properties in the field mapping:

```yaml
fields:
  - label: "Patient Name"
    type: text
    required: true
    max_length: 100
    font_size: 12
  
  - label: "Insurance Provider"
    type: dropdown
    options: ["Blue Cross", "Aetna", "United", "Other"]
    required: true
  
  - label: "Consent Signature"
    type: signature
    required: true
    lock_after_signing: true
```

See `references/field_properties.md` for complete property specifications.

## Style Preservation

Maintain original document appearance during conversion.

### Preserved Elements

- **Typography**: Fonts, sizes, weights, colors
- **Layout**: Margins, spacing, alignment
- **Graphics**: Logos, watermarks, background images
- **Borders**: Form field borders and styling
- **Colors**: Background colors, field highlights

### Style Extraction

```python
python scripts/extract_styles.py <input.pdf> --output styles.json
```

Use extracted styles when generating fillable forms:

```python
python scripts/generate_fillable_pdf.py <input.pdf> fields.json \
  --styles styles.json \
  --output styled_form.pdf
```

## Accessibility Enhancement

Ensure converted forms meet digital accessibility standards.

```python
python scripts/add_accessibility.py <fillable_form.pdf> \
  --add-tags \
  --alt-text \
  --tab-order \
  --screen-reader-labels \
  --output accessible_form.pdf
```

Accessibility features added:
- PDF/UA compliance tagging
- Form field labels for screen readers
- Logical tab order
- Alt text for images
- Keyboard navigation support

## Troubleshooting

### Low Detection Confidence

If field detection is poor:
1. Check PDF quality (increase scan resolution if needed)
2. Use `--enhance-image` flag to improve image quality
3. Run advanced detection with `--multipass` option
4. Manually review and edit field mapping

### Misaligned Fields

If fields don't align properly:
1. Verify PDF page dimensions match original
2. Check for skewed/rotated source documents
3. Use vision validation to correct boundaries
4. Adjust field positions in field mapping YAML

### Missing Fields

If fields are not detected:
1. Check OCR confidence thresholds (lower if needed)
2. Verify field labels are clear and readable
3. Use semantic analysis for unlabeled fields
4. Manually add missing fields to field mapping

### Style Issues

If original styling is lost:
1. Ensure style extraction was successful
2. Verify font embedding in source PDF
3. Check for unsupported font types
4. Use `--embed-fonts` flag when generating

## Resources

### scripts/

Core conversion and validation scripts:

- `analyze_pdf.py` - PDF structure analysis
- `textract_detection.py` - AWS Textract field detection
- `vision_validation.py` - AI vision cross-validation
- `generate_fillable_pdf.py` - Interactive PDF creation
- `validate_conversion.py` - Quality validation
- `advanced_detection.py` - Complex form detection
- `batch_convert.py` - Batch processing
- `extract_styles.py` - Style preservation
- `add_accessibility.py` - Accessibility compliance

### references/

Detailed documentation:

- `field_mapping_spec.md` - Field mapping YAML format specification
- `field_properties.md` - Complete field property reference
- `textract_api.md` - AWS Textract API patterns and best practices
- `accessibility_standards.md` - PDF/UA compliance guidelines
