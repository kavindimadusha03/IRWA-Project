import json
from typing import Any, Dict
from groq import Groq
from app.config import get_settings

settings = get_settings()


class GroqLLM:
    def __init__(self):
        self.enabled = bool(settings.groq_api_key and "put-your" not in settings.groq_api_key)
        self.client = Groq(api_key=settings.groq_api_key) if self.enabled else None

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        if not self.enabled:
            raise RuntimeError("Groq API key is not configured in .env")
        response = self.client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=700,
        )
        return response.choices[0].message.content or ""

    def chat_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        raw = self.chat(system_prompt, user_prompt, temperature=0.0).strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        return json.loads(raw)


llm = GroqLLM()
