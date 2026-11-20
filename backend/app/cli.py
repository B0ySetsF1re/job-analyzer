"""Admin commands: `uv run python -m app.cli --help` (or the `make` targets).

Typer builds the CLI from type hints, like FastAPI builds the API (≈ `nest-commander`).
Commands are sync functions; async work runs through `asyncio.run(...)`.
"""

import asyncio
from typing import Annotated

import typer
from pydantic import TypeAdapter, ValidationError

from app.db import dispose_engine, get_sessionmaker
from app.schemas import Email, Password
from app.services.users import UserService

cli = typer.Typer(no_args_is_help=True)


@cli.callback()
def main() -> None:
    """Job Analyzer admin commands."""
    # With a single command, Typer would make it the root command (`app.cli EMAIL`).
    # A callback keeps subcommand mode, so the call stays `app.cli create-admin EMAIL`.


async def _run_create_admin(email: str, password: str) -> bool:
    """Open a session for one command, and close the connection pool afterwards."""
    try:
        async with get_sessionmaker()() as session:
            return await UserService(session).create_or_promote_admin(email, password)
    finally:
        # The API closes the pool in its lifespan; a CLI process has no lifespan.
        await dispose_engine()


@cli.command()
def create_admin(
    email: Annotated[str, typer.Argument(help="Email of the admin account.")],
    password: Annotated[
        str,
        typer.Option(
            prompt=True,
            hide_input=True,
            confirmation_prompt=True,
            help="Asked interactively if omitted (keeps it out of shell history).",
        ),
    ],
) -> None:
    """Create an admin account, or promote an existing user to admin."""
    # Same rules as `POST /auth/register`: `TypeAdapter` validates a plain value against a
    # type, without a model around it (≈ `zodSchema.parse(value)`).
    try:
        email = TypeAdapter(Email).validate_python(email)
        password = TypeAdapter(Password).validate_python(password)
    except ValidationError as err:
        raise typer.BadParameter(err.errors()[0]["msg"]) from None

    created = asyncio.run(_run_create_admin(email, password))
    typer.echo(f"{'Created' if created else 'Promoted'} admin {email}")


# `python -m app.cli ...` runs this module as a script; importing it (tests) doesn't.
if __name__ == "__main__":
    cli()
