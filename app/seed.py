class SeedError(RuntimeError):
    """Raised when the seed command cannot proceed. Carries a stable `code` for operators."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
