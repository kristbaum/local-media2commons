"""Wiki credentials, resolved the same way by every step that needs them.

Credentials come from the environment or an interactive prompt only. They are
never written to a file, a log or a CSV.
"""

from __future__ import annotations

import getpass
import os

COMMONS_USERNAME_ENV = "COMMONS_USERNAME"
COMMONS_PASSWORD_ENV = "COMMONS_PASSWORD"

# The source wiki is edited by step 2b, under its own account.
LOCAL_WIKI_USERNAME_ENV = "LOCAL_WIKI_USERNAME"
LOCAL_WIKI_PASSWORD_ENV = "LOCAL_WIKI_PASSWORD"


def get_credentials(
    username: str | None = None,
    *,
    wiki: str = "Commons",
    username_env: str = COMMONS_USERNAME_ENV,
    password_env: str = COMMONS_PASSWORD_ENV,
) -> tuple[str, str]:
    """Resolve credentials from CLI args, the environment, or a prompt."""
    username = (
        username
        or os.environ.get(username_env)
        or input(f"{wiki} username: ").strip()
    )
    password = os.environ.get(password_env) or getpass.getpass(
        f"{wiki} bot password: "
    )
    if not username or not password:
        raise SystemExit(f"Username and password are required for {wiki}.")
    return username, password


def local_wiki_credentials(username: str | None = None) -> tuple[str, str]:
    """Credentials for the source wiki rather than for Commons."""
    return get_credentials(
        username,
        wiki="Source wiki",
        username_env=LOCAL_WIKI_USERNAME_ENV,
        password_env=LOCAL_WIKI_PASSWORD_ENV,
    )
