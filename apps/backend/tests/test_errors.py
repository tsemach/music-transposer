from backend.errors import BackendError, OmrFailedError


def test_omr_failed_error_carries_returncode_and_stderr():
    error = OmrFailedError(2, "boom")

    assert error.returncode == 2
    assert error.stderr == "boom"
    assert isinstance(error, BackendError)
