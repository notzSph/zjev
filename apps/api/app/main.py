"""FastAPI composition root for Jevzoo."""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .api.v1.routers.evaluations import router as evaluations_router
from .api.v1.routers.outreach import router as outreach_router
from .api.v1.routers.system import router as system_router
from .core.config import APISettings


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        APISettings.from_env().validate()
        yield

    application = FastAPI(title="Jevzoo API", version="0.1.0", lifespan=lifespan)
    application.include_router(system_router)
    application.include_router(evaluations_router)
    application.include_router(outreach_router)

    @application.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:128]
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @application.exception_handler(ValueError)
    async def value_error_handler(_request: Request, error: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"error": str(error)})

    return application


app = create_app()
