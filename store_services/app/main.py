from common.schemas import GenericResponse
from fastapi import Depends, FastAPI
from fastapi.security import HTTPBearer

from .routes.store import router as store_routes

app = FastAPI()
bearer = HTTPBearer()
app.include_router(store_routes, dependencies=[Depends(bearer)])


@app.get("/health", tags=["health"], response_model=GenericResponse)
def health_check()->GenericResponse:
    return GenericResponse(ok=True, message="store healthy")


@app.get("/metrics", tags=["observability"])
async def metrics():
    ...
