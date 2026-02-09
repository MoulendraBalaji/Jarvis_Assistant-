import tkinter as tk
import time
import datetime
import threading
import webbrowser
import os
import sys

# Third-party libraries
try:
    import customtkinter as ctk
    from PIL import Image, ImageTk
    import speech_recognition as sr
    import pyttsx3
    import pywhatkit
    import wikipedia
    import pyjokes
    import google.generativeai as genai
    from dotenv import load_dotenv
except ImportError:
    print("Missing libraries. Please install: pip install -r requirements.txt")
    sys.exit(1)

# Load environment variables
load_dotenv()

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Text-to-Speech Engine
engine = pyttsx3.init()
voices = engine.getProperty('voices')
# Set a male voice (usually index 0 on Windows)
try:
    engine.setProperty('voice', voices[0].id)
except:
    pass
engine.setProperty('rate', 170)  # Speed of speech

# --- Gemini Setup ---
if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    model = None
    print("Note: Gemini API Key not found in .env. Falling back to basic commands only.")

# --- Assistant Logic Class ---
class JarvisAssistant:
    def __init__(self, output_callback, status_callback):
        self.output_callback = output_callback
        self.status_callback = status_callback
        self.is_listening = False
        self.recognizer = sr.Recognizer()

    def speak(self, text):
        self.output_callback(f"Jarvis: {text}")
        engine.say(text)
        engine.runAndWait()

    def listen(self):
        try:
            with sr.Microphone() as source:
                self.status_callback("Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                voice = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                
                self.status_callback("Processing...")
                command = self.recognizer.recognize_google(voice, language='en-in')
                command = command.lower()
                self.output_callback(f"You: {command}")
                return command
        except sr.WaitTimeoutError:
            self.status_callback("Listening timed out.")
            return None
        except sr.UnknownValueError:
            self.status_callback("Did not catch that.")
            return None
        except sr.RequestError:
            self.output_callback("Network Error.")
            return None
        except Exception as e:
            print(e)
            return None

    def ask_gemini(self, query):
        if not model:
            return "I am unable to access my brain (Gemini API Key missing)."
        try:
            # Add context that it is an assistant named Jarvis
            prompt = f"You are Jarvis, a helpful AI assistant. Keep responses concise and conversational. User says: {query}"
            response = model.generate_content(prompt)
            return response.text.replace("*", "") # Clean up markdown slightly for speech
        except Exception as e:
            return f"I encountered an error accessing Gemini: {str(e)}"

    def execute_command(self, command):
        if not command:
            return

        command = command.lower()
        if 'jarvis' in command:
            command = command.replace('jarvis', '').strip()

        # --- Basic Commands ---
        if 'play' in command:
            song = command.replace('play', '').strip()
            self.speak(f"Playing {song} on YouTube")
            pywhatkit.playonyt(song)
        
        elif 'time' in command:
            time_now = datetime.datetime.now().strftime('%I:%M %p')
            self.speak(f"The current time is {time_now}")

        elif 'date' in command:
            date_now = datetime.datetime.now().strftime('%B %d, %Y')
            self.speak(f"Today is {date_now}")

        elif 'who is' in command or 'what is' in command and 'gemini' not in command:
            # Fallback to Wikipedia for specific fact checks if Gemini isn't preferred
            # But usually Gemini acts better. Let's try Wikipedia first for strict definitions
            try:
                topic = command.replace('who is', '').replace('what is', '').strip()
                info = wikipedia.summary(topic, sentences=2)
                self.speak(info)
            except:
                # If wikipedia fails, ask Gemini
                response = self.ask_gemini(command)
                self.speak(response)

        elif 'open google' in command:
            self.speak("Opening Google")
            webbrowser.open("google.com")

        elif 'open youtube' in command:
            self.speak("Opening YouTube")
            webbrowser.open("youtube.com")

        elif 'joke' in command:
            self.speak(pyjokes.get_joke())

        elif 'shutdown' in command:
            self.speak("Shadow protocol initiated. Shutting down system.")
            self.status_callback("Shutting down...")
            os.system("shutdown /s /t 1")

        elif 'exit' in command or 'quit' in command:
            self.speak("Goodbye, Sir.")
            sys.exit()

        else:
            # Default to Gemini for conversation
            if model:
                response = self.ask_gemini(command)
                self.speak(response)
            else:
                self.speak("I'm not sure how to help with that, and my Gemini connection is offline.")

# --- GUI Application ---
class JarvisApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("JARVIS AI")
        self.geometry("600x700")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self.header_label = ctk.CTkLabel(self, text="J.A.R.V.I.S", font=("Roboto Medium", 30))
        self.header_label.grid(row=0, column=0, pady=20, sticky="ew")

        # Chat/Log Area
        self.chat_area = ctk.CTkTextbox(self, width=500, height=400, font=("Consolas", 14))
        self.chat_area.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.chat_area.configure(state="disabled") # Read-only initially

        # Status Label
        self.status_label = ctk.CTkLabel(self, text="System Online", font=("Roboto", 14), text_color="cyan")
        self.status_label.grid(row=2, column=0, pady=5)

        # Buttons Frame
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=3, column=0, pady=20)

        # Listen Button (The "Arc Reactor")
        self.listen_button = ctk.CTkButton(
            self.button_frame, 
            text="LISTEN", 
            command=self.start_listening_thread,
            width=200, 
            height=50, 
            corner_radius=25,
            fg_color="#00A2E8",
            hover_color="#0077BE",
            font=("Roboto Bold", 16)
        )
        self.listen_button.pack(pady=10)

        # Initialize Assistant
        self.assistant = JarvisAssistant(self.update_chat, self.update_status)

        # Initial greeting thread
        threading.Thread(target=self.initial_greeting, daemon=True).start()

    def update_chat(self, message):
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", message + "\n\n")
        self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

    def update_status(self, status):
        self.status_label.configure(text=status)

    def initial_greeting(self):
        # Brief delay to let UI load
        time.sleep(1)
        self.assistant.speak("Systems initialized. Ready for commands.")

    def start_listening_thread(self):
        # Run listening in a separate thread to keep UI responsive
        threading.Thread(target=self.run_listening_cycle, daemon=True).start()

    def run_listening_cycle(self):
        self.listen_button.configure(state="disabled", text="LISTENING...")
        command = self.assistant.listen()
        self.listen_button.configure(state="normal", text="LISTEN")
        
        if command:
            self.assistant.execute_command(command)
        else:
            self.update_status("Waiting...")

if __name__ == "__main__":
    app = JarvisApp()
    app.mainloop()
