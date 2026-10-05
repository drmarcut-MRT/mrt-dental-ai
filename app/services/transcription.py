from openai import OpenAI
from flask import current_app

def transcribe_audio(filename, audio_bytes, mime_type):
    key=current_app.config["OPENAI_API_KEY"]
    if not key: raise RuntimeError("API configuration error")
    client=OpenAI(api_key=key)
    response=client.audio.transcriptions.create(
        model="whisper-1", file=(filename or "audio.webm",audio_bytes,mime_type), language="ro")
    return (response.text or "").strip()
