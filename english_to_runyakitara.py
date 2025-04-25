import os
import google.generativeai as genai
from pydub import AudioSegment
import speech_recognition as sr
import sounddevice as sd
import wave

# Configuration
GEMINI_API_KEY = "AIzaSyBU0nYJ79vuTX5CbJReS43Ygz96l_zrpgs"  # Replace with your actual key
AUDIO_FILENAME = "recorded_audio.wav"

def initialize_gemini():
    """Initialize Gemini with the current model"""
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Try to use a specific current model
    try:
        # Use the recommended model (gemini-1.5-flash) or another current model
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        print(f"Error initializing recommended model: {e}")
        
        # Fallback to finding any available model
        try:
            for model in genai.list_models():
                if 'generateContent' in model.supported_generation_methods:
                    print(f"Using available model: {model.name}")
                    return genai.GenerativeModel(model.name)
        except Exception as e:
            print(f"Error listing models: {e}")
            raise Exception("Failed to initialize any Gemini model. Check your API key and network connection.")

def record_audio(duration=5, sample_rate=44100):
    """Record audio from microphone"""
    print(f"Recording for {duration} seconds... Speak now!")
    audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
    sd.wait()
    print("Recording complete")
    
    with wave.open(AUDIO_FILENAME, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())
    return AUDIO_FILENAME

def transcribe_audio(audio_file_path):
    """Transcribe audio to text"""
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file_path) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
            print(f"Transcribed English text: {text}")
            return text
        except Exception as e:
            print(f"Transcription error: {e}")
            return None

def translate_to_runyankole(english_text):
    """Translate using Gemini"""
    try:
        prompt = """You are a professional translator. Translate this English to Runyankole (a Bantu language spoken in southwestern Uganda):
        English: {text}
        Runyankole:""".format(text=english_text)
        
        response = model.generate_content(prompt)
        return response.text if response.text else "No translation returned"
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return None

def main():
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        print("Error: Set your GEMINI_API_KEY first")
        return
    
    try:
        # Initialize model
        global model
        model = initialize_gemini()
        
        audio_file = record_audio(duration=10)
        english_text = transcribe_audio(audio_file)
        
        if not english_text:
            print("Transcription failed")
            return
            
        translation = translate_to_runyankole(english_text)
        if translation:
            print("\nRUNYANKOLE TRANSLATION:")
            print(translation)
            with open("translation.txt", "w") as f:
                f.write(translation)
            print("Translation saved to translation.txt")
        else:
            print("Translation failed")
            
    finally:
        if os.path.exists(AUDIO_FILENAME):
            os.remove(AUDIO_FILENAME)

if __name__ == "__main__":
    main()