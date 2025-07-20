import re
import json
import os
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime
from difflib import SequenceMatcher

# Voice input support - Enhanced version
from voice_input import VoiceInputHandler

def get_voice_input() -> str:
    """Capture voice input from microphone and return as text."""
    handler = VoiceInputHandler()
    result = handler.get_voice_input_interactive()
    return result or ""

# Simple Tool Classes (LangChain-inspired but without inheritance issues)
class SimpleTool:
    """Base class for simple tools"""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def run(self, input_text: str) -> str:
        """Run the tool with input text"""
        raise NotImplementedError

class CleanTextTool(SimpleTool):
    def __init__(self):
        super().__init__(
            name="clean_text",
            description="Remove noise and normalize text format for water meter reading parsing"
        )
    
    def run(self, raw_text: str) -> str:
        """Remove extra whitespace and normalize text"""
        print(f"🧹 Cleaning text: '{raw_text}'")
        cleaned = re.sub(r'\s+', ' ', raw_text.strip())
        cleaned = re.sub(r'[^\w\s\.\-:/]', ' ', cleaned)
        result = cleaned.upper()
        print(f"   ✅ Cleaned: '{result}'")
        return result

class ExtractNumbersTool(SimpleTool):
    def __init__(self):
        super().__init__(
            name="extract_numbers",
            description="Extract all numeric values from text, useful for finding water meter readings"
        )
    
    def run(self, text: str) -> str:
        """Extract numeric values from text"""
        print(f"🔢 Extracting numbers from: '{text}'")
        pattern = r'\d+\.?\d*'
        matches = re.findall(pattern, text)
        numbers = [float(match) for match in matches]
        print(f"   ✅ Found numbers: {numbers}")
        return json.dumps(numbers)

class MeterIdentificationTool(SimpleTool):
    def __init__(self, meter_tags: Dict[str, str], name_to_tag: Dict[str, str]):
        super().__init__(
            name="identify_meter",
            description="Identify water meter tag from text using fuzzy matching"
        )
        self.meter_tags = meter_tags
        self.name_to_tag = name_to_tag
    
    def run(self, text: str) -> str:
        """Find best meter match"""
        print(f"🏷️  Identifying meter from: '{text}'")
        
        # Try direct tag matching first
        for tag in self.meter_tags.keys():
            if tag in text:
                print(f"   ✅ Direct tag match: {tag}")
                return tag
        
        # Try fuzzy matching with meter tags
        best_match = None
        best_score = 0.0
        threshold = 0.6
        
        for tag in self.meter_tags.keys():
            score = SequenceMatcher(None, tag, text).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = tag
        
        if best_match:
            print(f"   ✅ Fuzzy tag match: {best_match} (score: {best_score:.2f})")
            return best_match
        
        # Try name-based lookup
        for name, tag in self.name_to_tag.items():
            if name in text:
                print(f"   ✅ Name-based match: {name} -> {tag}")
                return tag
        
        # Try fuzzy matching with names
        for name in self.name_to_tag.keys():
            score = SequenceMatcher(None, name, text).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = self.name_to_tag[name]
        
        if best_match:
            print(f"   ✅ Fuzzy name match: {best_match} (score: {best_score:.2f})")
            return best_match
        
        print(f"   ❌ No meter identified")
        return "UNKNOWN"

class StandardizeUnitTool(SimpleTool):
    def __init__(self):
        super().__init__(
            name="standardize_unit",
            description="Convert unit variations to standard form (cubic_meters, gallons, liters)"
        )
    
    def run(self, text: str) -> str:
        """Convert unit variations to standard form"""
        print(f"📏 Standardizing unit from: '{text}'")
        
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
                print(f"   ✅ Found unit: {variant} -> {standard}")
                return standard

        print(f"   ⚠️  No unit found, defaulting to cubic_meters")
        return 'cubic_meters'

class ValidateRangeTool(SimpleTool):
    def __init__(self):
        super().__init__(
            name="validate_range",
            description="Check if a water meter reading is within reasonable range for the given unit"
        )
    
    def run(self, value_unit: str) -> str:
        """Check if reading is within reasonable range"""
        print(f"✅ Validating range for: {value_unit}")
        
        try:
            if ',' in value_unit:
                parts = value_unit.split(',')
                value = float(parts[0].strip())
                unit = parts[1].strip()
            else:
                # Try to parse JSON format
                data = json.loads(value_unit)
                value = data.get('value', 0)
                unit = data.get('unit', 'cubic_meters')
        except:
            print(f"   ❌ Invalid format, expected 'value,unit' or JSON")
            return "INVALID_FORMAT"
        
        ranges = {
            'cubic_meters': (0, 1000, "Typical home usage: 0-1000 cubic meters"),
            'gallons': (0, 264000, "Typical home usage: 0-264,000 gallons"),
            'liters': (0, 1000000, "Typical home usage: 0-1,000,000 liters")
        }

        if unit not in ranges:
            print(f"   ⚠️  Unknown unit '{unit}' - cannot validate range")
            return f"UNKNOWN_UNIT"

        min_val, max_val, description = ranges[unit]
        is_valid = min_val <= value <= max_val

        if is_valid:
            print(f"   ✅ Valid: {value} {unit} is within expected range")
            return "VALID"
        else:
            print(f"   ⚠️  Warning: {value} {unit} is outside expected range ({description})")
            return "OUT_OF_RANGE"

class ParseDateTool(SimpleTool):
    def __init__(self):
        super().__init__(
            name="parse_date",
            description="Extract date from text or return current date in YYYY-MM-DD format"
        )
    
    def run(self, text: str) -> str:
        """Extract date or return current date"""
        print(f"📅 Parsing date from: '{text}'")
        
        patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{2}/\d{2}/\d{4})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(\d{2}-\d{2}-\d{4})'
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                print(f"   ✅ Found date: {date_str}")
                return date_str

        # Check for relative dates
        if 'TODAY' in text:
            date_str = datetime.now().strftime('%Y-%m-%d')
            print(f"   ✅ Today: {date_str}")
            return date_str
        if 'YESTERDAY' in text:
            date_str = (datetime.now().replace(day=datetime.now().day - 1)).strftime('%Y-%m-%d')
            print(f"   ✅ Yesterday: {date_str}")
            return date_str

        # Default to current date
        date_str = datetime.now().strftime('%Y-%m-%d')
        print(f"   ⚠️  No date found, using current: {date_str}")
        return date_str

class LocalLangChainStyleAgent:
    """
    Local agent that uses LangChain-style tools and ReAct pattern without external dependencies
    """
    
    def __init__(self):
        print("🔧 Initializing Local LangChain-Style Agent...")
        
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
        
        # Initialize tools (LangChain-style but local)
        self.tools = {
            'clean_text': CleanTextTool(),
            'extract_numbers': ExtractNumbersTool(),
            'identify_meter': MeterIdentificationTool(self.meter_tags, self.name_to_tag),
            'standardize_unit': StandardizeUnitTool(),
            'validate_range': ValidateRangeTool(),
            'parse_date': ParseDateTool()
        }
        
        print("✅ Local LangChain-Style Agent initialized!")
        print(f"📦 Available tools: {list(self.tools.keys())}")
    
    def parse_reading(self, raw_input: str) -> Dict[str, Any]:
        """
        Parse water meter reading using local ReAct pattern with LangChain-style tools
        """
        print(f"\n🚀 LOCAL LANGCHAIN-STYLE AGENT STARTING PARSE: '{raw_input}'")
        print("=" * 70)
        
        # Initialize parsing state
        state = {
            'raw_input': raw_input,
            'cleaned_text': None,
            'meter_tag': None,
            'reading_value': None,
            'unit': None,
            'date': None,
            'warnings': [],
            'confidence': 0.0,
            'tool_calls': []
        }
        
        try:
            # Execute ReAct loop with local decision making
            self._execute_react_loop(state)
            
            # Generate final result
            result = self._generate_result(state)
            
            # Check for duplicates
            self._check_duplicates(result)
            
            # Display results
            self._display_results(result)
            
            return result
            
        except Exception as e:
            print(f"❌ Local agent execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'raw_input': raw_input,
                'processing_method': 'local_langchain_style'
            }
    
    def _execute_react_loop(self, state: Dict[str, Any]):
        """Execute the local ReAct loop"""
        max_steps = 8
        
        for step in range(1, max_steps + 1):
            print(f"\n🧠 STEP {step} - THINKING:")
            
            # Decide next action based on current state
            action = self._think(state, step)
            
            if action == 'COMPLETE':
                print("   🎯 All data collected, analysis complete!")
                break
            elif action == 'FAIL':
                print("   ❌ Cannot proceed - insufficient data")
                state['warnings'].append('Parsing failed - insufficient data')
                break
            
            # Execute the decided action
            print(f"\n🎬 STEP {step} - ACTING: {action}")
            self._act(state, action, step)
    
    def _think(self, state: Dict[str, Any], step: int) -> str:
        """Local reasoning: decide next action based on current state"""
        
        # Step 1: Always clean the input first
        if state['cleaned_text'] is None:
            print("   💭 Raw input needs cleaning to remove noise and normalize format")
            return "CLEAN_TEXT"

        # Step 2: Identify the meter after cleaning
        elif state['meter_tag'] is None:
            if not state['cleaned_text'].strip():
                print("   💭 Cleaned text is empty - cannot proceed")
                return "FAIL"
            else:
                print("   💭 Need to identify which meter this reading belongs to")
                return "IDENTIFY_METER"

        # Step 3: Extract reading value
        elif state['reading_value'] is None:
            print("   💭 Need to extract the numerical reading from the text")
            return "EXTRACT_READING"

        # Step 4: Determine unit
        elif state['unit'] is None:
            print("   💭 Need to identify and standardize the unit of measurement")
            return "IDENTIFY_UNIT"

        # Step 5: Parse date
        elif state['date'] is None:
            print("   💭 Need to extract or assign a date for this reading")
            return "PARSE_DATE"

        # Step 6: Validate the reading (only once)
        elif not any('validate_range' in call[0] for call in state['tool_calls']):
            print("   💭 Have all basic data - now validate the reading makes sense")
            return "VALIDATE"
        
        # All steps complete
        else:
            print("   💭 All parsing steps completed successfully!")
            return "COMPLETE"
    
    def _act(self, state: Dict[str, Any], action: str, step: int):
        """Execute the decided action using LangChain-style tools"""
        
        if action == "CLEAN_TEXT":
            result = self.tools['clean_text'].run(state['raw_input'])
            state['cleaned_text'] = result
            state['tool_calls'].append(('clean_text', state['raw_input'], result))

        elif action == "IDENTIFY_METER":
            result = self.tools['identify_meter'].run(state['cleaned_text'])
            state['meter_tag'] = result
            if result != 'UNKNOWN':
                state['confidence'] += 0.3
            else:
                state['warnings'].append('Could not identify meter tag')
            state['tool_calls'].append(('identify_meter', state['cleaned_text'], result))

        elif action == "EXTRACT_READING":
            result = self.tools['extract_numbers'].run(state['cleaned_text'])
            numbers = json.loads(result) if result else []
            
            if numbers:
                # Take the first/largest meaningful number
                reading = max(numbers) if len(numbers) > 1 else numbers[0]
                state['reading_value'] = reading
                state['confidence'] += 0.4
            else:
                state['reading_value'] = 0.0
                state['warnings'].append('No numeric reading detected')
            state['tool_calls'].append(('extract_numbers', state['cleaned_text'], result))

        elif action == "IDENTIFY_UNIT":
            result = self.tools['standardize_unit'].run(state['cleaned_text'])
            state['unit'] = result
            state['confidence'] += 0.2
            state['tool_calls'].append(('standardize_unit', state['cleaned_text'], result))

        elif action == "PARSE_DATE":
            result = self.tools['parse_date'].run(state['cleaned_text'])
            state['date'] = result
            state['confidence'] += 0.1
            state['tool_calls'].append(('parse_date', state['cleaned_text'], result))

        elif action == "VALIDATE":
            validation_input = f"{state['reading_value']},{state['unit']}"
            result = self.tools['validate_range'].run(validation_input)
            
            if result == "OUT_OF_RANGE":
                state['warnings'].append(f'Reading {state["reading_value"]} {state["unit"]} is outside expected range')
            elif result == "UNKNOWN_UNIT":
                state['warnings'].append(f'Unknown unit {state["unit"]} - cannot validate range')
            
            state['tool_calls'].append(('validate_range', validation_input, result))
    
    def _generate_result(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final structured result"""
        
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
            'raw_input': state['raw_input'],
            'processing_method': 'local_langchain_style',
            'tool_calls': len(state['tool_calls']),
            'execution_trace': state['tool_calls'],
            'available_tools': list(self.tools.keys())
        }
        
        return result
    
    def _check_duplicates(self, result: Dict[str, Any]):
        """Check for duplicate readings"""
        if result.get('success'):
            meter_tag = result['meter']['tag']
            reading_value = result['reading']['value']
            date = result['reading']['date']
            
            reading_signature = f"{meter_tag}_{reading_value}_{date}"
            if reading_signature in self.parsing_history:
                result.setdefault('warnings', []).append('Potential duplicate reading')
            else:
                self.parsing_history.append(reading_signature)
                # Keep history manageable
                if len(self.parsing_history) > 100:
                    self.parsing_history = self.parsing_history[-50:]
    
    def _display_results(self, result: Dict[str, Any]):
        """Display formatted results"""
        print(f"\n🎯 LOCAL LANGCHAIN-STYLE AGENT FINAL RESULT:")
        print("=" * 70)
        
        print(f"✅ Success: {result.get('success', False)}")
        print(f"📊 Confidence: {result.get('confidence', 0.0)}")
        print(f"🏷️  Meter: {result['meter']['tag']} ({result['meter']['description']})")
        print(f"📏 Reading: {result['reading']['value']} {result['reading']['unit']}")
        print(f"📅 Date: {result['reading']['date']}")
        print(f"🔧 Processing: {result.get('processing_method', 'unknown')}")
        print(f"🛠️  Tool Calls: {result.get('tool_calls', 0)}")
        print(f"📦 Available Tools: {len(result.get('available_tools', []))}")
        
        if result.get('warnings'):
            print(f"⚠️  Warnings: {len(result['warnings'])}")
            for warning in result['warnings']:
                print(f"   - {warning}")

def main():
    """
    Main execution function with both voice and text input support
    """
    print("🤖 Local LangChain-Style Water Meter Agent")
    print("(No APIs, No LLMs - Pure Local Processing with Tool Framework)")
    print("=" * 65)
    
    # Initialize local agent
    try:
        agent = LocalLangChainStyleAgent()
    except Exception as e:
        print(f"❌ Failed to initialize local agent: {e}")
        return
    
    # Get input method preference
    use_voice = input("Use voice input? (y/n): ").lower().startswith('y')
    
    if use_voice:
        reading_text = get_voice_input()
        if not reading_text:
            print("❌ No voice input received, falling back to text input.")
            reading_text = input("Enter water meter reading: ")
    else:
        reading_text = input("Enter water meter reading: ")
    
    if not reading_text.strip():
        print("❌ No input provided.")
        return
    
    # Process the reading
    result = agent.parse_reading(reading_text)
    
    # Output final JSON
    print("\n📋 JSON OUTPUT:")
    print("-" * 30)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
