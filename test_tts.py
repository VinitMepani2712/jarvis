import pyttsx3

engine = pyttsx3.init()
engine.setProperty("rate", 150)
engine.setProperty("volume", 1.0)

voices = engine.getProperty("voices")
print("Voices available:", [v.name for v in voices])

engine.say("Hello from Jarvis test.")
engine.runAndWait()
