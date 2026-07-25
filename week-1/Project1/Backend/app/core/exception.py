from fastapi import HTTPException


class AppException(HTTPException):
    def __init__(
        self,
        status_code: int,
        message: str,
        error_code: str,
    ):
        super().__init__(status_code=status_code, detail=message)
        self.error_code = error_code