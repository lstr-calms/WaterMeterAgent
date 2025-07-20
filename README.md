# Water Meter Agent

A ReAct-pattern based AI agent for parsing and processing water meter readings from text or voice input. This intelligent agent can extract structured data from natural language descriptions of water meter readings.

## Features

- **Intelligent Text Parsing**: Uses the ReAct (Reasoning + Acting) pattern to systematically parse water meter readings
- **Voice Input Support**: Optional voice-to-text functionality using speech recognition
- **Fuzzy Matching**: Robust meter identification using fuzzy string matching
- **Multiple Units**: Supports various units (cubic meters, gallons, liters) with automatic standardization
- **Data Validation**: Range checking and duplicate detection
- **Structured Output**: Returns standardized JSON results with confidence scores

## ReAct Pattern Implementation

The agent follows a systematic Reasoning and Acting approach:

1. **Think**: Analyze current state and decide next action
2. **Act**: Execute the decided action using specialized tools
3. **Observe**: Process results and update state
4. **Repeat**: Continue until parsing is complete

## Supported Meter Tags

- `WM001`: Kitchen Water Meter
- `WM002`: Bathroom Water Meter  
- `WM003`: Garden Water Meter
- `WM004`: Main Water Supply
- `WM005`: Hot Water Heater

## Installation

1. Clone or download the project
2. Install required dependencies:
   ```bash
   pip install speech_recognition
   ```
3. For voice input, you may also need:
   ```bash
   pip install pyaudio
   ```

## Usage

### Basic Usage

```python
from water_meter_agent import WaterMeterAgent

# Create agent instance
agent = WaterMeterAgent()

# Parse a text reading
result = agent.parse_reading("Kitchen meter reading is 150.5 cubic meters today")

# Print structured result
print(json.dumps(result, indent=2))
```

### Voice Input

```python
# Enable voice input in the main section
use_voice = True  # Set to True for voice input
```

### Example Inputs

The agent can handle various input formats:

- `"WM001 reading 125.3 cubic meters"`
- `"Kitchen water meter shows 150 gallons"`
- `"Main supply reading: 45.7 m3 on 2025-01-15"`
- `"Bath meter 89.2 liters yesterday"`

## Output Format

```json
{
  "success": true,
  "confidence": 0.9,
  "meter": {
    "tag": "WM001",
    "description": "Kitchen Water Meter"
  },
  "reading": {
    "value": 150.5,
    "unit": "cubic_meters",
    "date": "2025-07-20"
  },
  "warnings": [],
  "raw_input": "Kitchen meter reading is 150.5 cubic meters today"
}
```

## Tools Used by the Agent

The agent employs several specialized tools:

### Text Processing Tools
- **`clean_text_tool`**: Removes noise and normalizes text format
- **`extract_numbers_tool`**: Extracts numeric values from text
- **`fuzzy_match_tool`**: Finds best matches using similarity scoring

### Data Processing Tools
- **`standardize_unit_tool`**: Converts unit variations to standard forms
- **`validate_range_tool`**: Checks if readings are within reasonable ranges
- **`parse_date_tool`**: Extracts dates or assigns current date

## Confidence Scoring

The agent calculates confidence based on successful identification of:
- Meter tag: +0.3
- Reading value: +0.4
- Unit: +0.2
- Date: +0.1

## Validation Features

- **Range Validation**: Ensures readings are within typical usage ranges
- **Duplicate Detection**: Maintains history to identify potential duplicate readings
- **Unit Standardization**: Converts various unit formats to standard forms

## Error Handling

The agent provides comprehensive error handling:
- Missing or invalid meter tags
- No numeric readings found
- Out-of-range values
- Duplicate reading warnings

## Extensibility

### Adding New Meter Tags

```python
# Add to meter_tags dictionary
self.meter_tags['WM006'] = 'Pool Water Meter'

# Add to name_to_tag for fuzzy matching
self.name_to_tag['POOL'] = 'WM006'
```

### Adding New Units

```python
# Extend unit_map in standardize_unit_tool
unit_map = {
    # ... existing units ...
    'CCF': 'hundred_cubic_feet',
    'HCF': 'hundred_cubic_feet'
}
```

## Dependencies

- Python 3.6+
- `re` (built-in)
- `json` (built-in)
- `typing` (built-in)
- `datetime` (built-in)
- `difflib` (built-in)
- `speech_recognition` (optional, for voice input)
- `pyaudio` (optional, for microphone access)

## Example Output

```
🏃 STARTING PARSE: 'Kitchen meter reading is 150.5 cubic meters'
============================================================

🧠 STEP 1
THINKING:
   Raw input needs cleaning to remove noise and normalize format
   DECISION: CLEAN_TEXT

🎬 ACTING:
   Using clean_text_tool
   Result: 'KITCHEN METER READING IS 150.5 CUBIC METERS'

🧠 STEP 2
THINKING:
   Need to identify which meter this reading belongs to
   DECISION: IDENTIFY_METER

🎬 ACTING:
   Using fuzzy_match_tool with meter tags
   No direct tag found, trying name-based lookup
   Found meter tag: WM001

📊 FINAL RESULT:
============================================================
✅ Success: true
📊 Confidence: 0.9
🏷️  Meter: WM001 (Kitchen Water Meter)
📏 Reading: 150.5 cubic_meters
📅 Date: 2025-07-20
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This project is open source. Please check the license file for details.

## Troubleshooting

### Voice Input Issues
- Ensure microphone permissions are granted
- Check that `pyaudio` is properly installed
- Verify microphone is working with other applications

### Recognition Issues
- Speak clearly and at moderate pace
- Ensure good audio quality (minimal background noise)
- Include meter identifier in speech ("Kitchen meter", "WM001", etc.)

### Range Validation Warnings
- Check if reading values are realistic for the meter type
- Verify units are correct
- Consider if this might be a cumulative vs. period reading

## Future Enhancements

- Database integration for reading history
- Support for multiple reading formats (CSV, JSON)
- Web interface for easier interaction
- Integration with IoT water meter devices
- Machine learning improvements for better recognition
- Support for additional languages
