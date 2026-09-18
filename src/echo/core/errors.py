"""User-friendly domain errors for Echo of the Inkwell."""

from __future__ import annotations


class EchoError(Exception):
    """Base error for all Echo failures."""

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        self.message = message
        self.hint = hint
        super().__init__(self.user_message)

    @property
    def user_message(self) -> str:
        if self.hint:
            return f"{self.message} ({self.hint})"
        return self.message


class BackendUnavailable(EchoError):
    """Raised when a generation backend cannot be used."""

    def __init__(
        self,
        backend: str,
        reason: str,
        *,
        hint: str | None = None,
    ) -> None:
        self.backend = backend
        self.reason = reason
        default_hint = hint or (
            "Install optional extras, set credentials, or enable mock mode "
            "(ECHO_MOCK_GENERATION=1 / generation.json use_mock_backend)."
        )
        super().__init__(
            f"Backend '{backend}' is unavailable: {reason}",
            hint=default_hint,
        )


class GateBlocked(EchoError):
    """Raised when a production gate prevents an action."""

    def __init__(self, gate: str, *, detail: str | None = None, hint: str | None = None) -> None:
        self.gate = gate
        msg = f"Production gate blocked: {gate}"
        if detail:
            msg = f"{msg} — {detail}"
        super().__init__(
            msg,
            hint=hint or "Complete the required approval step, then retry.",
        )


class ValidationError(EchoError):
    """Raised for invalid inputs, missing files, or schema problems."""

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message, hint=hint or "Check the input and try again.")
