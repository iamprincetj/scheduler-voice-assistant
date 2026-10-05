from pydantic import BaseModel


class ErrorResponse(BaseModel):
    status_code: int
    message: str
