import speech_recognition as sr
import pyttsx3
import webbrowser
import json
import time
from difflib import get_close_matches

# Initialize text-to-speech engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Adjust speaking speed

# Sample services for differently-abled users
services = {
    "screen_reader": "https://syllogismtech.com/screen-reader",
    "voice_commands": "https://syllogismtech.com/voice-navigation",
    "braille_support": "https://syllogismtech.com/braille",
    "ai_assistant": "https://syllogismtech.com/ai-assistant",
    "text_magnifier": "https://syllogismtech.com/text-magnifier"
}

def speak(text):
    """Convert text to speech."""
    engine.say(text)
    engine.runAndWait()

def listen():
    """Recognize voice input."""
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source)
            command = recognizer.recognize_google(audio).lower()
            return command
        except sr.UnknownValueError:
            return "Sorry, I didn't understand that."
        except sr.RequestError:
            return "Network error. Please check your connection."

def find_service(query):
    """Find closest matching service based on voice input."""
    matches = get_close_matches(query, services.keys(), n=1, cutoff=0.5)
    if matches:
        return matches[0], services[matches[0]]
    return None, None

def main():
    speak("Welcome to Syllogism Technology. How can I assist you today?")
    while True:
        command = listen()
        if "exit" in command or "quit" in command:
            speak("Goodbye! Have a great day.")
            break
        
        service, url = find_service(command)
        if service:
            speak(f"Opening {service} for you.")
            webbrowser.open(url)
        else:
            speak("Sorry, I couldn't find that service. Please try again.")
        
        time.sleep(1)

if __name__ == "__main__":
    main()
