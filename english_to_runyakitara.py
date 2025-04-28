import os
import google.generativeai as genai
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
        self.root.title("Enhanced English to Runyakitara Translator")
        self.root.geometry("700x550")
        
        # Configuration (API key hardcoded)
        self.GEMINI_API_KEY = "AIzaSyBU0nYJ79vuTX5CbJReS43Ygz96l_zrpgs"
        self.AUDIO_FILENAME = "recorded_audio.wav"
        self.model = None
        self.history = []  # Store translation history for context
        self.max_history = 5  # Maximum number of past translations to keep
        
        self.setup_ui()
        self.initialize_gemini()
        
    def initialize_gemini(self):
        """Initialize Gemini API with the hardcoded key and configure advanced settings"""
        try:
            genai.configure(api_key=self.GEMINI_API_KEY)
            generation_config = {
                "temperature": 0.1,  # Lower temperature for more precise translations
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
            
            self.model = genai.GenerativeModel(
                model_name='gemini-1.5-flash',
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            self.update_status("API initialized successfully with enhanced settings")
        except Exception as e:
            messagebox.showerror("API Error", f"Failed to initialize Gemini API: {str(e)}")
            self.root.destroy()

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
        
        self.record_btn = Button(btn_frame, text="🎤 Record Audio (20s)", 
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
        self.status_var.set("Ready")
        status_bar = Label(status_frame, textvariable=self.status_var, 
                         bd=0, anchor=W, font=('Arial', 9))
        status_bar.pack(side=LEFT, fill=X, expand=True, padx=5)
        
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate', length=100)
        self.progress.pack(side=RIGHT, padx=5, pady=2)
        
        # Initialize glossary
        self.glossary = self.load_glossary()
    
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
                "thank you": "webale",
                "goodbye": "oreebe",
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
        # Remove any explanations or metadata, keeping only the translation
        
        # Try to match common patterns that indicate a direct translation
        patterns = [
            r'(?:^|\n)"([^"]+)"',  # Text in quotes
            r'(?:^|\n)([^:]+)$',   # Last line that doesn't contain a colon
            r'Runyakitara:[\s\n]*([^\n]+)',  # After "Runyakitara:"
            r'Runyakitara translation:[\s\n]*([^\n]+)',  # After "Runyakitara translation:"
            r'Translation:[\s\n]*([^\n]+)',  # After "Translation:"
            r'\b([A-Za-z\s,]+)\b(?=\s*$)',  # Any word sequence at the end
        ]
        
        # Try each pattern
        for pattern in patterns:
            matches = re.search(pattern, response_text, re.MULTILINE)
            if matches:
                return matches.group(1).strip()
        
        # If no patterns match, use the first line only
        first_line = response_text.split('\n')[0]
        return first_line.strip()
    
    def translate_to_runyakitara(self):
        english_text = self.text_input.get(1.0, END).strip()
        if not english_text:
            messagebox.showerror("Error", "No text to translate")
            return
            
        self.update_status("Translating...")
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
            
            # Create a strict prompt that only returns the translation
            prompt = """Translate this English text to Runyakitara language (spoken in western Uganda). 
            IMPORTANT: Your response must contain ONLY the Runyakitara translation. 
            DO NOT include explanations, notes, or anything other than the direct translation.
            DO NOT use quotes or formatting.
            
            English: {text}""".format(text=english_text)
            
            response = self.model.generate_content(prompt)
            
            if response.text:
                # Get the raw translation and clean it
                translation = response.text.strip()
                
                # Remove any explanation text and get only the direct translation
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
                self.update_status("Translation complete")
            else:
                messagebox.showerror("Error", "No translation returned from API")
                self.update_status("Translation failed")
                
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