class UpstreamError(Exception):
    """itsm-api returned an HTTP error response (4xx/5xx)."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class UpstreamUnreachableError(Exception):
    """itsm-api could not be reached at all (connection refused, DNS, timeout)."""
