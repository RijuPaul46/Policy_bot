from app.generation.llm import GroqClient
from app.generation.prompts import QUERY_REWRITE_PROMPT


class QueryRewriter:
    def __init__(self, llm: GroqClient):
        self.llm = llm

    def rewrite(self, question: str, history: list[dict[str, str]]) -> str:
        if not history:
            return question
        transcript = "\n".join(
            f"{turn['role']}: {turn['content']}" for turn in history[-8:]
        )
        rewritten = self.llm.complete(
            [
                {"role": "system", "content": QUERY_REWRITE_PROMPT},
                {
                    "role": "user",
                    "content": f"Conversation:\n{transcript}\nLatest message: {question}",
                },
            ]
        )
        return rewritten or question
