from common.schemas import GenericResponse
from fastapi import FastAPI

from .routes.central import router as central_routes

app = FastAPI()
app.include_router(central_routes)

@app.get("/health", tags=["health"], response_model=GenericResponse)
def health_check()->GenericResponse:
    return GenericResponse(ok=True, message="store healthy")


@app.get("/metrics", tags=["observability"])
async def metrics():
    ...
