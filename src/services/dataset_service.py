from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models.evaluation import Dataset
from src.schemas.models import RAGTestCase


class DatasetService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_dataset(self, name: str, test_cases: list[RAGTestCase]) -> Dataset:
        dataset = Dataset(name=name, content=[tc.model_dump() for tc in test_cases])
        self.db.add(dataset)
        await self.db.commit()
        await self.db.refresh(dataset)
        return dataset

    async def get_dataset(self, dataset_id: int) -> Dataset | None:
        stmt = select(Dataset).where(Dataset.id == dataset_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def generate_synthetic_from_text(
        self, text: str, num_questions: int = 5
    ) -> list[RAGTestCase]:
        # Utilizing direct LLM call via OpenRouter instead of DeepEval Synthesizer
        # to avoid compatibility issues and have better control over JSON output.
        import json

        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            base_url=settings.OPENAI_API_BASE,
            api_key=settings.OPENAI_API_KEY,
        )

        prompt = f"""
        You are an expert at creating synthetic datasets for RAG evaluation.

        Given the following text context, generate {num_questions} diverse Q&A pairs.
        Test different aspects: factual retrieval, reasoning, and synthesis.

        CONTEXT:
        {text}

        Return output as JSON list. Each object must have:
        - "input": The question.
        - "expected_output": The correct answer based ONLY on the context.
        - "context": A list containing the specific text snippet used to answer.

        Example:
        [
            {{
                "input": "What is ...?",
                "expected_output": "It is ...",
                "context": ["relevant sentence..."]
            }}
        ]
        """

        try:
            response = await client.chat.completions.create(
                model=settings.DEEPEVAL_OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful data generator assistant. Return only JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or ""
            # Handle potential wrapping keys like {"data": [...]} or just [...]
            data = json.loads(content)

            # If the LLM wraps it in a key (common behavior for json_object mode), extract the list
            if isinstance(data, dict):
                # Try to find the list in values
                for _, value in data.items():
                    if isinstance(value, list):
                        data = value
                        break

            if not isinstance(data, list):
                # Fallback if structure is unexpected
                raise ValueError(f"LLM did not return a list of Q&A pairs (got {type(data)})")

            return [
                RAGTestCase(
                    input=item["input"],
                    actual_output="",
                    retrieval_context=item.get(
                        "context", [text]
                    ),  # Fallback to full text if context missing
                    expected_output=item["expected_output"],
                    context=item.get("context", [text]),
                )
                for item in data
            ]

        except json.JSONDecodeError as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to decode JSON from LLM: {e}. Content: {content}")
            raise ValueError("LLM returned invalid JSON") from e
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error generating dataset: {e}")
            raise e
