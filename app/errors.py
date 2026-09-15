class ApiError(Exception):
    """An error returned to the client as {"error": {"code", "message"}}."""

    def __init__(self, status: int, code: str, message: str, headers: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.headers = headers


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}
