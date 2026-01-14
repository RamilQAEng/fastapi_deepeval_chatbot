from typing import Literal

from pydantic import BaseModel, Field


class RAGTestCase(BaseModel):
    input: str = Field(..., description="The user query or input")
    actual_output: str = Field(..., description="The RAG system's answer")
    retrieval_context: list[str] | None = Field(default=[], description="Context retrieved by RAG")
    expected_output: str | None = Field(None, description="Golden answer for reference")
    context: list[str] | None = Field(None, description="Golden context for reference")


class DatasetConfig(BaseModel):
    name: str | None = Field("Uploaded Dataset", description="Name of the dataset")
    format: Literal["json", "csv", "xlsx"] = "json"
    test_cases: list[RAGTestCase]


class GenerateDatasetRequest(BaseModel):
    text: str | None = None
    file_path: str | None = None
    num_questions: int = Field(5, ge=1, le=50)


class EvaluationRequest(BaseModel):
    dataset_id: int
    metrics: list[str] = Field(default=["answer_relevancy", "faithfulness", "contextual_precision"])
