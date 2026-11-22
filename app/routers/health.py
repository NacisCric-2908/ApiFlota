from fastapi import APIRouter

router = APIRouter(tags=["Salud"])


@router.get("/health", summary="Estado del servicio")
async def health() -> dict:
    return {"estado": "ok"}
