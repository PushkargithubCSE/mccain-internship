from http import HTTPStatus


class AppException(Exception):
    def __init__(self, message: str, status_code: HTTPStatus):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ResourceNotFound(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, HTTPStatus.NOT_FOUND)


class BadRequest(AppException):
    def __init__(self, message: str = "Bad request"):
        super().__init__(message, HTTPStatus.BAD_REQUEST)


class Unauthorized(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, HTTPStatus.UNAUTHORIZED)


class Conflict(AppException):
    def __init__(self, message: str = "Conflict"):
        super().__init__(message, HTTPStatus.CONFLICT)