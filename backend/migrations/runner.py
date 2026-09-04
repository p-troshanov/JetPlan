# backend/migrations/runner.py
# Применяет SQL-файлы по порядку и фиксирует версии в служебной таблице.
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


MIGRATIONS_DIR = Path(__file__).resolve().parent


async def run_migrations(engine: AsyncEngine) -> list[str]:
    applied: list[str] = []
    async with engine.begin() as connection:
        await connection.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version VARCHAR PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
            ")"
        ))
        result = await connection.execute(text("SELECT version FROM schema_migrations"))
        known_versions = set(result.scalars().all())

        for migration_path in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql")):
            version = migration_path.stem
            if version in known_versions:
                continue
            sql = migration_path.read_text(encoding="utf-8")
            statements = [statement.strip() for statement in sql.split(";") if statement.strip()]
            for statement in statements:
                await connection.execute(text(statement))
            await connection.execute(
                text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                {"version": version},
            )
            applied.append(version)
    return applied
