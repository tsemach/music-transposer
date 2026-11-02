class BackendError(Exception):
    pass


class AudiverisNotFoundError(BackendError):
    pass


class InvalidInputError(BackendError):
    pass


class NoOutputError(BackendError):
    pass


class OmrFailedError(BackendError):
    def __init__(self, returncode: int, stderr: str):
        super().__init__(f"Audiveris failed with exit code {returncode}: {stderr}")
        self.returncode = returncode
        self.stderr = stderr
