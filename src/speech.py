## Adding Voice feature in order to facilitate search by speaking
## Speech-to-text conversion, result = query.
import os
from dotenv import load_dotenv
import speech_recognition as sr

load_dotenv()
wit_ai_key = os.getenv("WIT_AI_KEY")

def listen_and_transcribe():
  r = sr.Recognizer()

  with sr.Microphone() as source:
    print("Speak now...")
    audio = r.listen(source)

  try:
    text = r.recognize_wit(audio, key=wit_ai_key)
    print(f"You said: {text}")

  except sr.UnknownValueError:
    print("Could not understand audio")

  except sr.RequestError:
    print("API request error")

if __name__ == "__main__":
  listen_and_transcribe()