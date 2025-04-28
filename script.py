import os
import requests
import speech_recognition as sr
import sounddevice as sd
import wave
from pydub import AudioSegment
from tkinter import *
from tkinter import ttk, messagebox, filedialog
from threading import Thread
import json
import re

class TranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Enhanced English to Runyakitara Translator (Claude)")
        self.root.geometry("700x550")
        
        # Configuration (API key setup)
        self.OPENROUTER_API_KEY = "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"  # Replace with your OpenRouter API key
        self.API_URL = "https://openrouter.ai/api/v1/chat/completions"
        self.MODEL = "anthropic/claude-3-5-sonnet"  # Using Claude 3.5 Sonnet via OpenRouter
        self.AUDIO_FILENAME = "recorded_audio.wav"
        self.history = []  # Store translation history for context
        self.max_history = 5  # Maximum number of past translations to keep
        
        self.setup_ui()
        
    def setup_ui(self):
        # Set theme colors
        bg_color = "#f0f0f0"
        accent_color = "#3498db"
        self.root.configure(bg=bg_color)
        
        # Main container
        main_frame = Frame(self.root, padx=20, pady=20, bg=bg_color)
        main_frame.pack(fill=BOTH, expand=True)
        
        # Input Section
        input_frame = LabelFrame(main_frame, text="Input", padx=10, pady=10, bg=bg_color, font=('Arial', 11, 'bold'))
        input_frame.pack(fill=X, pady=5)
        
        # Recording buttons
        btn_frame = Frame(input_frame, bg=bg_color)
        btn_frame.pack(fill=X, pady=5)
        
        self.record_btn = Button(btn_frame, text="🎤 Record Audio (5s)", 
                               command=self.record_audio_thread,
                               font=('Arial', 10, 'bold'),
                               bg=accent_color, fg="white",
                               padx=10, pady=5)
        self.record_btn.pack(side=LEFT, padx=5)
        
        self.upload_btn = Button(btn_frame, text="📁 Upload Audio File", 
                               command=self.upload_audio,
                               font=('Arial', 10),
                               bg="#27ae60", fg="white",
                               padx=10, pady=5)
        self.upload_btn.pack(side=LEFT, padx=5)
        
        # Text input
        self.text_input = Text(input_frame, height=6, width=70, wrap=WORD,
                             font=('Arial', 11), padx=5, pady=5)
        self.text_input.pack(fill=BOTH, expand=True)
        
        # Translation Options
        options_frame = Frame(main_frame, bg=bg_color)
        options_frame.pack(fill=X, pady=5)
        
        # Add formality selection
        formality_label = Label(options_frame, text="Formality:", bg=bg_color, font=('Arial', 10))
        formality_label.pack(side=LEFT, padx=5)
        
        self.formality_var = StringVar()
        self.formality_var.set("neutral")
        
        formality_options = ttk.Combobox(options_frame, textvariable=self.formality_var, 
                                      values=["formal", "neutral", "informal"],
                                      width=10, state="readonly")
        formality_options.pack(side=LEFT, padx=5)
        
        # Translation Section
        trans_frame = LabelFrame(main_frame, text="Runyakitara Translation", padx=10, pady=10, 
                              bg=bg_color, font=('Arial', 11, 'bold'))
        trans_frame.pack(fill=BOTH, expand=True, pady=5)
        
        self.translation_output = Text(trans_frame, height=10, width=70, 
                                    state=DISABLED, wrap=WORD,
                                    font=('Arial', 11), padx=5, pady=5)
        self.translation_output.pack(fill=BOTH, expand=True)
        
        # Action buttons
        action_frame = Frame(main_frame, bg=bg_color)
        action_frame.pack(fill=X, pady=5)
        
        self.translate_btn = Button(action_frame, text="🔁 Translate", 
                                  command=self.translate_thread,
                                  state=DISABLED,
                                  font=('Arial', 10, 'bold'),
                                  bg=accent_color, fg="white",
                                  padx=10, pady=5)
        self.translate_btn.pack(side=LEFT, padx=5)
        
        self.save_btn = Button(action_frame, text="💾 Save Translation", 
                             command=self.save_translation,
                             state=DISABLED,
                             font=('Arial', 10),
                             bg="#16a085", fg="white",
                             padx=10, pady=5)
        self.save_btn.pack(side=LEFT, padx=5)
        
        # Add glossary button
        self.glossary_btn = Button(action_frame, text="📘 Manage Glossary", 
                                command=self.manage_glossary,
                                font=('Arial', 10),
                                bg="#9b59b6", fg="white",
                                padx=10, pady=5)
        self.glossary_btn.pack(side=LEFT, padx=5)
        
        # Add API key configuration button
        self.config_btn = Button(action_frame, text="⚙️ API Config", 
                               command=self.configure_api,
                               font=('Arial', 10),
                               bg="#f39c12", fg="white",
                               padx=10, pady=5)
        self.config_btn.pack(side=LEFT, padx=5)
        
        self.clear_btn = Button(action_frame, text="❌ Clear All", 
                              command=self.clear_all,
                              font=('Arial', 10),
                              bg="#e74c3c", fg="white",
                              padx=10, pady=5)
        self.clear_btn.pack(side=RIGHT, padx=5)
        
        # Status bar with progress
        status_frame = Frame(self.root, bd=1, relief=SUNKEN)
        status_frame.pack(side=BOTTOM, fill=X)
        
        self.status_var = StringVar()
        self.status_var.set("Ready - Using Claude via OpenRouter for translations")
        status_bar = Label(status_frame, textvariable=self.status_var, 
                         bd=0, anchor=W, font=('Arial', 9))
        status_bar.pack(side=LEFT, fill=X, expand=True, padx=5)
        
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate', length=100)
        self.progress.pack(side=RIGHT, padx=5, pady=2)
        
        # Initialize glossary
        self.glossary = self.load_glossary()
        
        # Load API key from config if exists
        self.load_api_config()
    
    def load_api_config(self):
        """Load API key from config file if it exists"""
        config_path = "openrouter_config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.OPENROUTER_API_KEY = config.get('api_key', '')
                    self.MODEL = config.get('model', 'anthropic/claude-3-5-sonnet')
                    self.update_status(f"Loaded API config - Using {self.MODEL.split('/')[-1]}")
            except Exception as e:
                self.update_status("Error loading API config")
    
    def save_api_config(self):
        """Save API key to config file"""
        config = {
            'api_key': self.OPENROUTER_API_KEY,
            'model': self.MODEL
        }
        with open("openrouter_config.json", 'w') as f:
            json.dump(config, f)
    
    def configure_api(self):
        """Open a window to configure API settings"""
        config_window = Toplevel(self.root)
        config_window.title("API Configuration")
        config_window.geometry("450x250")
        config_window.resizable(False, False)
        
        frame = Frame(config_window, padx=20, pady=20)
        frame.pack(fill=BOTH, expand=True)
        
        # API Key entry
        Label(frame, text="OpenRouter API Key:", font=('Arial', 10, 'bold')).pack(anchor=W, pady=(0, 5))
        api_key_entry = Entry(frame, width=50, show="•")
        api_key_entry.pack(fill=X, pady=(0, 15))
        api_key_entry.insert(0, self.OPENROUTER_API_KEY)
        
        # Model selection
        Label(frame, text="Claude Model:", font=('Arial', 10, 'bold')).pack(anchor=W, pady=(0, 5))
        model_var = StringVar(value=self.MODEL)
        models = [
            "anthropic/claude-3-5-sonnet",
            "anthropic/claude-3-opus",
            "anthropic/claude-3-sonnet",
            "anthropic/claude-3-haiku",
            "anthropic/claude-instant-v1"
        ]
        model_dropdown = ttk.Combobox(frame, textvariable=model_var, values=models, width=45)
        model_dropdown.pack(fill=X, pady=(0, 20))
        
        # Info text
        info_text = """Note: You need an OpenRouter account and API key.
Visit https://openrouter.ai to sign up and get your API key."""
        Label(frame, text=info_text, justify=LEFT, fg="#666").pack(anchor=W, pady=(0, 15))
        
        # Save button
        def save_config():
            self.OPENROUTER_API_KEY = api_key_entry.get().strip()
            self.MODEL = model_var.get()
            self.save_api_config()
            self.update_status(f"API config saved - Using {self.MODEL.split('/')[-1]}")
            config_window.destroy()
        
        Button(frame, text="Save Configuration", command=save_config, 
              bg="#3498db", fg="white", font=('Arial', 10, 'bold'),
              padx=10, pady=5).pack(fill=X)
    
    def load_glossary(self):
        """Load custom glossary from file or create a new one"""
        glossary_path = "runyakitara_glossary.json"
        if os.path.exists(glossary_path):
            try:
                with open(glossary_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        else:
            # Default glossary with some common phrases
            default_glossary = {
                "hello": "oraire gye",
                "good morning": "oraire gye",
                "thank you": "webare",
                "welcome": "twakwakiira",
                "how are you": "ori ota"
            }
            with open(glossary_path, 'w', encoding='utf-8') as f:
                json.dump(default_glossary, f, ensure_ascii=False, indent=2)
            return default_glossary
    
    def save_glossary(self):
        """Save glossary to file"""
        with open("runyakitara_glossary.json", 'w', encoding='utf-8') as f:
            json.dump(self.glossary, f, ensure_ascii=False, indent=2)
    
    def manage_glossary(self):
        """Open a window to manage the custom glossary"""
        glossary_window = Toplevel(self.root)
        glossary_window.title("Runyakitara Translation Glossary")
        glossary_window.geometry("500x400")
        
        # Create frame for the glossary
        frame = Frame(glossary_window, padx=10, pady=10)
        frame.pack(fill=BOTH, expand=True)
        
        # Instructions
        Label(frame, text="Add custom translations to improve accuracy", 
            font=('Arial', 10, 'bold')).pack(anchor=W, pady=(0, 10))
        
        # Entry fields for new terms
        entry_frame = Frame(frame)
        entry_frame.pack(fill=X, pady=5)
        
        Label(entry_frame, text="English:").grid(row=0, column=0, padx=5, pady=5)
        english_entry = Entry(entry_frame, width=20)
        english_entry.grid(row=0, column=1, padx=5, pady=5)
        
        Label(entry_frame, text="Runyakitara:").grid(row=0, column=2, padx=5, pady=5)
        runyakitara_entry = Entry(entry_frame, width=20)
        runyakitara_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # Add button
        def add_term():
            eng = english_entry.get().strip().lower()
            run = runyakitara_entry.get().strip()
            if eng and run:
                self.glossary[eng] = run
                self.save_glossary()
                update_glossary_display()
                english_entry.delete(0, END)
                runyakitara_entry.delete(0, END)
        
        Button(entry_frame, text="Add Term", command=add_term).grid(row=1, column=1, columnspan=2, pady=5)
        
        # Display existing glossary
        display_frame = Frame(frame)
        display_frame.pack(fill=BOTH, expand=True, pady=10)
        
        # Scrollable list
        scrollbar = Scrollbar(display_frame)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        glossary_list = Listbox(display_frame, width=50, height=10, yscrollcommand=scrollbar.set)
        glossary_list.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.config(command=glossary_list.yview)
        
        def update_glossary_display():
            glossary_list.delete(0, END)
            for eng, run in sorted(self.glossary.items()):
                glossary_list.insert(END, f"{eng} → {run}")
        
        update_glossary_display()
        
        # Delete button
        def delete_term():
            selection = glossary_list.curselection()
            if selection:
                term = glossary_list.get(selection[0]).split(" → ")[0]
                if term in self.glossary:
                    del self.glossary[term]
                    self.save_glossary()
                    update_glossary_display()
        
        Button(frame, text="Delete Selected Term", command=delete_term).pack(pady=5)
    
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
        self.progress.start()
        
        try:
            duration = 5  # seconds
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
            self.progress.stop()
            if os.path.exists(self.AUDIO_FILENAME):
                os.remove(self.AUDIO_FILENAME)
    
    def upload_audio(self):
        filepath = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=[("Audio Files", "*.wav *.mp3 *.ogg"), ("All Files", "*.*")]
        )
        
        if filepath:
            self.update_status(f"Processing {os.path.basename(filepath)}...")
            self.progress.start()
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
                self.progress.stop()
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
    
    def check_glossary(self, text):
        """Check if any words or phrases in the text match the glossary"""
        text_lower = text.lower()
        
        # First check for exact matches
        if text_lower in self.glossary:
            return self.glossary[text_lower]
            
        # Then check for partial matches
        for eng, run in self.glossary.items():
            # Case insensitive replacement
            pattern = r'\b' + re.escape(eng) + r'\b'
            text = re.sub(pattern, run, text, flags=re.IGNORECASE)
        return text
    
    def extract_direct_translation(self, response_text):
        """Extract only the direct translation from the API response"""
        # Clean up the response to get only the translation part
        # Common patterns in Claude's responses
        patterns = [
            r'(?:^|\n)"([^"]+)"',  # Text in quotes
            r'Runyakitara:[\s\n]*([^\n]+)',  # After "Runyakitara:"
            r'Runyakitara translation:[\s\n]*([^\n]+)',  # After "Runyakitara translation:"
            r'Translation:[\s\n]*([^\n]+)',  # After "Translation:"
        ]
        
        for pattern in patterns:
            matches = re.search(pattern, response_text, re.MULTILINE)
            if matches:
                return matches.group(1).strip()
        
        # If no patterns match, use the first paragraph
        paragraphs = [p for p in response_text.split('\n') if p.strip()]
        if paragraphs:
            return paragraphs[0].strip()
            
        return response_text.strip()
    
    def translate_to_runyakitara(self):
        english_text = self.text_input.get(1.0, END).strip()
        if not english_text:
            messagebox.showerror("Error", "No text to translate")
            return
            
        # Check if API key is configured
        if not self.OPENROUTER_API_KEY:
            messagebox.showerror("API Error", "OpenRouter API key not configured. Please set it in API Config.")
            self.configure_api()
            return
            
        self.update_status("Translating with Claude...")
        self.translate_btn.config(state=DISABLED)
        self.progress.start()
        
        try:
            # Check if there's a direct match in the glossary
            glossary_match = self.check_glossary(english_text)
            if glossary_match != english_text:  # If glossary changed the text
                self.translation_output.config(state=NORMAL)
                self.translation_output.delete(1.0, END)
                self.translation_output.insert(END, glossary_match)
                self.translation_output.config(state=DISABLED)
                self.save_btn.config(state=NORMAL)
                self.update_status("Translation complete (from glossary)")
                self.progress.stop()
                self.translate_btn.config(state=NORMAL)
                return
            
            # Get formality setting
            formality = self.formality_var.get()
            
            # Create a message for Claude via OpenRouter
            prompt = f"""Translate this English text to Runyakitara language (spoken in western Uganda).
            
            Use a {formality} tone in the translation.
            
            IMPORTANT: Your response must contain ONLY the Runyakitara translation.
            DO NOT include explanations, notes, or anything other than the direct translation.
            DO NOT use quotes or formatting.
            
            English text to translate:
            {english_text}"""
            
            # Create request payload for OpenRouter API
            payload = {
                "model": self.MODEL,
                "messages": [
                    {"role": "system", "content": "You are a professional translator specializing in Runyakitara, a Bantu language spoken in western Uganda. Provide direct, accurate translations only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 1000
            }
            
            headers = {
                "Authorization": f"Bearer {self.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://translator-app.com",  # Replace with your app domain if needed
                "X-Title": "English-Runyakitara Translator"
            }
            
            response = requests.post(self.API_URL, json=payload, headers=headers)
            response.raise_for_status()  # Raise exception for HTTP errors
            
            response_data = response.json()
            if 'choices' in response_data and len(response_data['choices']) > 0:
                # Get the translation from Claude's response
                translation = response_data['choices'][0]['message']['content'].strip()
                
                # Extract just the direct translation
                translation = self.extract_direct_translation(translation)
                
                # Remove any quotation marks or other decorations
                translation = translation.strip('"\'')
                
                # Update translation history
                self.history.append({
                    "english": english_text,
                    "runyakitara": translation
                })
                
                # Keep history within limits
                if len(self.history) > self.max_history:
                    self.history = self.history[-self.max_history:]
                
                self.translation_output.config(state=NORMAL)
                self.translation_output.delete(1.0, END)
                self.translation_output.insert(END, translation)
                self.translation_output.config(state=DISABLED)
                self.save_btn.config(state=NORMAL)
                
                # Calculate token usage for info
                tokens_used = response_data.get('usage', {}).get('total_tokens', 0)
                self.update_status(f"Translation complete - Used {tokens_used} tokens")
            else:
                messagebox.showerror("API Error", "No translation returned from API")
                self.update_status("Translation failed")
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror("API Error", f"OpenRouter API request failed: {str(e)}")
            self.update_status("Error connecting to OpenRouter API")
        except Exception as e:
            messagebox.showerror("Translation Error", str(e))
            self.update_status("Error during translation")
        finally:
            self.progress.stop()
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
                    english = self.text_input.get(1.0, END).strip()
                    f.write(f"English:\n{english}\n\nRunyakitara:\n{translation}")
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