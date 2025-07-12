## Adding Voice feature in order to facilitate search by speaking
## Speech-to-text conversion, result = query.
import os
from dotenv import load_dotenv
import speech_recognition as sr

load_dotenv()
wit_ai_key = os.getenv("WIT_AI_KEY")

def fetch_query_by_voice():
  r = sr.Recognizer()
  with sr.Microphone() as source:
    audio = r.listen(source)

  try:
    query = r.recognize_wit(audio, key=wit_ai_key)
    # print("You said: " + query)

  except sr.UnknownValueError:
    print("Could not understand audio")
    return ""
  except sr.RequestError:
    print("API request error")
    return ""
  return query

if __name__ == "__main__":
  query = fetch_query_by_voice()
  print(query)