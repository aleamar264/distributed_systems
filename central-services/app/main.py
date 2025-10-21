from api.central import router as central_routes
from auth.routes import router as auth_route
from common.schemas import GenericResponse
from fastapi import FastAPI

app = FastAPI()
app.include_router(central_routes)
app.include_router(auth_route)

@app.get("/health", tags=["health"], response_model=GenericResponse)
def health_check()->GenericResponse:
    return GenericResponse(ok=True, message="store healthy")


@app.get("/metrics", tags=["observability"])
async def metrics():
    ...
