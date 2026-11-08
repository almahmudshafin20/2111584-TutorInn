from fastapi import APIRouter

router = APIRouter(tags=["System"])


@router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "database": "configured"}


@router.get("/api/hello")
def hello(name: str = "World") -> dict[str, str]:
    return {"message": f"Hello, {name}!"}
