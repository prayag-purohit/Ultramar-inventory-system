from gemini_processor import GeminiProcessor
from io import StringIO

import pandas as pd

def main(document_path: str):
    gemini = GeminiProcessor(
        model_name="gemini-1.5-flash",
        temperature=0.3,  # Set your API key here or load from environment
        enable_google_search=False       # Enable Google Search tool
    )

    prompt = gemini.load_prompt_template("prompt_template.md")

    gemini.upload_file(document_path=document_path)

    response = gemini.generate_content(
        prompt=prompt)

    response_text = response.text
    response_text = response.text.strip()
    if response_text.startswith("```csv"):
        response_text = response_text.replace("```csv", "").strip()
    if response_text.endswith("```"):
        response_text = response_text[:-3].strip()

    csv_file = StringIO(response_text)
    df = pd.read_csv(csv_file)
    return df