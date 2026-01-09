# AWS Textract API Reference

Guide for using AWS Textract for form field detection in PDF form conversion.

## Setup

### AWS Credentials

Set environment variables:
```bash
export AWS_ACCESS_KEY_ID=your_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

### IAM Permissions Required

Your AWS user/role needs these permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "textract:AnalyzeDocument",
        "textract:StartDocumentAnalysis",
        "textract:GetDocumentAnalysis"
      ],
      "Resource": "*"
    }
  ]
}
```

## API Methods

### AnalyzeDocument (Synchronous)

For documents up to 1 MB or 1 page:

```python
import boto3

textract = boto3.client('textract', region_name='us-east-1')

with open('document.pdf', 'rb') as file:
    response = textract.analyze_document(
        Document={'Bytes': file.read()},
        FeatureTypes=['FORMS']
    )
```

**Features:**
- `FORMS` - Detects form fields and key-value pairs
- `TABLES` - Extracts tables and their structure
- `SIGNATURES` - Identifies signature fields (preview)
- `LAYOUT` - Detects document layout elements

### StartDocumentAnalysis (Asynchronous)

For larger documents (up to 3000 pages, 500 MB):

```python
# Start analysis
response = textract.start_document_analysis(
    DocumentLocation={
        'S3Object': {
            'Bucket': 'my-bucket',
            'Name': 'document.pdf'
        }
    },
    FeatureTypes=['FORMS', 'TABLES']
)

job_id = response['JobId']

# Poll for results
import time
while True:
    response = textract.get_document_analysis(JobId=job_id)
    status = response['JobStatus']
    
    if status in ['SUCCEEDED', 'FAILED']:
        break
    
    time.sleep(5)

if status == 'SUCCEEDED':
    blocks = response['Blocks']
    # Process blocks...
```

## Response Structure

### Block Types

Textract returns data as "blocks" with different types:

#### PAGE
```python
{
    'BlockType': 'PAGE',
    'Id': 'page-1',
    'Page': 1,
    'Geometry': {...}
}
```

#### KEY_VALUE_SET
Form fields are represented as key-value pairs:

```python
# KEY block (label)
{
    'BlockType': 'KEY_VALUE_SET',
    'Id': 'key-1',
    'EntityTypes': ['KEY'],
    'Confidence': 98.5,
    'Relationships': [
        {
            'Type': 'VALUE',
            'Ids': ['value-1']
        },
        {
            'Type': 'CHILD',
            'Ids': ['word-1', 'word-2']
        }
    ],
    'Geometry': {
        'BoundingBox': {
            'Left': 0.1,
            'Top': 0.2,
            'Width': 0.3,
            'Height': 0.02
        }
    }
}

# VALUE block (input area)
{
    'BlockType': 'KEY_VALUE_SET',
    'Id': 'value-1',
    'EntityTypes': ['VALUE'],
    'Confidence': 95.2,
    'Relationships': [
        {
            'Type': 'CHILD',
            'Ids': ['word-3']
        }
    ],
    'Geometry': {...}
}
```

#### WORD
Text content:

```python
{
    'BlockType': 'WORD',
    'Id': 'word-1',
    'Text': 'Name:',
    'Confidence': 99.8,
    'Geometry': {...}
}
```

## Parsing Form Fields

### Extract Key-Value Pairs

```python
def parse_form_fields(blocks):
    """Parse Textract blocks into form fields."""
    
    # Create block map for relationships
    block_map = {block['Id']: block for block in blocks}
    
    # Find KEY_VALUE_SET blocks
    fields = []
    for block in blocks:
        if block['BlockType'] == 'KEY_VALUE_SET':
            if 'KEY' in block.get('EntityTypes', []):
                # This is a field label
                key_text = get_text(block, block_map)
                value_text = get_value(block, block_map)
                
                field = {
                    'label': key_text,
                    'value': value_text,
                    'confidence': block.get('Confidence', 0),
                    'bounding_box': block['Geometry']['BoundingBox'],
                    'page': block.get('Page', 1)
                }
                fields.append(field)
    
    return fields


def get_text(block, block_map):
    """Extract text from a block's CHILD relationships."""
    text = ''
    if 'Relationships' in block:
        for relationship in block['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    child = block_map.get(child_id)
                    if child and child['BlockType'] == 'WORD':
                        text += child.get('Text', '') + ' '
    return text.strip()


def get_value(key_block, block_map):
    """Get the value associated with a key block."""
    if 'Relationships' in key_block:
        for relationship in key_block['Relationships']:
            if relationship['Type'] == 'VALUE':
                for value_id in relationship['Ids']:
                    value_block = block_map.get(value_id)
                    if value_block:
                        return get_text(value_block, block_map)
    return ''
```

## Best Practices

### 1. Image Quality

Textract works best with:
- 300 DPI or higher
- Clear, unrotated images
- Good contrast
- Minimal noise/artifacts

Enhance images before sending:
```python
from PIL import Image, ImageEnhance

img = Image.open('document.pdf')
img = img.convert('L')  # Grayscale
enhancer = ImageEnhance.Contrast(img)
img = enhancer.enhance(1.5)
```

### 2. Confidence Thresholds

Filter results by confidence:
```python
HIGH_CONFIDENCE = 90
MEDIUM_CONFIDENCE = 75

fields = [f for f in fields if f['confidence'] >= MEDIUM_CONFIDENCE]
```

### 3. Error Handling

```python
from botocore.exceptions import ClientError

try:
    response = textract.analyze_document(...)
except ClientError as e:
    error_code = e.response['Error']['Code']
    
    if error_code == 'InvalidParameterException':
        print("Invalid document format or size")
    elif error_code == 'ThrottlingException':
        print("Rate limit exceeded, retry with backoff")
    elif error_code == 'ProvisionedThroughputExceededException':
        print("Quota exceeded")
    else:
        print(f"Textract error: {e}")
```

### 4. Rate Limits

Default limits (can be increased):
- Synchronous: 1 transaction/second
- Asynchronous: 2 concurrent jobs

Implement exponential backoff:
```python
import time
from botocore.exceptions import ClientError

def call_textract_with_retry(func, max_retries=5):
    for attempt in range(max_retries):
        try:
            return func()
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")
```

## Cost Optimization

### Pricing (as of 2024)
- Per-page pricing
- Additional charges for FORMS, TABLES features
- Free tier: 1,000 pages/month for 3 months

### Tips to Reduce Costs

1. **Batch processing**: Process multiple documents in single operations
2. **Pre-filtering**: Remove blank pages before analysis
3. **Feature selection**: Only request needed features (FORMS vs FORMS+TABLES)
4. **Caching**: Cache results for repeated analysis

```python
import hashlib
import json

def get_cached_result(pdf_bytes):
    """Check cache before calling Textract."""
    doc_hash = hashlib.md5(pdf_bytes).hexdigest()
    cache_file = f"cache/{doc_hash}.json"
    
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)
    
    # Call Textract
    result = textract.analyze_document(...)
    
    # Cache result
    os.makedirs('cache', exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(result, f)
    
    return result
```

## Troubleshooting

### Low Confidence Scores

**Problem**: Fields detected with low confidence (<75%)

**Solutions**:
1. Improve source document quality
2. Enhance image before processing
3. Use multiple detection passes
4. Verify with AI vision validation

### Missing Fields

**Problem**: Expected fields not detected

**Solutions**:
1. Check if labels are clearly visible
2. Ensure sufficient contrast
3. Verify field type (checkboxes may need different detection)
4. Use bounding box adjustment in post-processing

### Incorrect Field Boundaries

**Problem**: Bounding boxes don't match actual field locations

**Solutions**:
1. Cross-validate with vision models
2. Apply correction algorithms
3. Manual adjustment for critical fields

### Table Detection Issues

**Problem**: Form sections with tables not properly detected

**Solutions**:
1. Enable TABLES feature
2. Pre-process to enhance table borders
3. Use dedicated table extraction tools
4. Consider manual template for complex tables

## Integration with Form Converter

The form converter scripts use Textract in this workflow:

1. **textract_detection.py**: Calls Textract API and formats results
2. **vision_validation.py**: Cross-validates Textract output
3. **generate_fillable_pdf.py**: Uses validated fields to create form

Example integration:
```python
# Step 1: Textract detection
fields = detect_with_textract('input.pdf')

# Step 2: Vision validation
validated_fields = validate_with_vision('input.pdf', fields)

# Step 3: Generate form
create_fillable_pdf('input.pdf', validated_fields, 'output.pdf')
```
