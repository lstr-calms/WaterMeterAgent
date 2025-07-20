import re
import json
import os
from typing import Dict, List, Any, Optional, Tuple, Type
from datetime import datetime
from difflib import SequenceMatcher

# LangChain imports
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import BaseTool
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.schema import AgentAction, AgentFinish
from langchain.callbacks.manager import CallbackManagerForToolRun
from pydantic import BaseModel, Field

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# LangChain Tool Definitions
class CleanTextTool(BaseTool):
    name = "clean_text"
    description = "Remove noise and normalize text format for water meter reading parsing"
    
    def _run(self, raw_text: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Remove extra whitespace and normalize text"""
        cleaned = re.sub(r'\s+', ' ', raw_text.strip())
        cleaned = re.sub(r'[^\w\s\.\-:/]', ' ', cleaned)
        return cleaned.upper()

class ExtractNumbersTool(BaseTool):
    name = "extract_numbers"
    description = "Extract all numeric values from text, useful for finding water meter readings"
    
    def _run(self, text: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> List[float]:
        """Extract numeric values from text"""
        pattern = r'\d+\.?\d*'
        matches = re.findall(pattern, text)
        return [float(match) for match in matches]

class FuzzyMatchTool(BaseTool):
    name = "fuzzy_match"
    description = "Find best fuzzy match from a dictionary of known values (meter tags or names)"
    
    def __init__(self, dictionary: Dict[str, str], threshold: float = 0.6):
        super().__init__()
        self.dictionary = dictionary
        self.threshold = threshold
    
    def _run(self, text: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> Optional[str]:
        """Find best fuzzy match in dictionary"""
        best_match = None
        best_score = 0.0

        for key in self.dictionary.keys():
            if key in text:  # Exact match
                return key

            # Fuzzy matching
            score = SequenceMatcher(None, key, text).ratio()
            if score > best_score and score >= self.threshold:
                best_score = score
                best_match = key

        return best_match

class StandardizeUnitTool(BaseTool):
    name = "standardize_unit"
    description = "Convert unit variations to standard form (cubic_meters, gallons, liters)"
    
    def _run(self, text: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Convert unit variations to standard form"""
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

class ValidateRangeTool(BaseTool):
    name = "validate_range"
    description = "Check if a water meter reading is within reasonable range for the given unit"
    
    def _run(self, value_unit: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Check if reading is within reasonable range"""
        try:
            parts = value_unit.split(',')
            value = float(parts[0])
            unit = parts[1].strip()
        except:
            return "Error: Expected format 'value,unit'"
        
        ranges = {
            'cubic_meters': (0, 1000, "Typical home usage: 0-1000 cubic meters"),
            'gallons': (0, 264000, "Typical home usage: 0-264,000 gallons"),
            'liters': (0, 1000000, "Typical home usage: 0-1,000,000 liters")
        }

        if unit not in ranges:
            return f"Unknown unit '{unit}' - cannot validate range"

        min_val, max_val, description = ranges[unit]
        is_valid = min_val <= value <= max_val

        if is_valid:
            return f"VALID: Value {value} {unit} is within expected range"
        else:
            return f"WARNING: Value {value} {unit} is outside expected range ({description})"

class ParseDateTool(BaseTool):
    name = "parse_date"
    description = "Extract date from text or return current date in YYYY-MM-DD format"
    
    def _run(self, text: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Extract date or return current date"""
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

# Voice input support - Enhanced version
from voice_input import VoiceInputHandler

def get_voice_input() -> str:
    """Capture voice input from microphone and return as text."""
    handler = VoiceInputHandler()
    result = handler.get_voice_input_interactive()
    return result or ""

class LangChainWaterMeterAgent:
    """
    Water Meter Agent powered by LangChain's ReAct framework
    """
    
    def __init__(self, api_key: Optional[str] = None):
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
        
        # Initialize LangChain components
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            openai_api_key=api_key or os.getenv("OPENAI_API_KEY")
        )
        
        # Create tools
        self.tools = [
            CleanTextTool(),
            ExtractNumbersTool(),
            FuzzyMatchTool(self.meter_tags, threshold=0.6),
            FuzzyMatchTool(self.name_to_tag, threshold=0.6),
            StandardizeUnitTool(),
            ValidateRangeTool(),
            ParseDateTool()
        ]
        
        # Create the ReAct prompt
        self.prompt = PromptTemplate.from_template("""
You are a water meter reading agent that processes text input to extract structured water meter data.

Your goal is to extract:
1. Meter tag (WM001-WM005 or map from common names like KITCHEN->WM001)
2. Reading value (numeric)
3. Unit (standardized to cubic_meters, gallons, or liters)
4. Date (YYYY-MM-DD format)

Available tools: {tool_names}
Tool descriptions: {tools}

ALWAYS follow this sequence:
1. First use clean_text to normalize the input
2. Use fuzzy_match to identify the meter (try meter tags first, then common names)
3. Use extract_numbers to get the reading value
4. Use standardize_unit to identify and standardize the unit
5. Use parse_date to extract or assign a date
6. Use validate_range to check if the reading is reasonable

Input: {input}

{agent_scratchpad}

Remember: 
- Known meter tags: WM001 (Kitchen), WM002 (Bathroom), WM003 (Garden), WM004 (Main), WM005 (Hot Water)
- Common names: KITCHEN, BATH, GARDEN, MAIN, SUPPLY, HEATER map to respective tags
- Always provide a final answer in JSON format with all extracted information
""")
        
        # Create the agent
        self.agent = create_react_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent, 
            tools=self.tools, 
            verbose=True,
            max_iterations=10,
            return_intermediate_steps=True
        )
    
    def parse_reading(self, raw_input: str) -> Dict[str, Any]:
        """
        Parse water meter reading using LangChain ReAct agent
        """
        print(f"🚀 LANGCHAIN AGENT STARTING PARSE: '{raw_input}'")
        print("=" * 60)
        
        try:
            # Run the agent
            result = self.agent_executor.invoke({"input": raw_input})
            
            # Extract the final answer
            final_answer = result.get("output", "")
            
            # Try to parse JSON from the final answer
            try:
                if "{" in final_answer and "}" in final_answer:
                    json_start = final_answer.find("{")
                    json_end = final_answer.rfind("}") + 1
                    json_str = final_answer[json_start:json_end]
                    parsed_result = json.loads(json_str)
                else:
                    # Fallback: create structured result from intermediate steps
                    parsed_result = self._create_fallback_result(raw_input, result)
            except json.JSONDecodeError:
                parsed_result = self._create_fallback_result(raw_input, result)
            
            # Add metadata
            parsed_result.update({
                'raw_input': raw_input,
                'agent_steps': len(result.get('intermediate_steps', [])),
                'processing_method': 'langchain_react'
            })
            
            # Check for duplicates
            self._check_duplicates(parsed_result)
            
            # Display results
            self._display_results(parsed_result)
            
            return parsed_result
            
        except Exception as e:
            print(f"❌ Agent execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'raw_input': raw_input,
                'processing_method': 'langchain_react'
            }
    
    def _create_fallback_result(self, raw_input: str, agent_result: Dict) -> Dict[str, Any]:
        """Create a structured result when agent doesn't return proper JSON"""
        
        # Extract information from intermediate steps
        intermediate_steps = agent_result.get('intermediate_steps', [])
        
        # Initialize default values
        result = {
            'success': False,
            'confidence': 0.5,
            'meter': {'tag': 'UNKNOWN', 'description': 'Unknown Meter'},
            'reading': {'value': 0.0, 'unit': 'cubic_meters', 'date': datetime.now().strftime('%Y-%m-%d')},
            'warnings': ['Fallback parsing used - agent did not return structured JSON'],
            'raw_input': raw_input
        }
        
        # Try to extract information from tool outputs
        for step in intermediate_steps:
            if isinstance(step, tuple) and len(step) == 2:
                action, observation = step
                tool_name = getattr(action, 'tool', '')
                tool_output = str(observation)
                
                if tool_name == 'extract_numbers' and tool_output:
                    try:
                        numbers = eval(tool_output)  # Be careful with eval in production
                        if numbers and isinstance(numbers, list):
                            result['reading']['value'] = max(numbers)
                            result['confidence'] += 0.2
                    except:
                        pass
                
                elif tool_name == 'fuzzy_match' and tool_output and tool_output != 'None':
                    if tool_output in self.meter_tags:
                        result['meter']['tag'] = tool_output
                        result['meter']['description'] = self.meter_tags[tool_output]
                        result['confidence'] += 0.3
                    elif tool_output in self.name_to_tag:
                        tag = self.name_to_tag[tool_output]
                        result['meter']['tag'] = tag
                        result['meter']['description'] = self.meter_tags.get(tag, 'Unknown')
                        result['confidence'] += 0.3
                
                elif tool_name == 'standardize_unit' and tool_output:
                    result['reading']['unit'] = tool_output
                    result['confidence'] += 0.1
                
                elif tool_name == 'parse_date' and tool_output:
                    result['reading']['date'] = tool_output
                    result['confidence'] += 0.1
        
        # Determine success
        result['success'] = (
            result['meter']['tag'] != 'UNKNOWN' and 
            result['reading']['value'] > 0
        )
        
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
        print(f"\n🎯 LANGCHAIN AGENT FINAL RESULT:")
        print("=" * 60)
        
        print(f"✅ Success: {result.get('success', False)}")
        print(f"📊 Confidence: {result.get('confidence', 0.0)}")
        print(f"🏷️  Meter: {result['meter']['tag']} ({result['meter']['description']})")
        print(f"📏 Reading: {result['reading']['value']} {result['reading']['unit']}")
        print(f"📅 Date: {result['reading']['date']}")
        print(f"🔧 Processing: {result.get('processing_method', 'unknown')}")
        print(f"🔄 Agent Steps: {result.get('agent_steps', 0)}")
        
        if result.get('warnings'):
            print(f"⚠️  Warnings: {len(result['warnings'])}")
            for warning in result['warnings']:
                print(f"   - {warning}")


def main():
    """
    Main execution function with both voice and text input support
    """
    print("🤖 LangChain Water Meter Agent")
    print("=" * 40)
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not found in environment variables.")
        print("Please set your OpenAI API key in a .env file or environment variable.")
        api_key = input("Enter your OpenAI API key (or press Enter to skip): ").strip()
        if not api_key:
            print("❌ Cannot proceed without API key.")
            return
    else:
        api_key = None
    
    # Initialize agent
    try:
        agent = LangChainWaterMeterAgent(api_key=api_key)
        print("✅ LangChain agent initialized successfully!")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
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
