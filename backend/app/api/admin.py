"""`/admin` endpoints: invites (and users, next). Admin role required for every route."""

from fastapi import APIRouter, Depends

from app.api.deps import InviteServiceDep, PaginationDep, require_role
from app.models.user import UserRole
from app.schemas import InviteRead, Page

# Router-level dependency: runs before every route below (≈ `@UseGuards(RolesGuard)` +
# `@Roles('admin')` on a NestJS controller). Its return value isn't passed to handlers;
# a handler that needs the admin object takes `admin: AdminUser` as well (cached per
# request, so the check doesn't run twice). `responses` documents 401/403 in OpenAPI.
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Admin role required"},
    },
)


@router.get("/invites")
async def list_invites(invites: InviteServiceDep, pagination: PaginationDep) -> Page[InviteRead]:
    """All invites, newest first, with their derived status."""
    rows, total = await invites.list(pagination)
    return Page[InviteRead](
        items=[InviteRead.model_validate(invite) for invite in rows],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )
