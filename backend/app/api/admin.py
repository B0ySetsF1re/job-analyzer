"""`/admin` endpoints: invites (and users, next). Admin role required for every route."""

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import AdminUser, InviteServiceDep, PaginationDep, require_role
from app.models.user import UserRole
from app.schemas import InviteCreate, InviteCreated, InviteRead, Page

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


@router.post(
    "/invites",
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "Email already registered"}},
)
async def create_invite(
    body: InviteCreate, invites: InviteServiceDep, admin: AdminUser
) -> InviteCreated:
    """Invite an email to register. The response holds the plain code: it's shown only once."""
    invite, code = await invites.create(body, admin)
    # The row's fields via `InviteRead`, plus the code, which isn't stored on the row.
    # `status` is computed, so it's left out of the input (`InviteCreated` computes it again).
    invite_read = InviteRead.model_validate(invite)
    return InviteCreated(**invite_read.model_dump(exclude={"status"}), code=code)


# 204 No Content: success without a body, so the handler returns `None`.
@router.delete(
    "/invites/{invite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Invite not found"},
        409: {"description": "Invite already used"},
    },
)
async def revoke_invite(invite_id: uuid.UUID, invites: InviteServiceDep) -> None:
    """Revoke an unused invite (pending or expired), so its code stops working."""
    await invites.revoke(invite_id)
