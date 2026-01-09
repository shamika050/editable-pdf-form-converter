# Field Properties Reference

Complete reference for all available field properties and configuration options.

## Common Properties

These properties apply to all field types:

### label (required)
**Type**: `string`  
**Description**: The field name displayed to users and used for identification.

```yaml
label: "Full Name"
```

### page (required)
**Type**: `integer` (1-indexed)  
**Description**: The PDF page number where the field appears.

```yaml
page: 1
```

### type (required)
**Type**: `string`  
**Values**: `text`, `textarea`, `number`, `date`, `email`, `phone`, `checkbox`, `radio`, `dropdown`, `signature`  
**Description**: The type of form field to create.

```yaml
type: text
```

### bounding_box (required)
**Type**: `object`  
**Description**: Position and dimensions using normalized coordinates (0.0-1.0).

```yaml
bounding_box:
  left: 0.15    # Distance from left edge
  top: 0.20     # Distance from top edge
  width: 0.35   # Field width
  height: 0.03  # Field height
```

### required
**Type**: `boolean`  
**Default**: `false`  
**Description**: Whether the field must be filled before submission.

```yaml
required: true
```

### read_only
**Type**: `boolean`  
**Default**: `false`  
**Description**: Makes the field non-editable (useful for pre-filled data).

```yaml
read_only: true
```

### default_value
**Type**: `string`  
**Description**: Pre-populated value for the field.

```yaml
default_value: "N/A"
```

Special values for date fields:
- `"today"` - Current date
- `"now"` - Current date and time

### tooltip
**Type**: `string`  
**Description**: Help text shown on hover.

```yaml
tooltip: "Enter your legal name as it appears on official documents"
```

## Text Field Properties

### max_length
**Type**: `integer`  
**Description**: Maximum number of characters allowed.

```yaml
max_length: 100
```

### password
**Type**: `boolean`  
**Default**: `false`  
**Description**: Masks input characters (for sensitive data).

```yaml
password: true
```

### multiline
**Type**: `boolean`  
**Default**: `false`  
**Description**: Allows multiple lines of text (alternative to `textarea` type).

```yaml
multiline: true
```

### alignment
**Type**: `string`  
**Values**: `left`, `center`, `right`  
**Default**: `left`

```yaml
alignment: center
```

## Validation Properties

### validation
**Type**: `string` (regex pattern)  
**Description**: Regular expression pattern for input validation.

```yaml
validation: "^[A-Z]{2}[0-9]{6}$"
```

### validation_message
**Type**: `string`  
**Description**: Error message shown when validation fails.

```yaml
validation_message: "Must be 2 letters followed by 6 numbers"
```

### min_value
**Type**: `number`  
**Applies to**: `number` fields  
**Description**: Minimum allowed value.

```yaml
min_value: 0
```

### max_value
**Type**: `number`  
**Applies to**: `number` fields  
**Description**: Maximum allowed value.

```yaml
max_value: 999
```

## Selection Field Properties

### options
**Type**: `array` of strings  
**Applies to**: `radio`, `dropdown`  
**Description**: List of available choices.

```yaml
options:
  - "Option 1"
  - "Option 2"
  - "Option 3"
```

### allow_custom
**Type**: `boolean`  
**Default**: `false`  
**Applies to**: `dropdown`  
**Description**: Allows users to enter custom values not in options list.

```yaml
allow_custom: true
```

### sort_options
**Type**: `boolean`  
**Default**: `false`  
**Description**: Automatically sorts options alphabetically.

```yaml
sort_options: true
```

## Checkbox Properties

### checked
**Type**: `boolean`  
**Default**: `false`  
**Description**: Whether checkbox is checked by default.

```yaml
checked: true
```

### group
**Type**: `string`  
**Description**: Groups checkboxes together (for multi-select scenarios).

```yaml
group: "interests"
```

## Signature Properties

### lock_after_signing
**Type**: `boolean`  
**Default**: `false`  
**Description**: Makes all fields read-only after signature is applied.

```yaml
lock_after_signing: true
```

### require_certificate
**Type**: `boolean`  
**Default**: `false`  
**Description**: Requires digital certificate for signature.

```yaml
require_certificate: true
```

## Styling Properties

### font_size
**Type**: `integer`  
**Default**: `12`  
**Description**: Font size in points.

```yaml
font_size: 14
```

### font_family
**Type**: `string`  
**Values**: `Helvetica`, `Times`, `Courier`, `Symbol`, `ZapfDingbats`  
**Default**: `Helvetica`

```yaml
font_family: "Times"
```

### font_color
**Type**: `string` (hex color)  
**Default**: `"#000000"` (black)

```yaml
font_color: "#003366"
```

### background_color
**Type**: `string` (hex color)  
**Description**: Field background color.

```yaml
background_color: "#F0F0F0"
```

### border_color
**Type**: `string` (hex color)  
**Default**: `"#000000"` (black)

```yaml
border_color: "#CCCCCC"
```

### border_width
**Type**: `integer`  
**Default**: `1`  
**Description**: Border thickness in points.

```yaml
border_width: 2
```

## Calculation Properties

### calculation
**Type**: `string` (JavaScript expression)  
**Description**: Formula for calculated fields.

```yaml
calculation: "field1 + field2"
```

### format
**Type**: `string`  
**Values**: `number`, `percent`, `currency`, `date`, `time`  
**Description**: Display format for calculated values.

```yaml
format: "currency"
```

## Conditional Properties

### visible_when
**Type**: `object`  
**Description**: Conditions for field visibility.

```yaml
visible_when:
  field: "employment_status"
  value: "employed"
```

### enabled_when
**Type**: `object`  
**Description**: Conditions for field being editable.

```yaml
enabled_when:
  field: "agree_to_terms"
  value: true
```

## Tab Order

### tab_index
**Type**: `integer`  
**Description**: Specifies the order fields are visited when pressing Tab.

```yaml
tab_index: 1
```

## Example: Comprehensive Field Definition

```yaml
- label: "Annual Income"
  page: 1
  type: number
  bounding_box:
    left: 0.15
    top: 0.40
    width: 0.25
    height: 0.03
  required: true
  default_value: "0"
  min_value: 0
  max_value: 9999999
  validation: "^[0-9]{1,7}$"
  validation_message: "Please enter a valid income amount"
  tooltip: "Enter your total annual income before taxes"
  font_size: 12
  font_family: "Helvetica"
  alignment: "right"
  tab_index: 5
  visible_when:
    field: "employment_status"
    value: "employed"
```

## Property Inheritance

Some properties can be set at the document level and inherited by all fields:

```yaml
document:
  filename: "form.pdf"
  defaults:
    font_size: 11
    font_family: "Helvetica"
    required: false
    border_color: "#999999"

fields:
  - label: "Name"
    # Inherits font_size: 11, font_family: "Helvetica", etc.
    page: 1
    type: text
    bounding_box: { left: 0.15, top: 0.20, width: 0.35, height: 0.03 }
    required: true  # Overrides inherited default
```

## Best Practices

1. **Always specify required properties** (label, page, type, bounding_box)
2. **Use validation** for data quality (email, phone, postal codes)
3. **Add tooltips** for complex fields to help users
4. **Set appropriate max_length** to prevent database issues
5. **Use read_only** for reference data that shouldn't change
6. **Group related fields** visually with consistent spacing
7. **Set tab_index** for logical navigation flow
8. **Test thoroughly** after applying properties
