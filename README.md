
#  RAG Evaluation System (Pet Project)

A robust, production-ready system to **generate**, **manage**, and **evaluate** synthetic datasets for RAG (Retrieval-Augmented Generation) pipelines.

Built with **FastAPI**, **PostgreSQL**, **DeepEval**, and **OpenRouter**.

![Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

##  Features

*   **Synthetic Data Generation**: Automatically create Q&A pairs from raw text context using LLMs (via OpenRouter).
*   **Automated Evaluation**: Run DeepEval metrics (Faithfulness, Answer Relevancy) in background tasks.
*   **Russian Localization**: Custom metrics ensure rationale ("Reason") is generated in **Russian language**.
*   **Dataset Management**: Upload custom JSON datasets or generate them on the fly.
*   **Persistence**: All datasets, runs, and results are stored in PostgreSQL.
*   **Async Architecture**: Fully asynchronous API and Database interactions for high performance.

##  Tech Stack

*   **Backend**: Python 3.12, FastAPI, SQLAlchemy (Async), Pydantic V2.
*   **Database**: PostgreSQL 16 (via Docker).
*   **LLM Integration**: OpenRouter (access to GPT-4, Gemini, Claude, etc.), DeepEval.
*   **Migration**: Alembic.
*   **Package Manager**: Poetry.

##  Quick Start

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

##  API Documentation

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

## Project Structure

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

## Testing and Verification

### 1. Running Unit Tests
Run all tests using pytest:
```bash
poetry run pytest
```

### 2. Verification Scripts (End-to-End)
The project includes ready-made scripts to verify the entire pipeline (DB -> LLM -> API).

| Script | Description | Command |
|--------|-------------|---------|
| `tests/verify_pipeline.py` | **Basic Check**: Generate dataset from text + Run evaluation. | `poetry run python tests/verify_pipeline.py` |
| `tests/verify_analytics.py` | **Analytics Check**: Outputs detailed statistics of the last run (speed, pass rate). | `poetry run python tests/verify_analytics.py` |
| `tests/verify_mixed_quality.py` | **Stress Test**: Creates a dataset with good, medium, and poor answers to verify metric discrimination. | `poetry run python tests/verify_mixed_quality.py` |

> **Important**: Containers (`docker-compose up`) or a local server must be running for scripts to work.

### 3. Database Migrations
If you changed models, don't forget to update the database:
```bash
# Apply all migrations (to head)
poetry run alembic upgrade head

# Create a new migration (automatically)
poetry run alembic revision --autogenerate -m "description"
```

### 4. CI Pipeline (GitHub Actions)
Automatic checks are configured in `.github/workflows/ci.yml` for every push to `main`:
1.  **Linting**: `ruff`, `black`
2.  **Type Checking**: `mypy`
3.  **Unit Tests**: `pytest`

### 5. Pre-commit (Linting)
To check code before committing (to avoid pushing errors):

```bash
# Install hooks (once)
poetry run pre-commit install

# Run checks manually (for all files)
poetry run pre-commit run --all-files
```

##  Localization
To ensure evaluation reasons are in Russian, we use custom overrides in `src/metrics/russian.py`. This patches `DeepEval`'s prompt templates dynamically.

---
**Author**: Ramil Allahverdiev
**License**: MIT
