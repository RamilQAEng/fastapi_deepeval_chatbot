from fastapi import FastAPI

from src.api.endpoints.rag import rag_router

# Check if other routers exist and import them if possible.
# For now, we assume we might need to recreate main if it doesn't exist or is minimal.

app = FastAPI(title="Pet Project (DeepEval) RAG API")

app.include_router(rag_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
