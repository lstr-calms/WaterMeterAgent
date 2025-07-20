"""
Comparison script to demonstrate all three implementations:
1. Original ReAct implementation (rule-based)
2. Local LangChain-style implementation (uses tool framework but local reasoning)
3. LangChain-powered version (requires OpenAI API) - optional

Enhanced with voice input capabilities across all implementations.
"""

import json
import os
from water_meter_agent import WaterMeterAgent
from local_langchain_style_agent import LocalLangChainStyleAgent
from voice_input import VoiceInputHandler

# Try to import LangChain agent if available
try:
    from langchain_water_meter_agent import LangChainWaterMeterAgent
    LANGCHAIN_AVAILABLE = True
    print("✅ LangChain with OpenAI available")
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    print(f"⚠️  LangChain with OpenAI not available: {e}")
except Exception as e:
    LANGCHAIN_AVAILABLE = False
    print(f"⚠️  LangChain with OpenAI initialization failed: {e}")

def test_all_agents():
    """Test all three implementations with sample inputs"""
    
    # Test cases
    test_cases = [
        "Kitchen meter reading is 150.5 cubic meters",
        "WM002 shows 89.3 gallons today",
        "Garden water meter: 45.7 liters on 2025-01-15",
        "Main supply reading 234.8 m3",
        "Hot water heater meter WM005 reads 67.2 cubic meters"
    ]
    
    print("🔬 COMPARING ALL THREE IMPLEMENTATIONS")
    print("=" * 70)
    
    # Initialize agents
    original_agent = WaterMeterAgent()
    local_langchain_agent = LocalLangChainStyleAgent()
    
    # Check if OpenAI API key is available for LangChain agent
    langchain_available = False
    if LANGCHAIN_AVAILABLE and os.getenv("OPENAI_API_KEY"):
        try:
            langchain_agent = LangChainWaterMeterAgent()
            langchain_available = True
        except Exception as e:
            print(f"⚠️  LangChain API agent initialization failed: {e}")
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n🧪 TEST CASE {i}: '{test_input}'")
        print("-" * 70)
        
        # Test original implementation
        print("\n📊 ORIGINAL REACT IMPLEMENTATION:")
        print("=" * 40)
        original_result = original_agent.parse_reading(test_input)
        
        # Test local LangChain implementation
        print("\n🔧 LOCAL LANGCHAIN-STYLE IMPLEMENTATION:")
        print("=" * 40)
        local_result = local_langchain_agent.parse_reading(test_input)
        
        # Test API LangChain implementation if available
        if langchain_available:
            print("\n🤖 API LANGCHAIN REACT IMPLEMENTATION:")
            print("=" * 40)
            api_result = langchain_agent.parse_reading(test_input)
        
        # Compare results
        print(f"\n🔍 COMPARISON:")
        print("-" * 20)
        print(f"Original Success: {original_result.get('success')}")
        print(f"Local LC Success: {local_result.get('success')}")
        if langchain_available:
            print(f"API LC Success: {api_result.get('success')}")
        
        print(f"Original Confidence: {original_result.get('confidence', 0)}")
        print(f"Local LC Confidence: {local_result.get('confidence', 0)}")
        if langchain_available:
            print(f"API LC Confidence: {api_result.get('confidence', 0)}")
        
        # Check if all got same meter tag
        orig_tag = original_result.get('meter', {}).get('tag')
        local_tag = local_result.get('meter', {}).get('tag')
        print(f"Meter Tags (Orig vs Local): {orig_tag == local_tag} ({orig_tag} vs {local_tag})")
        
        if langchain_available:
            api_tag = api_result.get('meter', {}).get('tag')
            print(f"All Meter Tags Match: {orig_tag == local_tag == api_tag}")
        
        print("\n" + "=" * 70)

def demonstrate_local_langchain_features():
    """Demonstrate Local LangChain-style specific features"""
    
    print("\n🌟 LOCAL LANGCHAIN-STYLE FEATURES DEMO")
    print("=" * 50)
    
    try:
        agent = LocalLangChainStyleAgent()
        
        print("\n✨ Enhanced Tool Framework with Local Reasoning:")
        print("Testing with complex input...")
        
        complex_input = "I think the water thing in my kitchen showed something like 150 or maybe 155 gallons yesterday"
        result = agent.parse_reading(complex_input)
        
        print(f"\n📋 Local LangChain-style handled complex input:")
        print(f"Input: {complex_input}")
        print(f"Result Summary:")
        print(f"  - Success: {result.get('success')}")
        print(f"  - Meter: {result.get('meter', {}).get('tag')} ({result.get('meter', {}).get('description')})")
        print(f"  - Reading: {result.get('reading', {}).get('value')} {result.get('reading', {}).get('unit')}")
        print(f"  - Tool Calls: {result.get('tool_calls')}")
        print(f"  - Processing Method: {result.get('processing_method')}")
        
        print(f"\n🔧 Execution Trace:")
        for i, (tool, input_val, output) in enumerate(result.get('execution_trace', []), 1):
            print(f"  {i}. {tool}: {input_val[:50]}... → {str(output)[:50]}...")
        
    except Exception as e:
        print(f"❌ Local LangChain-style demo failed: {e}")

if __name__ == "__main__":
    # Run comparison
    test_all_agents()
    
    # Demonstrate Local LangChain features
    demonstrate_local_langchain_features()
    
    print("\n🎯 SUMMARY:")
    print("=" * 30)
    print("✅ Original Implementation:")
    print("  - Deterministic ReAct pattern")
    print("  - No external dependencies")
    print("  - Fast and predictable")
    print("  - Rule-based parsing")
    
    print("\n✅ Local LangChain-Style Implementation:")
    print("  - LangChain-inspired tool framework")
    print("  - Local reasoning (no APIs)")
    print("  - Structured tool execution")
    print("  - Enhanced traceability")
    print("  - Modular and extensible")
    print("  - No external dependencies")
    
    if LANGCHAIN_AVAILABLE:
        print("\n✅ API LangChain Implementation:")
        print("  - AI-powered reasoning")
        print("  - Better handling of ambiguous input")
        print("  - Extensible tool framework")
        print("  - Natural language understanding")
        print("  - Requires OpenAI API key")
