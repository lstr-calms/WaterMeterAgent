"""
Enhanced Voice Input Module for Water Meter Agent
Provides robust voice recognition with multiple fallback options and error handling.
"""

import time
import re
from typing import Optional, Dict, Any

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    sr = None

class VoiceInputHandler:
    """
    Enhanced voice input handler with multiple recognition engines and robust error handling
    """
    
    def __init__(self):
        self.recognizer = None
        self.microphone = None
        self.available_engines = []
        
        if SPEECH_RECOGNITION_AVAILABLE:
            self.recognizer = sr.Recognizer()
            try:
                self.microphone = sr.Microphone()
                self._initialize_engines()
                self._calibrate_microphone()
            except Exception as e:
                print(f"⚠️  Microphone initialization failed: {e}")
        else:
            print("⚠️  SpeechRecognition library not available. Please install: pip install SpeechRecognition pyaudio")
    
    def _initialize_engines(self):
        """Check which recognition engines are available"""
        test_engines = [
            ('google', 'Google Speech Recognition'),
            ('sphinx', 'CMU Sphinx (offline)'),
            ('wit', 'Wit.ai'),
            ('azure', 'Microsoft Azure Speech'),
            ('ibm', 'IBM Watson Speech')
        ]
        
        for engine, description in test_engines:
            if self._test_engine(engine):
                self.available_engines.append((engine, description))
        
        if self.available_engines:
            print(f"✅ Available speech engines: {len(self.available_engines)}")
            for engine, desc in self.available_engines:
                print(f"   - {desc}")
        else:
            print("⚠️  No speech recognition engines available")
    
    def _test_engine(self, engine: str) -> bool:
        """Test if a speech recognition engine is available"""
        try:
            if engine == 'google':
                return True  # Google is usually available
            elif engine == 'sphinx':
                # Test if pocketsphinx is installed
                try:
                    import pocketsphinx
                    return True
                except ImportError:
                    return False
            # Add tests for other engines as needed
            return False
        except:
            return False
    
    def _calibrate_microphone(self):
        """Calibrate microphone for ambient noise"""
        if not self.microphone:
            return
        
        try:
            print("🎤 Calibrating microphone for ambient noise...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ Microphone calibrated")
        except Exception as e:
            print(f"⚠️  Microphone calibration failed: {e}")
    
    def get_voice_input(self, 
                       timeout: int = 10, 
                       phrase_timeout: int = 5,
                       retries: int = 3,
                       engine: str = 'google') -> Optional[str]:
        """
        Capture voice input with enhanced error handling and multiple attempts
        
        Args:
            timeout: Maximum time to wait for speech to start
            phrase_timeout: Maximum time to wait for speech to complete
            retries: Number of retry attempts
            engine: Speech recognition engine to use
            
        Returns:
            Recognized text or None if failed
        """
        if not SPEECH_RECOGNITION_AVAILABLE:
            print("❌ Speech recognition not available")
            return None
        
        if not self.microphone:
            print("❌ Microphone not available")
            return None
        
        for attempt in range(retries):
            try:
                print(f"\n🎤 Voice Input Attempt {attempt + 1}/{retries}")
                print("🗣️  Please speak your water meter reading clearly...")
                print("   (Speak now - listening...)")
                
                with self.microphone as source:
                    # Listen for audio with timeout
                    audio = self.recognizer.listen(
                        source, 
                        timeout=timeout, 
                        phrase_time_limit=phrase_timeout
                    )
                
                print("🔄 Processing speech...")
                
                # Try recognition with specified engine
                text = self._recognize_with_engine(audio, engine)
                
                if text:
                    print(f"✅ Recognized: '{text}'")
                    
                    # Post-process the text for better water meter reading format
                    processed_text = self._post_process_speech(text)
                    if processed_text != text:
                        print(f"📝 Processed: '{processed_text}'")
                        return processed_text
                    
                    return text
                else:
                    print(f"❌ Recognition failed (attempt {attempt + 1})")
                    
            except sr.WaitTimeoutError:
                print(f"⏰ No speech detected within {timeout} seconds (attempt {attempt + 1})")
            except sr.UnknownValueError:
                print(f"❓ Could not understand audio (attempt {attempt + 1})")
            except sr.RequestError as e:
                print(f"🌐 Recognition service error: {e} (attempt {attempt + 1})")
            except Exception as e:
                print(f"❌ Unexpected error: {e} (attempt {attempt + 1})")
            
            if attempt < retries - 1:
                print("🔄 Trying again in 2 seconds...")
                time.sleep(2)
        
        print(f"❌ Voice input failed after {retries} attempts")
        return None
    
    def _recognize_with_engine(self, audio, engine: str) -> Optional[str]:
        """Recognize speech using the specified engine"""
        try:
            if engine == 'google':
                return self.recognizer.recognize_google(audio)
            elif engine == 'sphinx':
                return self.recognizer.recognize_sphinx(audio)
            elif engine == 'wit':
                # Requires Wit.ai API key
                return self.recognizer.recognize_wit(audio, key="YOUR_WIT_AI_KEY")
            # Add other engines as needed
            else:
                return self.recognizer.recognize_google(audio)  # Fallback to Google
        except Exception as e:
            print(f"Recognition engine error ({engine}): {e}")
            return None
    
    def _post_process_speech(self, text: str) -> str:
        """
        Post-process speech recognition text to improve water meter reading format
        """
        if not text:
            return text
        
        # Convert to uppercase for consistent processing
        processed = text.upper()
        
        # Common speech-to-text corrections for water meter readings
        corrections = {
            # Number corrections
            'ZERO': '0',
            'ONE': '1',
            'TWO': '2',
            'THREE': '3',
            'FOUR': '4',
            'FIVE': '5',
            'SIX': '6',
            'SEVEN': '7',
            'EIGHT': '8',
            'NINE': '9',
            'TEN': '10',
            
            # Unit corrections
            'METERS': 'CUBIC METERS',
            'METER': 'CUBIC METERS',
            'GALLON': 'GALLONS',
            'LITER': 'LITERS',
            'LITRE': 'LITERS',
            'LITRES': 'LITERS',
            
            # Common misheard phrases
            'WATER THING': 'WATER METER',
            'READER': 'METER',
            'READING': 'METER READING',
            
            # Meter tag corrections
            'DOUBLE YOU M': 'WM',
            'W M': 'WM',
            'DUBYA M': 'WM',
            
            # Location corrections
            'KITCHEN': 'KITCHEN METER',
            'BATHROOM': 'BATHROOM METER',
            'GARDEN': 'GARDEN METER',
            'MAIN': 'MAIN METER',
        }
        
        # Apply corrections
        for wrong, correct in corrections.items():
            processed = processed.replace(wrong, correct)
        
        # Fix common decimal point issues
        processed = re.sub(r'(\d+)\s+POINT\s+(\d+)', r'\1.\2', processed)
        processed = re.sub(r'(\d+)\s+DOT\s+(\d+)', r'\1.\2', processed)
        
        # Fix spacing around numbers
        processed = re.sub(r'(\d+)\s+(\d+)', r'\1\2', processed)
        
        return processed.strip()
    
    def test_microphone(self) -> Dict[str, Any]:
        """
        Test microphone functionality and return diagnostic information
        """
        if not SPEECH_RECOGNITION_AVAILABLE:
            return {'available': False, 'error': 'SpeechRecognition not installed'}
        
        try:
            # Test microphone access
            with sr.Microphone() as source:
                print("🎤 Testing microphone... (say something)")
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=3)
                
            # Test recognition
            text = self.recognizer.recognize_google(audio)
            
            return {
                'available': True,
                'microphone_working': True,
                'recognition_working': True,
                'test_result': text,
                'available_engines': self.available_engines
            }
            
        except sr.WaitTimeoutError:
            return {
                'available': True,
                'microphone_working': True,
                'recognition_working': False,
                'error': 'No speech detected during test',
                'available_engines': self.available_engines
            }
        except Exception as e:
            return {
                'available': True,
                'microphone_working': False,
                'recognition_working': False,
                'error': str(e),
                'available_engines': self.available_engines
            }
    
    def get_voice_input_interactive(self) -> Optional[str]:
        """
        Interactive voice input with user guidance and options
        """
        if not SPEECH_RECOGNITION_AVAILABLE:
            print("❌ Voice input not available. Please install required packages:")
            print("   pip install SpeechRecognition pyaudio")
            return None
        
        print("\n🎤 VOICE INPUT MODE")
        print("=" * 40)
        print("📋 Tips for better recognition:")
        print("   • Speak clearly and at moderate pace")
        print("   • Include meter ID (WM001, Kitchen, etc.)")
        print("   • State the number and unit (150.5 cubic meters)")
        print("   • Mention date if specific (yesterday, today)")
        print("   • Example: 'Kitchen meter reading 150.5 cubic meters'")
        print()
        
        # Ask user for preferences
        use_advanced = input("Use advanced settings? (y/n): ").lower().startswith('y')
        
        timeout = 10
        retries = 3
        engine = 'google'
        
        if use_advanced:
            try:
                timeout = int(input("Listening timeout in seconds (10): ") or "10")
                retries = int(input("Number of retry attempts (3): ") or "3")
                
                if len(self.available_engines) > 1:
                    print("Available engines:")
                    for i, (eng, desc) in enumerate(self.available_engines):
                        print(f"  {i + 1}. {desc}")
                    choice = input(f"Choose engine (1-{len(self.available_engines)}, default=1): ")
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(self.available_engines):
                            engine = self.available_engines[idx][0]
                    except:
                        pass
            except:
                print("Using default settings...")
        
        # Get voice input
        result = self.get_voice_input(timeout=timeout, retries=retries, engine=engine)
        
        if result:
            # Confirm with user
            print(f"\n✅ Voice input captured: '{result}'")
            confirm = input("Use this input? (y/n): ").lower().startswith('y')
            if confirm:
                return result
            else:
                print("Voice input cancelled by user")
                return None
        else:
            print("\n❌ Voice input failed")
            fallback = input("Enter text manually instead? (y/n): ").lower().startswith('y')
            if fallback:
                return input("Enter water meter reading: ")
            return None

# Convenience function for backward compatibility
def get_voice_input() -> str:
    """Simple voice input function for backward compatibility"""
    handler = VoiceInputHandler()
    result = handler.get_voice_input()
    return result or ""

# Main test function
def main():
    """Test the voice input functionality"""
    print("🎤 Voice Input Test")
    print("=" * 30)
    
    handler = VoiceInputHandler()
    
    # Test microphone
    test_result = handler.test_microphone()
    print(f"📊 Microphone test: {test_result}")
    
    if test_result.get('available'):
        # Interactive voice input
        result = handler.get_voice_input_interactive()
        print(f"\n📋 Final result: '{result}'")
    else:
        print("❌ Voice input not available")

if __name__ == "__main__":
    main()
