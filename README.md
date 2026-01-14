
# 🧠 RAG Evaluation System (Pet Project)

A robust, production-ready system to **generate**, **manage**, and **evaluate** synthetic datasets for RAG (Retrieval-Augmented Generation) pipelines.

Built with **FastAPI**, **PostgreSQL**, **DeepEval**, and **OpenRouter**.

![Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

## 🚀 Features

*   **Synthetic Data Generation**: Automatically create Q&A pairs from raw text context using LLMs (via OpenRouter).
*   **Automated Evaluation**: Run DeepEval metrics (Faithfulness, Answer Relevancy) in background tasks.
*   **Russian Localization**: Custom metrics ensure rationale ("Reason") is generated in **Russian language**.
*   **Dataset Management**: Upload custom JSON datasets or generate them on the fly.
*   **Persistence**: All datasets, runs, and results are stored in PostgreSQL.
*   **Async Architecture**: Fully asynchronous API and Database interactions for high performance.

## 🛠 Tech Stack

*   **Backend**: Python 3.12, FastAPI, SQLAlchemy (Async), Pydantic V2.
*   **Database**: PostgreSQL 16 (via Docker).
*   **LLM Integration**: OpenRouter (access to GPT-4, Gemini, Claude, etc.), DeepEval.
*   **Migration**: Alembic.
*   **Package Manager**: Poetry.

## 🏃‍♂️ Quick Start

### Prerequisites
*   Docker & Docker Compose
*   Python 3.11+
*   Poetry (`curl -sSL https://install.python-poetry.org | python3 -`)
*   **OpenRouter API Key**

### 1. Clone & Configure
```bash
git clone <your-repo-url>
cd pet-project-rag
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY (OpenRouter Key)
```

### 2. Run with Docker (Recommended)
```bash
docker-compose up --build
```
The API will be available at: `http://localhost:8000/docs`

### 3. Local Development (Manual)
```bash
# Start DB
docker-compose up -d db

# Install dependencies
poetry install

# Run Migrations
poetry run alembic upgrade head

# Start App
poetry run uvicorn src.api.main:app --reload --loop asyncio
```

## 📚 API Documentation

### 1. Generate Dataset
**POST** `/api/v1/datasets/generate`
```json
{
  "text": "Your long context text here...",
  "num_questions": 5
}
```

### 2. Upload Dataset
**POST** `/api/v1/datasets/upload?run_eval=true`
Upload a pre-made JSON dataset and immediately trigger evaluation.

### 3. Check Evaluation
**GET** `/api/v1/evaluations/{run_id}`
Returns status (`pending`, `completed`, `failed`) and detailed metric scores/reasons.

## 🏗 Project Structure

```
.
├── migrations/         # Database migrations (Alembic)
├── src/
│   ├── api/            # FastAPI Endpoints & router
│   ├── core/           # Config & DB connection
│   ├── metrics/        # Custom DeepEval metrics (Russian localization)
│   ├── models/         # SQLAlchemy Database Models
│   ├── schemas/        # Pydantic Schemas
│   └── services/       # Business Logic (Dataset & Evaluation)
├── tests/              # Verification scripts
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## 🔄 CI/CD & Testing

### Verification Scripts
We have included automated scripts to test the entire pipeline:
```bash
# Test Upload & Eval
poetry run python tests/verify_upload.py

# Test Generation & Eval
poetry run python tests/verify_pipeline.py
```

### CI Pipeline (GitHub Actions)
See `.github/workflows/ci.yml`. Triggers on push to `main`.
1.  Sets up Python & Poetry.
2.  Runs Linting (`ruff`, `black`).
3.  Runs Type Checking (`mypy`).
4.  Runs Unit Tests (`pytest`).

## 🇷🇺 Localization
To ensure evaluation reasons are in Russian, we use custom overrides in `src/metrics/russian.py`. This patches `DeepEval`'s prompt templates dynamically.

---
**Author**: Ramil Allahverdiev
**License**: MIT
