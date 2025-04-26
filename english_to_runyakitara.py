import os
import google.generativeai as genai
import speech_recognition as sr
import sounddevice as sd
import wave
from pydub import AudioSegment
from tkinter import *
from tkinter import ttk, messagebox, filedialog
from threading import Thread

class TranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("English to Runyakitara Translator")
        self.root.geometry("650x500")
        
        # Configuration (API key hardcoded)
        self.GEMINI_API_KEY = "AIzaSyBU0nYJ79vuTX5CbJReS43Ygz96l_zrpgs"
        self.AUDIO_FILENAME = "recorded_audio.wav"
        self.model = None
        
        self.setup_ui()
        self.initialize_gemini()
        
    def initialize_gemini(self):
        """Initialize Gemini API with the hardcoded key"""
        try:
            genai.configure(api_key=self.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.update_status("API initialized successfully")
        except Exception as e:
            messagebox.showerror("API Error", f"Failed to initialize Gemini API: {str(e)}")
            self.root.destroy()

    def setup_ui(self):
        # Main container
        main_frame = Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=BOTH, expand=True)
        
        # Input Section
        input_frame = LabelFrame(main_frame, text="Input", padx=10, pady=10)
        input_frame.pack(fill=X, pady=5)
        
        # Recording buttons
        btn_frame = Frame(input_frame)
        btn_frame.pack(fill=X, pady=5)
        
        self.record_btn = Button(btn_frame, text="🎤 Record Audio (20s)", 
                               command=self.record_audio_thread,
                               font=('Arial', 10, 'bold'))
        self.record_btn.pack(side=LEFT, padx=5)
        
        self.upload_btn = Button(btn_frame, text="📁 Upload Audio File", 
                               command=self.upload_audio,
                               font=('Arial', 10))
        self.upload_btn.pack(side=LEFT, padx=5)
        
        # Text input
        self.text_input = Text(input_frame, height=6, width=70, wrap=WORD,
                             font=('Arial', 10), padx=5, pady=5)
        self.text_input.pack(fill=BOTH, expand=True)
        
        # Translation Section
        trans_frame = LabelFrame(main_frame, text="Runyakitara Translation", padx=10, pady=10)
        trans_frame.pack(fill=BOTH, expand=True, pady=5)
        
        self.translation_output = Text(trans_frame, height=10, width=70, 
                                    state=DISABLED, wrap=WORD,
                                    font=('Arial', 10), padx=5, pady=5)
        self.translation_output.pack(fill=BOTH, expand=True)
        
        # Action buttons
        action_frame = Frame(main_frame)
        action_frame.pack(fill=X, pady=5)
        
        self.translate_btn = Button(action_frame, text="🔁 Translate", 
                                  command=self.translate_thread,
                                  state=DISABLED,
                                  font=('Arial', 10, 'bold'))
        self.translate_btn.pack(side=LEFT, padx=5)
        
        self.save_btn = Button(action_frame, text="💾 Save Translation", 
                             command=self.save_translation,
                             state=DISABLED,
                             font=('Arial', 10))
        self.save_btn.pack(side=LEFT, padx=5)
        
        self.clear_btn = Button(action_frame, text="❌ Clear All", 
                              command=self.clear_all,
                              font=('Arial', 10))
        self.clear_btn.pack(side=RIGHT, padx=5)
        
        # Status bar
        self.status_var = StringVar()
        self.status_var.set("Ready")
        status_bar = Label(self.root, textvariable=self.status_var, 
                         bd=1, relief=SUNKEN, anchor=W,
                         font=('Arial', 9))
        status_bar.pack(side=BOTTOM, fill=X)
    
    def record_audio_thread(self):
        Thread(target=self.record_audio, daemon=True).start()
    
    def translate_thread(self):
        Thread(target=self.translate_to_runyakitara, daemon=True).start()
    
    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def record_audio(self):
        self.update_status("Recording... Speak now!")
        self.record_btn.config(state=DISABLED)
        
        try:
            duration = 20  # seconds
            sample_rate = 44100
            audio_data = sd.rec(int(duration * sample_rate), 
                              samplerate=sample_rate, 
                              channels=1, 
                              dtype='int16')
            sd.wait()
            
            with wave.open(self.AUDIO_FILENAME, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data.tobytes())
            
            self.update_status("Transcribing audio...")
            english_text = self.transcribe_audio(self.AUDIO_FILENAME)
            
            if english_text:
                self.text_input.delete(1.0, END)
                self.text_input.insert(END, english_text)
                self.translate_btn.config(state=NORMAL)
                self.update_status("Ready - Text transcribed successfully")
            else:
                self.update_status("Error - Could not transcribe audio")
                
        except Exception as e:
            messagebox.showerror("Recording Error", str(e))
            self.update_status("Error during recording")
        finally:
            self.record_btn.config(state=NORMAL)
            if os.path.exists(self.AUDIO_FILENAME):
                os.remove(self.AUDIO_FILENAME)
    
    def upload_audio(self):
        filepath = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[("Audio Files", "*.wav *.mp3 *.ogg"), ("All Files", "*.*")]
        )
        
        if filepath:
            self.update_status(f"Processing {os.path.basename(filepath)}...")
            try:
                # Convert to WAV if needed
                if not filepath.lower().endswith('.wav'):
                    audio = AudioSegment.from_file(filepath)
                    filepath = "converted_audio.wav"
                    audio.export(filepath, format="wav")
                
                english_text = self.transcribe_audio(filepath)
                
                if english_text:
                    self.text_input.delete(1.0, END)
                    self.text_input.insert(END, english_text)
                    self.translate_btn.config(state=NORMAL)
                    self.update_status("Ready - Text transcribed successfully")
                else:
                    self.update_status("Error - Could not transcribe audio")
                    
            except Exception as e:
                messagebox.showerror("Processing Error", str(e))
                self.update_status("Error processing audio file")
            finally:
                if filepath != "converted_audio.wav" and os.path.exists("converted_audio.wav"):
                    os.remove("converted_audio.wav")
    
    def transcribe_audio(self, audio_file_path):
        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(audio_file_path) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data)
                return text
        except sr.UnknownValueError:
            messagebox.showerror("Transcription Error", "Could not understand audio")
            return None
        except sr.RequestError as e:
            messagebox.showerror("API Error", f"Could not request results: {e}")
            return None
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            return None
    
    def translate_to_runyakitara(self):
        english_text = self.text_input.get(1.0, END).strip()
        if not english_text:
            messagebox.showerror("Error", "No text to translate")
            return
            
        self.update_status("Translating...")
        self.translate_btn.config(state=DISABLED)
        
        try:
            prompt = """You are a professional translator specializing in Runyakitara language 
            (a Bantu language spoken in western Uganda, specifically in the Ankole region). 
            Translate the following English text to Runyakitara clearly and accurately.
            Use proper Runyakitara grammar and vocabulary.
            Return ONLY the Runyakitara translation without any additional commentary or explanation.
            
            English: {text}
            Runyakitara:""".format(text=english_text)
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                # Clean the response to remove any potential English explanations
                translation = response.text.split('\n')[0].strip()
                if translation.lower().startswith(('runyakitara:', 'translation:')):
                    translation = translation.split(':', 1)[1].strip()
                
                self.translation_output.config(state=NORMAL)
                self.translation_output.delete(1.0, END)
                self.translation_output.insert(END, translation)
                self.translation_output.config(state=DISABLED)
                self.save_btn.config(state=NORMAL)
                self.update_status("Translation complete")
            else:
                messagebox.showerror("Error", "No translation returned from API")
                self.update_status("Translation failed")
                
        except Exception as e:
            messagebox.showerror("Translation Error", str(e))
            self.update_status("Error during translation")
        finally:
            self.translate_btn.config(state=NORMAL)
    
    def save_translation(self):
        translation = self.translation_output.get(1.0, END).strip()
        if not translation:
            messagebox.showerror("Error", "No translation to save")
            return
            
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Save Translation"
        )
        
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(translation)
                self.update_status(f"Translation saved to {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Save Error", str(e))
                self.update_status("Error saving file")
    
    def clear_all(self):
        self.text_input.delete(1.0, END)
        self.translation_output.config(state=NORMAL)
        self.translation_output.delete(1.0, END)
        self.translation_output.config(state=DISABLED)
        self.translate_btn.config(state=DISABLED)
        self.save_btn.config(state=DISABLED)
        self.update_status("Ready")

if __name__ == "__main__":
    root = Tk()
    app = TranslatorApp(root)
    root.mainloop()
