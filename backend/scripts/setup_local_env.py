"""Create a private local backend .env with generated secrets.

Run from any directory:
    python backend/scripts/setup_local_env.py

The script never prints secret values and never overwrites an existing non-placeholder
secret. It is safe to re-run.
"""
from __future__ import annotations

import argparse
import os
import secrets
import tempfile
from pathlib import Path


SECRET_KEYS = {"JWT_SECRET", "PASSWORD_PEPPER", "CRON_SECRET"}


def prepare_env(template: str, existing: str | None) -> str:
    existing_values: dict[str, str] = {}
    if existing is not None:
        for line in existing.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            existing_values[key.strip()] = value.strip()

    output: list[str] = []
    seen: set[str] = set()
    for line in template.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            output.append(line)
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in existing_values and existing_values[key] and existing_values[key] != "CHANGE_ME":
            value = existing_values[key]
        elif key in SECRET_KEYS and (not value.strip() or value.strip() == "CHANGE_ME"):
            value = secrets.token_urlsafe(48)
        output.append(f"{key}={value}")
        seen.add(key)

    for key, value in existing_values.items():
        if key not in seen:
            output.append(f"{key}={value}")
    return "\n".join(output) + "\n"


def setup(directory: Path) -> Path:
    directory = directory.resolve()
    template_path = directory / ".env.example"
    env_path = directory / ".env"
    if not template_path.is_file():
        raise FileNotFoundError(f"Environment template not found: {template_path}")
    if env_path.is_symlink():
        raise RuntimeError(f"Refusing to write through a symlink: {env_path}")

    existing = env_path.read_text(encoding="utf-8") if env_path.exists() else None
    content = prepare_env(template_path.read_text(encoding="utf-8"), existing)
    directory.mkdir(parents=True, exist_ok=True)

    fd, temporary_name = tempfile.mkstemp(prefix=".env.", dir=directory, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, env_path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return env_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a private local TutorInn backend .env file.")
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Backend directory containing .env.example (defaults to this script's backend directory).",
    )
    args = parser.parse_args()
    path = setup(args.directory)
    print(f"Created/updated {path}")
    print("Generated missing local secrets without displaying them; existing non-placeholder values were preserved.")
    print("Keep this file private. It is intended to be ignored by Git.")


if __name__ == "__main__":
    main()
