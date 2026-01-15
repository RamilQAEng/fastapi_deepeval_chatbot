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


class MetricStats(BaseModel):
    name: str = Field(..., description="Metric name")
    avg_score: float = Field(..., description="Average score (0-1)")
    pass_rate: float = Field(..., description="Percentage of passed tests (0-1)")
    passed_count: int = Field(..., description="Number of passed tests")
    total_count: int = Field(..., description="Total tests for this metric")


class EvaluationResultItem(BaseModel):
    metric: str
    score: float
    reason: str | None
    input: str | None
    output: str | None


class EvaluationResponse(BaseModel):
    id: int
    status: str
    model_name: str | None = None
    created_at: str
    finished_at: str | None = None
    duration_seconds: float | None = None
    avg_seconds_per_question: float | None = None
    metrics_stats: list[MetricStats]
    results: list[EvaluationResultItem]
