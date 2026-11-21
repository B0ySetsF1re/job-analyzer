"""Domain errors raised by services; one app-level handler turns them into HTTP responses.

Services don't know about HTTP; they raise e.g. `EmailTaken()`, and the handler in
`app/main.py` answers with its `status_code` and `{"detail": ...}` (≈ NestJS
`throw new ConflictException()` + an exception filter).
`HTTPStatus` is the stdlib enum, so this module doesn't import FastAPI.
"""

from http import HTTPStatus


class DomainError(Exception):
    """Base class: subclasses set `status_code` and a default `detail`."""

    status_code: HTTPStatus = HTTPStatus.BAD_REQUEST
    detail: str = "Bad request"

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class NotFound(DomainError):
    """The requested row doesn't exist (or, later, belongs to another user)."""

    status_code = HTTPStatus.NOT_FOUND
    detail = "Not found"


class Conflict(DomainError):
    """The request clashes with the current state of the row, e.g. revoking a used invite."""

    status_code = HTTPStatus.CONFLICT
    detail = "Conflict"


class InvalidInvite(DomainError):
    """Unknown, used, expired or other-email invite: one message, so guessers learn nothing."""

    detail = "Invalid or expired invite code"


class InvalidCredentials(DomainError):
    """Unknown email, wrong password or inactive account: one message for all three."""

    status_code = HTTPStatus.UNAUTHORIZED
    detail = "Invalid email or password"


class EmailTaken(DomainError):
    status_code = HTTPStatus.CONFLICT
    detail = "Email already registered"
