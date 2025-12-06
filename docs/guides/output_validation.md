# Output Validation

## Overview

The system implements comprehensive Pydantic-based output validation to ensure agent tool outputs are consistent, reliable, and production-ready. This validation layer prevents malformed or low-quality data from propagating through the workflow.

## Classification Tool Validation

### Validation Schema

The `ClassificationOutput` Pydantic model enforces strict output structure:

```python
class ClassificationOutput(BaseModel):
    category: str
    severity: Literal["critical", "high", "medium", "low"]
    priority: str
    required_actions: list[str] = Field(min_length=3, max_length=20)
    reasoning: str = Field(min_length=20, max_length=500)
```

### Validation Features

#### 1. Priority/Severity Auto-Correction

**Purpose**: Ensures priority levels match severity classification

**How it works**:
- Critical incidents → P1 (Immediate Response)
- High incidents → P2 (Urgent Response)
- Medium incidents → P3 (Standard Response)
- Low incidents → P4 (Routine Response)

**Example**:
```python
# Input with mismatched priority
{
    "severity": "critical",
    "priority": "P4 - Low"  # Wrong!
}

# Auto-corrected output
{
    "severity": "critical",
    "priority": "P1 - Immediate Response (within 1 hour)"  # Fixed!
}
```

**Logging**: Warnings logged when auto-correction occurs:
```
WARNING: Priority 'P4 - Low' doesn't match severity 'critical'. Expected to start with 'P1'
```

#### 2. Action Deduplication and Quality Control

**Purpose**: Ensures all required actions are unique, meaningful, and actionable

**Validation rules**:
- **Deduplication**: Removes duplicate actions while preserving order
- **Minimum length**: Actions must be at least 5 characters
- **Whitespace trimming**: Removes extra whitespace
- **Minimum count**: At least 3 actions required
- **Maximum count**: No more than 20 actions

**Example**:
```python
# Input with duplicates and short actions
required_actions = [
    "Deploy containment booms",
    "Go",  # Too short - removed
    "Notify Environment Agency",
    "Deploy containment booms",  # Duplicate - removed
    "Call",  # Too short - removed
    "Monitor water quality"
]

# Validated output
required_actions = [
    "Deploy containment booms",
    "Notify Environment Agency",
    "Monitor water quality"
]
```

**Logging**: 
```
WARNING: Removed duplicate actions from classification
WARNING: Removed short action: 'Go'
WARNING: Removed short action: 'Call'
```

#### 3. Reasoning Quality Validation

**Purpose**: Prevents placeholder or empty reasoning text

**Validation rules**:
- **Minimum length**: 20 characters
- **Maximum length**: 500 characters
- **No placeholders**: Rejects "TODO:", "TBD", "N/A", "None" at the start
- **Whitespace trimming**: Strips leading/trailing whitespace

**Example**:
```python
# Invalid reasoning (rejected)
reasoning = "TODO: Add reasoning here"  # ❌ Placeholder
reasoning = "Short"  # ❌ Too short
reasoning = "N/A"  # ❌ Placeholder

# Valid reasoning (accepted)
reasoning = "Incident classified as high severity water_pollution..."  # ✅
```

**Error messages**:
- Empty: `"Reasoning cannot be empty"`
- Placeholder: `"Reasoning appears to be placeholder text: TODO: Add reasoning here"`
- Too short: `"String should have at least 20 characters"`

### Fallback Mechanism

If validation fails (e.g., LLM returns malformed output), the tool returns safe defaults:

```python
{
    "category": incident_type,
    "severity": "medium",
    "priority": "P3 - Standard Response (within 24 hours)",
    "required_actions": [
        "Initial assessment and documentation",
        "Notify relevant authorities",
        "Monitor situation for changes"
    ],
    "reasoning": f"Default classification applied for {incident_type} incident."
}
```

**Logging**: 
```
ERROR: Classification output validation failed: [error details]
INFO: Using fallback classification for [incident]
```

## Testing

### Comprehensive Test Suite

Location: `tests/unit/test_classification_validation.py`

**Test coverage** (19 tests):

1. **Valid Output Tests**
   - `test_valid_classification_output` - Baseline validation
   - `test_classify_incident_returns_valid_output` - Integration test

2. **Priority/Severity Correction**
   - `test_priority_severity_mismatch_auto_correction` - Auto-fix mismatches
   - `test_high_severity_priority_correction` - P2 for high
   - `test_medium_severity_priority_correction` - P3 for medium
   - `test_low_severity_priority_correction` - P4 for low

3. **Action Validation**
   - `test_duplicate_actions_removed` - Deduplication
   - `test_short_actions_removed` - Minimum length enforcement
   - `test_minimum_actions_required` - At least 3 actions
   - `test_maximum_actions_enforced` - No more than 20 actions
   - `test_mixed_valid_invalid_actions` - Mixed input cleanup

4. **Reasoning Validation**
   - `test_reasoning_too_short` - Minimum length
   - `test_reasoning_placeholder_rejected` - Placeholder detection

5. **Edge Cases**
   - `test_exactly_three_actions` - Boundary test
   - `test_exactly_twenty_actions` - Boundary test
   - `test_reasoning_exactly_twenty_chars` - Boundary test

6. **Integration Tests**
   - `test_classify_incident_fallback_on_validation_error` - Fallback mechanism
   - `test_critical_incident_gets_p1_priority` - End-to-end validation

### Running Tests

```bash
# Run all validation tests
docker exec defra-agent-api pytest tests/unit/test_classification_validation.py -v

# Run specific test class
docker exec defra-agent-api pytest tests/unit/test_classification_validation.py::TestClassificationOutputValidation -v

# Run with coverage
docker exec defra-agent-api pytest tests/unit/test_classification_validation.py --cov=app.tools.classification
```

## Benefits

### 1. Data Quality

- **Consistent format**: All outputs match expected schema
- **No garbage data**: Filters out malformed or low-quality content
- **Automatic correction**: Fixes common issues without failing

### 2. System Reliability

- **Graceful degradation**: Fallback ensures system continues operating
- **Predictable behavior**: Downstream components receive validated data
- **Error visibility**: Logging tracks validation issues

### 3. Debugging Support

- **Clear error messages**: Pydantic provides detailed validation errors
- **Comprehensive logging**: Tracks auto-corrections and failures
- **Test coverage**: 19 tests verify all validation logic

### 4. Production Readiness

- **Type safety**: Literal types prevent invalid values
- **Constraint enforcement**: Field validators ensure quality
- **Observability**: Logging enables monitoring and alerting

## Future Extensions

### Other Tools

Similar validation can be added to:

1. **Spatial Context Tool**
   ```python
   class SpatialContextOutput(BaseModel):
       nearby_sites: list[str] = Field(min_length=0, max_length=50)
       environmental_sensitivity: Literal["very_high", "high", "medium", "low"]
       buffer_zones: list[dict] = Field(min_length=0, max_length=10)
   ```

2. **Notification Tool**
   ```python
   class NotificationOutput(BaseModel):
       recipients: list[str] = Field(min_length=1, max_length=20)
       notification_type: Literal["email", "sms", "webhook"]
       delivery_status: Literal["sent", "pending", "failed"]
   ```

3. **Guidance Search Tool**
   ```python
   class GuidanceSearchOutput(BaseModel):
       relevant_regulations: list[str] = Field(min_length=0, max_length=10)
       compliance_requirements: list[str] = Field(min_length=1, max_length=15)
       reference_documents: list[dict] = Field(min_length=0, max_length=20)
   ```

### Advanced Validation

Consider adding:

- **Cross-field validation**: Ensure multiple fields are consistent
- **External validation**: Check against external APIs/databases
- **Semantic validation**: Use embeddings to verify content quality
- **Rate limiting**: Prevent abuse with input validation
- **Schema versioning**: Support multiple validation versions

## Implementation Notes

### Pydantic V2

The implementation uses Pydantic V2 with modern syntax:

- `field_validator` instead of `@validator` decorator
- `model_dump()` instead of `.dict()` method
- `min_length`/`max_length` instead of `min_items`/`max_items`
- `info.data` instead of `values` parameter

### Performance

- **Minimal overhead**: Validation adds ~5-10ms per classification
- **Early failure**: Invalid data fails fast before downstream processing
- **Caching**: Pydantic models are compiled and cached

### Logging

All validation operations log to `app.tools.classification` logger:

```python
logger = logging.getLogger(__name__)
```

**Log levels**:
- `INFO`: Successful validation, fallback usage
- `WARNING`: Auto-corrections, data cleanup
- `ERROR`: Validation failures requiring fallback

## Example Usage

```python
from app.tools.classification import classify_incident

# Call the tool
result = classify_incident.invoke({
    "incident_type": "water_pollution",
    "description": "Chemical spill in river",
    "location": "River Thames",
    "urgency": "high"
})

# Result is guaranteed to be valid
assert result["severity"] in ["critical", "high", "medium", "low"]
assert len(result["required_actions"]) >= 3
assert len(result["reasoning"]) >= 20

# Priority matches severity
if result["severity"] == "critical":
    assert result["priority"].startswith("P1")
```

## References

- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Field Validators](https://docs.pydantic.dev/latest/concepts/validators/)
- [Classification Tool Source](../../app/tools/classification.py)
- [Validation Tests](../../tests/unit/test_classification_validation.py)
