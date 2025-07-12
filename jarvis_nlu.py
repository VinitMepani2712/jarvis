import os, openai
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))


load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def parse_intent(text):
    prompt = (
        "You are an assistant that maps user requests into one of: "
        "OPEN_BROWSER, GET_TIME, EXIT, UNKNOWN. "
        f"User: \"{text}\"\nIntent:"
    )
    resp = openai.Completion.create(
        model="gpt-3.5-turbo",
        prompt=prompt,
        max_tokens=10,
        temperature=0
    )
    return resp.choices[0].text.strip()