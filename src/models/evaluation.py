import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.core.db import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    content: Mapped[list[dict[str, Any]]] = mapped_column(JSON)  # Stores list of test cases

    runs: Mapped[list["EvaluationRun"]] = relationship(back_populates="dataset")


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"))
    status: Mapped[RunStatus] = mapped_column(SQLEnum(RunStatus), default=RunStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metrics_used: Mapped[list[str]] = mapped_column(JSON)

    dataset: Mapped["Dataset"] = relationship(back_populates="runs")
    results: Mapped[list["EvaluationResult"]] = relationship(back_populates="run")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("evaluation_runs.id"))
    input: Mapped[str] = mapped_column(String)
    output: Mapped[str] = mapped_column(String)
    score: Mapped[float] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    metric_name: Mapped[str] = mapped_column(String)

    run: Mapped["EvaluationRun"] = relationship(back_populates="results")
