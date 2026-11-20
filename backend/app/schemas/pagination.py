"""Limit/offset pagination: query parameters in, `Page[T]` out. Shared by every list endpoint."""

from pydantic import BaseModel, Field

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class PaginationParams(BaseModel):
    """`?limit=&offset=` query parameters. Out-of-range values → automatic 422."""

    limit: int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)
    offset: int = Field(default=0, ge=0)


class Page[T](BaseModel):
    """One page of a list endpoint (≈ a TS `Page<T>` generic).

    `T` is filled in per endpoint: `-> Page[InviteRead]` shows up in OpenAPI as its own
    schema (`Page_InviteRead_`) with typed `items`.
    """

    items: list[T]
    total: int = Field(description="Number of rows across all pages.")
    limit: int
    offset: int
