import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import Settings


class LLMUnavailableError(RuntimeError):
    pass


class GroqClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def complete(self, messages: list[dict[str, str]], temperature: float = 0.1) -> str:
        if not self.settings.groq_api_key:
            raise LLMUnavailableError("GROQ_API_KEY is not configured")
        response = httpx.post(
            f"{self.settings.groq_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.settings.groq_api_key}"},
            json={
                "model": self.settings.groq_model,
                "messages": messages,
                "temperature": temperature,
            },
            timeout=self.settings.groq_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
