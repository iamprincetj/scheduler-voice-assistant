from fastapi import HTTPException


class GlobalError(HTTPException):
    def __init__(self, status_code: int, message: str):
        super().__init__(status_code, detail=message)
