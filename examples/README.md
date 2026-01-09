# Example PDF Forms

This directory contains example forms for testing the PDF form converter.

## Directory Structure

```
examples/
├── README.md                          # This file
├── simple_form.pdf                    # Basic test form (add your own)
├── complex_form.pdf                   # Multi-page form (add your own)
└── expected_outputs/                  # Expected conversion results
    ├── simple_form_fillable.pdf
    ├── simple_form_validation.json
    └── simple_form_quality_report.json
```

## Test Forms

### simple_form.pdf (To be added)
A basic single-page form for testing core functionality:
- 5-10 text fields
- 2-3 checkboxes
- 1 signature field
- Clear labels and spacing

**Use for**: Basic functionality testing

### complex_form.pdf (To be added)
A more complex multi-page form:
- 3+ pages
- Tables with multiple rows
- Nested fields
- Date fields
- Radio button groups

**Use for**: Advanced detection testing

## Usage

### Quick Test

Test the converter on an example form:

```bash
cd /Users/shamikadharmasiri/Documents/my-it-projects/editable-pdf-form-converter

# Convert an example form
python pdf-form-converter/scripts/convert_pdf_form.py examples/simple_form.pdf --output examples/test_output.pdf --keep-intermediates
```

### Validate Output

Compare your output against expected results:

```bash
# Visual comparison
python pdf-form-converter/scripts/validate_conversion.py \
    examples/simple_form.pdf \
    examples/test_output.pdf \
    --detailed-report
```

### Manual Verification Checklist

After converting a form, check:

- [ ] Output PDF opens without errors
- [ ] All expected fields are present and clickable
- [ ] Fields are in correct positions (not overlapping labels)
- [ ] Field types are correct (text, checkbox, signature)
- [ ] Original PDF appearance is preserved (no visual differences)
- [ ] Fields are sized appropriately for their space
- [ ] Text can be entered and saved in fields
- [ ] PDF can be printed with field values

## Adding Your Own Test PDFs

To add test forms:

1. Place PDF files in this directory
2. Name them descriptively (e.g., `employment_application.pdf`)
3. Run the converter
4. Manually verify the output
5. If correct, save to `expected_outputs/` for future comparison

## Common Test Scenarios

### Scenario 1: Simple Text Form
**Input**: Form with text fields and clear labels
**Expected**: All text fields detected, properly sized, no overlaps

### Scenario 2: Checkbox Form
**Input**: Form with multiple checkboxes and radio buttons
**Expected**: Checkboxes are square, properly positioned over checkbox graphics

### Scenario 3: Signature Form
**Input**: Form with signature lines
**Expected**: Signature fields are wide enough, positioned over signature lines

### Scenario 4: Dense Form
**Input**: Form with many fields close together
**Expected**: No field overlaps, all fields properly sized despite tight spacing

### Scenario 5: Scanned Form
**Input**: Scanned/image-based PDF form
**Expected**: Fields detected via OCR, positioned correctly despite image quality

## Validation Metrics

Good conversion quality indicators:

- **Field Detection Rate**: >95% of fields detected
- **Position Accuracy**: Fields within 2-3 pixels of ideal position
- **Visual PSNR**: >40 dB (indistinguishable from original)
- **Field Type Accuracy**: >98% correct field type classification
- **Processing Time**: <30 seconds per page

## Troubleshooting Test Failures

**All fields missed**:
- Check AWS Textract credentials
- Verify PDF is not encrypted or protected

**Some fields missed**:
- Fields may be too small or faint
- Try increasing DPI: `--dpi 400`

**Fields in wrong positions**:
- Check if PDF has unusual page size/rotation
- Verify field coordinates are normalized (0.0-1.0)

**Output PDF looks different**:
- Check PDF viewer (try Adobe Acrobat Reader)
- Ensure pdfrw is installed correctly

## Contributing Test Cases

If you encounter PDFs that don't convert well:

1. Simplify/anonymize the PDF
2. Document the issue
3. Include expected vs actual output
4. Submit as a test case for improvement

---

**Note**: Due to privacy, this repository doesn't include actual PDF forms. Please add your own test PDFs to this directory.
