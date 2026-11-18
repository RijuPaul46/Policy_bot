from app.generation.llm import GroqClient
from app.generation.prompts import SYSTEM_PROMPT
from app.retrieval.retriever import Retriever


class Answerer:
    def __init__(self, retriever: Retriever, llm: GroqClient):
        self.retriever = retriever
        self.llm = llm

    def answer(self, query: str) -> tuple[str, list[dict]]:
        hits = self.retriever.retrieve(query)
        if not hits:
            return "I could not find this information in the indexed policy documents.", []
        passages = []
        for index, hit in enumerate(hits, start=1):
            label = self.retriever.citation(hit, index)
            passages.append(f"{label}\n{hit['text']}")
            hit["citation"] = label
        answer = self.llm.complete(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Question: {query}\n\nPolicy excerpts:\n\n"
                        + "\n\n".join(passages)
                    ),
                },
            ]
        )
        return answer, hits
