"""
Voice Input Demo for Water Meter Agent
"""

import json
from voice_input import VoiceInputHandler
from local_langchain_style_agent import LocalLangChainStyleAgent
from water_meter_agent import WaterMeterAgent

def test_voice_input_basic():
    """Test basic voice input functionality"""
    print(" BASIC VOICE INPUT TEST")
    print("=" * 40)
    
    handler = VoiceInputHandler()
    
    # Test microphone setup
    test_result = handler.test_microphone()
    print(f"Microphone Status:")
    print(f"   Available: {test_result.get('available', False)}")
    print(f"   Working: {test_result.get('microphone_working', False)}")
    print(f"   Recognition: {test_result.get('recognition_working', False)}")
    
    if test_result.get('error'):
        print(f"   Error: {test_result['error']}")
        return False
    
    return True

def demo_voice_with_agents():
    """Demonstrate voice input with both agent implementations"""
    print("\n VOICE INPUT WITH AGENTS DEMO")
    print("=" * 50)
    
    # Initialize agents
    try:
        original_agent = WaterMeterAgent()
        local_agent = LocalLangChainStyleAgent()
        print(" Agents initialized successfully")
    except Exception as e:
        print(f"Failed to initialize agents: {e}")
        return
    
    # Get voice input
    handler = VoiceInputHandler()
    print("\n Please provide a water meter reading via voice:")
    
    voice_text = handler.get_voice_input_interactive()
    
    if not voice_text:
        print(" No voice input received")
        return
    
    print(f"\n Processing: '{voice_text}'")
    print("=" * 60)
    
    # Test with original agent
    print("\n ORIGINAL AGENT PROCESSING:")
    print("-" * 40)
    original_result = original_agent.parse_reading(voice_text)
    
    # Test with local LangChain-style agent
    print("\n LOCAL LANGCHAIN-STYLE AGENT PROCESSING:")
    print("-" * 40)
    local_result = local_agent.parse_reading(voice_text)
    
    # Compare results
    print(f"\n RESULTS COMPARISON:")
    print("=" * 30)
    print(f"Original Success: {original_result.get('success')}")
    print(f"Local LC Success: {local_result.get('success')}")
    print(f"Original Meter: {original_result.get('meter', {}).get('tag')}")
    print(f"Local LC Meter: {local_result.get('meter', {}).get('tag')}")
    print(f"Original Reading: {original_result.get('reading', {}).get('value')}")
    print(f"Local LC Reading: {local_result.get('reading', {}).get('value')}")

def demo_voice_commands():
    """Demonstrate voice commands and speech processing"""
    print("\n  VOICE COMMANDS DEMO")
    print("=" * 40)
    
    handler = VoiceInputHandler()
    
    test_phrases = [
        "Try saying: 'Kitchen meter reading 125.5 cubic meters'",
        "Try saying: 'WM002 shows 89 gallons today'", 
        "Try saying: 'Garden water meter forty five point seven liters'",
        "Try saying: 'Main supply reading two hundred thirty four point eight cubic meters'"
    ]
    
    print(" Suggested test phrases:")
    for phrase in test_phrases:
        print(f"   • {phrase}")
    
    print(f"\n Voice Input Session:")
    print("   Say 'quit' or 'exit' to stop")
    
    session_count = 0
    while session_count < 5:  # Limit to 5 attempts
        session_count += 1
        print(f"\n--- Voice Input {session_count} ---")
        
        voice_text = handler.get_voice_input(timeout=15, retries=2)
        
        if not voice_text:
            continue
            
        # Check for exit commands
        if any(word in voice_text.lower() for word in ['quit', 'exit', 'stop', 'done']):
            print(" Voice session ended by user")
            break
        
        # Process with local agent for quick demonstration
        print(f" Quick processing...")
        agent = LocalLangChainStyleAgent()
        result = agent.parse_reading(voice_text)
        
        print(f" Quick Result:")
        print(f"   Input: '{voice_text}'")
        print(f"   Success: {result.get('success')}")
        print(f"   Meter: {result.get('meter', {}).get('tag')} ({result.get('meter', {}).get('description')})")
        print(f"   Reading: {result.get('reading', {}).get('value')} {result.get('reading', {}).get('unit')}")
        
        continue_session = input("\nContinue voice session? (y/n): ").lower().startswith('y')
        if not continue_session:
            break

def demo_speech_processing():
    """Demonstrate speech text processing and corrections"""
    print("\n SPEECH PROCESSING DEMO")
    print("=" * 40)
    
    handler = VoiceInputHandler()
    
    # Test speech processing with common misheard phrases
    test_inputs = [
        "kitchen water thing shows one hundred fifty point five gallons",
        "double you m zero zero two reading eighty nine point three",
        "garden meter forty five dot seven liters yesterday",
        "main supply two thirty four point eight cubic meters today"
    ]
    
    print(" Testing speech processing corrections:")
    for test_input in test_inputs:
        processed = handler._post_process_speech(test_input)
        print(f"Original:  '{test_input}'")
        print(f"Processed: '{processed}'")
        print()

def main():
    """Main demo function"""
    print(" ENHANCED VOICE INPUT DEMO")
    print("=" * 50)
    print("This demo showcases the enhanced voice input capabilities")
    print("for the Water Meter Agent project.")
    print()
    
    # Test basic functionality
    if not test_voice_input_basic():
        print(" Basic voice input test failed. Check microphone setup.")
        return
    
    print("\n Choose demo mode:")
    print("1. Voice input with agent processing")
    print("2. Interactive voice commands session") 
    print("3. Speech processing demonstration")
    print("4. All demos")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    try:
        if choice == '1':
            demo_voice_with_agents()
        elif choice == '2':
            demo_voice_commands()
        elif choice == '3':
            demo_speech_processing()
        elif choice == '4':
            demo_voice_with_agents()
            demo_voice_commands() 
            demo_speech_processing()
        else:
            print("Invalid choice. Running speech processing demo...")
            demo_speech_processing()
    except KeyboardInterrupt:
        print("\n Demo interrupted by user")
    except Exception as e:
        print(f" Demo error: {e}")
    
    print("\n Voice input demo completed!")

if __name__ == "__main__":
    main()
