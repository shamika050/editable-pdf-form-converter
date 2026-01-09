# Field Mapping Specification

This document defines the YAML format for manually specifying or editing form field mappings.

## Format Overview

```yaml
document:
  filename: "original.pdf"
  pages: 1

fields:
  - label: string          # Field label/name (required)
    page: integer          # Page number (1-indexed, required)
    type: string           # Field type (required)
    bounding_box:          # Position and size (required)
      left: float          # Left position (0.0-1.0, normalized)
      top: float           # Top position (0.0-1.0, normalized)
      width: float         # Width (0.0-1.0, normalized)
      height: float        # Height (0.0-1.0, normalized)
    required: boolean      # Whether field is required (optional, default: false)
    default_value: string  # Default value (optional)
    max_length: integer    # Maximum character length (optional, text fields only)
    options: list          # Options for dropdown/radio (optional)
    validation: string     # Validation pattern (optional)
    font_size: integer     # Font size in points (optional, default: 12)
    read_only: boolean     # Make field read-only (optional, default: false)
```

## Field Types

### text
Standard single-line text input.

```yaml
- label: "Full Name"
  page: 1
  type: text
  bounding_box:
    left: 0.15
    top: 0.20
    width: 0.35
    height: 0.03
  required: true
  max_length: 100
```

### textarea
Multi-line text input for longer content.

```yaml
- label: "Comments"
  page: 1
  type: textarea
  bounding_box:
    left: 0.15
    top: 0.50
    width: 0.70
    height: 0.15
  max_length: 500
```

### number
Numeric input with optional validation.

```yaml
- label: "Age"
  page: 1
  type: number
  bounding_box:
    left: 0.15
    top: 0.30
    width: 0.10
    height: 0.03
  validation: "^[0-9]{1,3}$"
```

### date
Date input field.

```yaml
- label: "Date of Birth"
  page: 1
  type: date
  bounding_box:
    left: 0.15
    top: 0.35
    width: 0.20
    height: 0.03
  required: true
```

### email
Email input with validation.

```yaml
- label: "Email Address"
  page: 1
  type: email
  bounding_box:
    left: 0.15
    top: 0.40
    width: 0.40
    height: 0.03
  required: true
  validation: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
```

### phone
Phone number input.

```yaml
- label: "Phone Number"
  page: 1
  type: phone
  bounding_box:
    left: 0.15
    top: 0.45
    width: 0.25
    height: 0.03
  validation: "^\\(?[0-9]{3}\\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}$"
```

### checkbox
Single checkbox or grouped checkboxes.

```yaml
- label: "Agree to Terms"
  page: 1
  type: checkbox
  bounding_box:
    left: 0.15
    top: 0.70
    width: 0.03
    height: 0.03
  required: true
```

### radio
Radio button group (mutually exclusive options).

```yaml
- label: "Gender"
  page: 1
  type: radio
  options:
    - "Male"
    - "Female"
    - "Other"
  bounding_box:
    left: 0.15
    top: 0.55
    width: 0.50
    height: 0.08
```

### dropdown
Dropdown/select menu.

```yaml
- label: "State"
  page: 1
  type: dropdown
  options:
    - "California"
    - "New York"
    - "Texas"
    - "Florida"
  bounding_box:
    left: 0.15
    top: 0.60
    width: 0.25
    height: 0.03
  required: true
```

### signature
Digital signature field.

```yaml
- label: "Applicant Signature"
  page: 2
  type: signature
  bounding_box:
    left: 0.15
    top: 0.80
    width: 0.35
    height: 0.08
  required: true
```

## Coordinate System

The bounding box uses normalized coordinates (0.0 to 1.0):
- `left`: Distance from left edge of page (0.0 = left edge, 1.0 = right edge)
- `top`: Distance from top edge of page (0.0 = top edge, 1.0 = bottom edge)
- `width`: Width as proportion of page width
- `height`: Height as proportion of page height

### Example Positions

```
Top-left corner:     left: 0.0,  top: 0.0
Top-right corner:    left: 0.9,  top: 0.0
Center:              left: 0.4,  top: 0.45
Bottom-left corner:  left: 0.0,  top: 0.95
```

## Complete Example

```yaml
document:
  filename: "job_application.pdf"
  pages: 2

fields:
  # Page 1 - Personal Information
  - label: "First Name"
    page: 1
    type: text
    bounding_box:
      left: 0.15
      top: 0.15
      width: 0.25
      height: 0.03
    required: true
    max_length: 50
  
  - label: "Last Name"
    page: 1
    type: text
    bounding_box:
      left: 0.45
      top: 0.15
      width: 0.25
      height: 0.03
    required: true
    max_length: 50
  
  - label: "Email"
    page: 1
    type: email
    bounding_box:
      left: 0.15
      top: 0.22
      width: 0.40
      height: 0.03
    required: true
  
  - label: "Position Applied For"
    page: 1
    type: dropdown
    options:
      - "Software Engineer"
      - "Product Manager"
      - "Designer"
      - "Other"
    bounding_box:
      left: 0.15
      top: 0.30
      width: 0.30
      height: 0.03
    required: true
  
  # Page 2 - Agreements
  - label: "Agree to Background Check"
    page: 2
    type: checkbox
    bounding_box:
      left: 0.15
      top: 0.70
      width: 0.03
      height: 0.03
    required: true
  
  - label: "Signature"
    page: 2
    type: signature
    bounding_box:
      left: 0.15
      top: 0.85
      width: 0.35
      height: 0.08
    required: true
  
  - label: "Date Signed"
    page: 2
    type: date
    bounding_box:
      left: 0.55
      top: 0.85
      width: 0.20
      height: 0.03
    required: true
    default_value: "today"
```

## Validation Patterns

Regular expressions for common validation:

- **Email**: `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`
- **Phone (US)**: `^\(?[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}$`
- **ZIP Code**: `^[0-9]{5}(-[0-9]{4})?$`
- **Date (MM/DD/YYYY)**: `^(0[1-9]|1[0-2])\/(0[1-9]|[12][0-9]|3[01])\/\d{4}$`
- **SSN**: `^[0-9]{3}-[0-9]{2}-[0-9]{4}$`
- **URL**: `^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b`

## Tips for Manual Editing

1. **Positioning**: Use a PDF viewer with rulers or coordinates to determine accurate positions
2. **Alignment**: Keep fields aligned by using consistent left/top values
3. **Spacing**: Standard vertical spacing between fields is 0.05-0.07
4. **Field heights**: 0.03 for single-line fields, 0.05-0.15 for multi-line
5. **Testing**: Always test the generated PDF to verify field positions
