import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from difflib import SequenceMatcher

# Tool Definitions (Simple Functions that the Agent can use)
def clean_text_tool(raw_text: str) -> str:
    """Tool: Remove noise and normalize text"""
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', raw_text.strip())
    # Remove special characters but keep important ones
    cleaned = re.sub(r'[^\w\s\.\-:/]', ' ', cleaned)
    # Normalize to uppercase for consistent processing
    return cleaned.upper()

def extract_numbers_tool(text: str) -> List[float]:
    """Tool: Extract all numeric values from text"""
    pattern = r'\d+\.?\d*'
    matches = re.findall(pattern, text)
    return [float(match) for match in matches]


def fuzzy_match_tool(text: str, dictionary: Dict[str, str], threshold: float = 0.6) -> Optional[str]:
    """Tool: Find best fuzzy match in dictionary"""
    best_match = None
    best_score = 0.0

    for key in dictionary.keys():
        if key in text:  # Exact match
            return key

        # Fuzzy matching
        score = SequenceMatcher(None, key, text).ratio()
        if score > best_score and score >= threshold:
            best_score = score
            best_match = key

    return best_match


def standardize_unit_tool(text: str) -> str:
    """Tool: Convert unit variations to standard form"""
    unit_map = {
        'CU M': 'cubic_meters',
        'CUBIC M': 'cubic_meters',
        'M3': 'cubic_meters',
        'CUBIC METER': 'cubic_meters',
        'CUBIC METERS': 'cubic_meters',
        'GAL': 'gallons',
        'GALLON': 'gallons',
        'GALLONS': 'gallons',
        'L': 'liters',
        'LITER': 'liters',
        'LITERS': 'liters'
    }

    for variant, standard in unit_map.items():
        if variant in text:
            return standard

    return 'cubic_meters'


def validate_range_tool(value: float, unit: str) -> Tuple[bool, str]:
    """Tool: Check if reading is within reasonable range"""
    ranges = {
        'cubic_meters': (0, 1000, "Typical home usage: 0-1000 cubic meters"),
        'gallons': (0, 264000, "Typical home usage: 0-264,000 gallons"),
        'liters': (0, 1000000, "Typical home usage: 0-1,000,000 liters")
    }

    if unit not in ranges:
        return True, f"Unknown unit '{unit}' - cannot validate range"

    min_val, max_val, description = ranges[unit]
    is_valid = min_val <= value <= max_val

    if is_valid:
        return True, f"Value {value} {unit} is within expected range"
    else:
        return False, f"Value {value} {unit} is outside expected range ({description})"


def parse_date_tool(text: str) -> str:
    """Tool: Extract date or return current date"""
    patterns = [
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{2}/\d{2}/\d{4})',
        r'(\d{1,2}/\d{1,2}/\d{4})',
        r'(\d{2}-\d{2}-\d{4})'
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)

    # Check for relative dates
    if 'TODAY' in text:
        return datetime.now().strftime('%Y-%m-%d')
    if 'YESTERDAY' in text:
        return (datetime.now().replace(day=datetime.now().day - 1)).strftime('%Y-%m-%d')

    # Default to current date
    return datetime.now().strftime('%Y-%m-%d')

# Agent Logic

class WaterMeterAgent:

    def __init__(self):
        # Meter tag knowledge base
        self.meter_tags = {
            'WM001': 'Kitchen Water Meter',
            'WM002': 'Bathroom Water Meter',
            'WM003': 'Garden Water Meter',
            'WM004': 'Main Water Supply',
            'WM005': 'Hot Water Heater'
        }

        # Reverse lookup for common names
        self.name_to_tag = {
            'KITCHEN': 'WM001',
            'BATH': 'WM002',
            'BATHROOM': 'WM002',
            'GARDEN': 'WM003',
            'YARD': 'WM003',
            'MAIN': 'WM004',
            'SUPPLY': 'WM004',
            'HEATER': 'WM005',
            'HOT': 'WM005'
        }

        self.parsing_history = []  # For duplicate detection

    def parse_reading(self, raw_input: str) -> Dict[str, Any]:
        """
        Main parsing method using ReAct pattern
        """
        print(f" STARTING PARSE: '{raw_input}'")
        print("=" * 60)

        # Initialize parsing state
        state = {
            'raw_input': raw_input,
            'cleaned_text': None,
            'meter_tag': None,
            'reading_value': None,
            'unit': None,
            'date': None,
            'warnings': [],
            'confidence': 0.0
        }

        # Execute ReAct loop
        max_steps = 8
        for step in range(1, max_steps + 1):
            print(f"\n STEP {step}")

            decision = self._think(state, step)
            if decision['action'] == 'COMPLETE':
                break
            elif decision['action'] == 'FAIL':
                state['warnings'].append('Parsing failed - insufficient data')
                break

            # Execute the decided action
            self._act(state, decision, step)

        return self._generate_result(state)

    def _think(self, state: Dict[str, Any], step: int) -> Dict[str, str]:
        """
        Reasoning phase: Decide what to do next based on current state
        """
        print("THINKING:")

        # Step 1: Always clean the input first
        if state['cleaned_text'] is None:
            thought = "Raw input needs cleaning to remove noise and normalize format"
            action = "CLEAN_TEXT"

        # Step 2: Identify the meter after cleaning
        elif state['meter_tag'] is None:
            if not state['cleaned_text'].strip():
                thought = "Cleaned text is empty - cannot proceed"
                action = "FAIL"
            else:
                thought = "Need to identify which meter this reading belongs to"
                action = "IDENTIFY_METER"

        # Step 3: Extract reading value
        elif state['reading_value'] is None:
            thought = "Need to extract the numerical reading from the text"
            action = "EXTRACT_READING"

        # Step 4: Determine unit
        elif state['unit'] is None:
            thought = "Need to identify and standardize the unit of measurement"
            action = "IDENTIFY_UNIT"

        # Step 5: Parse date
        elif state['date'] is None:
            thought = "Need to extract or assign a date for this reading"
            action = "PARSE_DATE"

        # Step 6: Validate the reading
        else:
            thought = "Have all basic data - now validate the reading makes sense"
            action = "VALIDATE"

        print(f"   {thought}")
        print(f"   DECISION: {action}")

        return {'thought': thought, 'action': action}

    def _act(self, state: Dict[str, Any], decision: Dict[str, str], step: int):
        """
        Action phase: Execute the decided action using appropriate tools
        """
        print(f" ACTING:")
        action = decision['action']

        if action == "CLEAN_TEXT":
            print(f"   Using clean_text_tool")
            result = clean_text_tool(state['raw_input'])
            print(f"   Result: '{result}'")
            state['cleaned_text'] = result

        elif action == "IDENTIFY_METER":
            print(f"   Using fuzzy_match_tool with meter tags")

            # Try direct tag matching first
            tag = fuzzy_match_tool(state['cleaned_text'], self.meter_tags)

            # If no direct tag match, try name-based lookup
            if not tag:
                print(f"   No direct tag found, trying name-based lookup")
                tag = fuzzy_match_tool(state['cleaned_text'], self.name_to_tag)

            if tag:
                print(f"   Found meter tag: {tag}")
                state['meter_tag'] = tag
                state['confidence'] += 0.3
            else:
                print(f"   No meter tag identified")
                state['meter_tag'] = 'UNKNOWN'
                state['warnings'].append('Could not identify meter tag')

        elif action == "EXTRACT_READING":
            print(f"    Using extract_numbers_tool")
            numbers = extract_numbers_tool(state['cleaned_text'])

            if numbers:
                # Take the first/largest meaningful number
                reading = max(numbers) if len(numbers) > 1 else numbers[0]
                print(f"    Extracted reading: {reading}")
                state['reading_value'] = reading
                state['confidence'] += 0.4
            else:
                print(f"    No numeric reading found")
                state['reading_value'] = 0.0
                state['warnings'].append('No numeric reading detected')

        elif action == "IDENTIFY_UNIT":
            print(f"    Using standardize_unit_tool")
            unit = standardize_unit_tool(state['cleaned_text'])
            print(f"    Standardized unit: {unit}")
            state['unit'] = unit
            state['confidence'] += 0.2

        elif action == "PARSE_DATE":
            print(f"    Using parse_date_tool")
            date = parse_date_tool(state['cleaned_text'])
            print(f"    Parsed date: {date}")
            state['date'] = date
            state['confidence'] += 0.1

        elif action == "VALIDATE":
            print(f"    Using validate_range_tool")
            is_valid, message = validate_range_tool(state['reading_value'], state['unit'])
            print(f"    Validation: {message}")

            if not is_valid:
                state['warnings'].append(message)

            # Check for potential duplicates
            reading_signature = f"{state['meter_tag']}_{state['reading_value']}_{state['date']}"
            if reading_signature in self.parsing_history:
                state['warnings'].append('Potential duplicate reading')
            else:
                self.parsing_history.append(reading_signature)
                # Keep history manageable
                if len(self.parsing_history) > 100:
                    self.parsing_history = self.parsing_history[-50:]

    def _generate_result(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate final structured result
        """
        print(f"\n FINAL RESULT:")
        print("=" * 60)

        success = (state['meter_tag'] and state['meter_tag'] != 'UNKNOWN'
                   and state['reading_value'] is not None
                   and state['reading_value'] > 0)

        result = {
            'success': success,
            'confidence': round(state['confidence'], 2),
            'meter': {
                'tag': state['meter_tag'],
                'description': self.meter_tags.get(state['meter_tag'], 'Unknown Meter')
            },
            'reading': {
                'value': state['reading_value'],
                'unit': state['unit'],
                'date': state['date']
            },
            'warnings': state['warnings'],
            'raw_input': state['raw_input']
        }

        # Display results
        print(f"✅ Success: {result['success']}")
        print(f"📊 Confidence: {result['confidence']}")
        print(f"🏷️  Meter: {result['meter']['tag']} ({result['meter']['description']})")
        print(f"📏 Reading: {result['reading']['value']} {result['reading']['unit']}")
        print(f"📅 Date: {result['reading']['date']}")

        if result['warnings']:
            print(f"⚠️  Warnings: {len(result['warnings'])}")
            for warning in result['warnings']:
                print(f"   - {warning}")

        return result

# Voice input support
try:
    import speech_recognition as sr
except ImportError:
    sr = None
    print("speech_recognition library not found. Voice input will be disabled.")

def get_voice_input() -> str:
    """Capture voice input from microphone and return as text."""
    if sr is None:
        print("speech_recognition is not available.")
        return ""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Please speak your water meter reading...")
        audio = recognizer.listen(source)
    try:
        text = recognizer.recognize_google(audio)
        print(f"You said: {text}")
        return text
    except sr.UnknownValueError:
        print("Could not understand audio.")
        return ""
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        return ""

# Test single case
if __name__ == "__main__":
    agent = WaterMeterAgent()
    # Use voice input if available, else fallback to text
    use_voice = True  # Set to True to enable voice input
    if use_voice:
        reading_text = get_voice_input()
    else:
        reading_text = get_voice_input()
    result = agent.parse_reading(reading_text)
    print(json.dumps(result, indent=2))