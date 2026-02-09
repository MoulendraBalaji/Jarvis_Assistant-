import customtkinter as ctk
import datetime
import webbrowser
import os
import sys
import threading
import google.generativeai as genai
from dotenv import load_dotenv

# Optional Libraries with Graceful Fallback
CAN_SPEAK = False
CAN_LISTEN = False

try:
    import pyttsx3
    CAN_SPEAK = True
except ImportError:
    print("Text-to-speech library missing.")

try:
    import speech_recognition as sr
    import pyaudio
    CAN_LISTEN = True
except ImportError:
    print("Speech recognition libraries missing.")
    
try:
    import pywhatkit
    import wikipedia
    import pyjokes
except ImportError:
    pass

# --- UI Setup ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class ModernJarvisApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Configuration ---
        self.title("J.A.R.V.I.S")
        self.geometry("450x650")
        self.resizable(False, False)
        
        # Load Env
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key and self.api_key != "YOUR_GEMINI_API_KEY_HERE":
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-flash-latest')
        else:
            self.model = None

        # --- Audio Engine ---
        self.engine = None
        self.recognizer = None
        self.can_speak = CAN_SPEAK
        self.can_listen = CAN_LISTEN
        
        if self.can_speak:
            try:
                self.engine = pyttsx3.init()
                voices = self.engine.getProperty('voices')
                try:
                    self.engine.setProperty('voice', voices[0].id)
                except: pass
                self.engine.setProperty('rate', 175)
            except Exception as e:
                print(f"TTS Engine Init Failed: {e}")
                self.can_speak = False

        if self.can_listen:
            try:
                self.recognizer = sr.Recognizer()
            except Exception as e:
                print(f"Recognizer Init Failed: {e}")
                self.can_listen = False

        # --- UI Elements ---
        
        # Header "Arc Reactor" Effect
        self.reactor_frame = ctk.CTkFrame(self, width=450, height=100, corner_radius=0, fg_color="transparent")
        self.reactor_frame.pack(pady=(10, 5))
        
        self.status_label = ctk.CTkLabel(self.reactor_frame, text="SYSTEM ONLINE", font=("Orbitron", 24, "bold"), text_color="#00FFFF")
        self.status_label.place(relx=0.5, rely=0.5, anchor="center")

        # Chat History
        self.chat_display = ctk.CTkTextbox(self, width=410, height=340, corner_radius=15, font=("Roboto", 14))
        self.chat_display.pack(pady=5)
        
        init_msg = "Jarvis: protocols initialized. Waiting for input...\n\n"
        if not self.can_speak:
            init_msg += "[Status: Speech Output Unavailable]\n"
        if not self.can_listen:
            init_msg += "[Status: Microphone Input Unavailable (Text Only)]\n\n"
            
        self.chat_display.insert("0.0", init_msg)
        self.chat_display.configure(state="disabled")

        # Control Panel (Voice Button)
        self.control_frame = ctk.CTkFrame(self, width=410, height=70, corner_radius=15)
        self.control_frame.pack(pady=5)

        listen_text = "ACTIVATE VOICE"
        listen_color = "#00A8E8"
        if not self.can_listen:
            listen_text = "MIC UNAVAILABLE"
            listen_color = "#555555"

        self.listen_btn = ctk.CTkButton(
            self.control_frame, 
            text=listen_text, 
            width=380, 
            height=50, 
            corner_radius=25,
            fg_color=listen_color,
            hover_color="#0077B6" if self.can_listen else "#555555", 
            font=("Roboto", 16, "bold"),
            command=self.start_listening_thread,
            state="normal" if self.can_listen else "disabled"
        )
        self.listen_btn.place(relx=0.5, rely=0.5, anchor="center")
        
        # Manual Input Frame (Text Mode)
        self.input_frame = ctk.CTkFrame(self, width=410, height=60, corner_radius=15, fg_color="transparent")
        self.input_frame.pack(pady=10)

        self.input_entry = ctk.CTkEntry(self.input_frame, width=300, placeholder_text="Type command here...")
        self.input_entry.pack(side="left", padx=(10, 5))
        self.input_entry.bind("<Return>", lambda event: self.process_text_input())

        self.send_btn = ctk.CTkButton(self.input_frame, text="SEND", width=80, command=self.process_text_input)
        self.send_btn.pack(side="left")

        # Thread lock for speaking
        self.is_speaking = False

    def log(self, text):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", text + "\n\n")
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")

    def speak(self, text):
        self.log(f"Jarvis: {text}")
        if self.can_speak and self.engine:
            self.is_speaking = True
            self.status_label.configure(text="SPEAKING...", text_color="#00FF00")
            threading.Thread(target=self._speak_thread, args=(text,), daemon=True).start()
        else:
            # Text only mode
            pass

    def _speak_thread(self, text):
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except:
            pass
        self.status_label.configure(text="SYSTEM ONLINE", text_color="#00FFFF")
        self.is_speaking = False

    def start_listening_thread(self):
        if not self.can_listen:
            return
        if not self.is_speaking:
            threading.Thread(target=self.listen_process, daemon=True).start()

    def listen_process(self):
        self.listen_btn.configure(state="disabled", text="LISTENING...", fg_color="#FF4500")
        self.status_label.configure(text="LISTENING...", text_color="#FF4500")
        
        command = ""
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                voice = self.recognizer.listen(source, timeout=5, phrase_time_limit=8)
                self.status_label.configure(text="PROCESSING...", text_color="#FFFF00")
                command = self.recognizer.recognize_google(voice)
                self.log(f"You: {command}")
        except Exception:
            self.speak("I didn't catch that, Sir.")
            self.reset_ui()
            return

        self.process_command(command.lower())
        self.reset_ui()

    def process_text_input(self):
        command = self.input_entry.get()
        if not command:
            return
        self.input_entry.delete(0, "end")
        self.log(f"You: {command}")
        self.process_command(command.lower())

    def reset_ui(self):
        if self.can_listen:
            self.listen_btn.configure(state="normal", text="ACTIVATE VOICE", fg_color="#00A8E8")
        self.status_label.configure(text="SYSTEM ONLINE", text_color="#00FFFF")

    def process_command(self, command):
        
        if 'play' in command:
             try:
                import pywhatkit
                song = command.replace('play', '').strip()
                self.speak(f"Playing {song}")
                pywhatkit.playonyt(song)
             except ImportError:
                self.speak("Media module (pywhatkit) not available.")
             except Exception as e:
                self.speak(f"Could not play media: {e}")
            
        elif 'time' in command:
            time = datetime.datetime.now().strftime('%I:%M %p')
            self.speak(f"It is {time}")
            
        elif 'open google' in command:
            self.speak("Accessing Google Database.")
            webbrowser.open("google.com")

        elif 'shutdown' in command:
            self.speak("Initiating shutdown sequence.")
            os.system("shutdown /s /t 1")
            
        elif 'who is' in command:
             # Basic fallback
             try:
                 import wikipedia
                 person = command.replace('who is', '').strip()
                 sentences = 1 if self.can_speak else 3
                 info = wikipedia.summary(person, sentences=sentences)
                 self.speak(info)
             except ImportError:
                 self.ask_gemini(command)
             except Exception:
                 self.ask_gemini(command)
        else:
            self.ask_gemini(command)

    def ask_gemini(self, prompt):
        if not self.model:
            self.speak("I cannot access my neural network (Gemini API Key Missing).")
            return
            
        try:
            response = self.model.generate_content(f"You are Jarvis. Be concise. Reply to: {prompt}")
            text = response.text.replace("*", "")
            self.speak(text)
        except Exception as e:
            self.speak(f"Error accessing neural network: {e}")

if __name__ == "__main__":
    app = ModernJarvisApp()
    app.mainloop()
