from fastapi import Request
from fastapi.responses import JSONResponse
from .global_error import GlobalError
from .models import ErrorResponse


async def global_error_handler(request: Request, exc: GlobalError):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            status_code=exc.status_code,
            message=exc.detail
        ).model_dump()
    )
