"""
Global error handlers for the application.
"""

from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging

from app.schemas.common import ErrorResponse


logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI):
    """Register global error handlers for the application."""
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        logger.error(f"Validation error: {exc}")

        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="validation_error",
                detail="Invalid input data"
            ).model_dump()
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
        """Handle Pydantic validation errors."""
        logger.error(f"Pydantic validation error: {exc}")

        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="validation_error",
                detail="Invalid data format"
            ).model_dump()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error(f"General error: {exc}", exc_info=True)

        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="internal_error",
                detail="An internal server error occurred"
            ).model_dump()
        )
