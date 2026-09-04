# tests/test_docker_context.py
# Проверяет, что Docker build context не включает env-файлы и локальные зависимости.

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DockerContextTests(unittest.TestCase):
    def test_backend_context_excludes_secrets_and_local_artifacts(self) -> None:
        patterns = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()

        self.assertIn(".env", patterns)
        self.assertIn(".env.*", patterns)
        self.assertIn("venv", patterns)
        self.assertIn("node_modules", patterns)

    def test_backend_dockerfile_copies_only_backend_sources(self) -> None:
        dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("COPY backend ./backend", dockerfile)
        self.assertNotIn("COPY . .", dockerfile)

    def test_frontend_context_excludes_env_and_node_modules(self) -> None:
        patterns = (
            PROJECT_ROOT / "frontend" / ".dockerignore"
        ).read_text(encoding="utf-8").splitlines()

        self.assertIn(".env", patterns)
        self.assertIn(".env.*", patterns)
        self.assertIn("node_modules", patterns)
        self.assertIn("dist", patterns)


if __name__ == "__main__":
    unittest.main()
