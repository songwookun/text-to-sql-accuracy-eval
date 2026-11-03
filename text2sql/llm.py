import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

MODEL = "gemini-3.5-flash"


def extract_sql(text: str) -> str:
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    return (m.group(1) if m else text).strip()


def generate_sql(prompt: str, retries: int = 3) -> str:
    client = genai.Client()
    for attempt in range(retries):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0),
            )
            return extract_sql(resp.text or "")
        except errors.ServerError:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt * 5)
