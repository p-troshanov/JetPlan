# backend/migrations/__init__.py
# Экспортирует файловый runner идемпотентных SQL-миграций JetPlan.
from backend.migrations.runner import run_migrations


__all__ = ["run_migrations"]
