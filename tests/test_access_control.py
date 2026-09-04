# tests/test_access_control.py
# Проверяет отказ при присвоении задаче чужой или несуществующей категории.

import unittest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from backend.access_control import require_owned_task_category
from backend.database import TaskCategory


class TaskCategoryAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_none_category_is_allowed_without_query(self) -> None:
        session = AsyncMock()

        category = await require_owned_task_category(session, None, user_id=11)

        self.assertIsNone(category)
        session.execute.assert_not_awaited()

    async def test_owned_category_is_returned(self) -> None:
        session = AsyncMock()
        result = MagicMock()
        expected = TaskCategory(id=7, user_id=11, name="Работа", category_type="custom")
        result.scalar_one_or_none.return_value = expected
        session.execute.return_value = result

        category = await require_owned_task_category(session, 7, user_id=11)

        self.assertIs(category, expected)
        statement = session.execute.await_args.args[0]
        compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("task_categories.id = 7", compiled)
        self.assertIn("task_categories.user_id = 11", compiled)

    async def test_foreign_or_missing_category_is_rejected(self) -> None:
        session = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session.execute.return_value = result

        with self.assertRaises(HTTPException) as caught:
            await require_owned_task_category(session, 7, user_id=11)

        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(
            caught.exception.detail,
            "Category does not belong to the current user",
        )


if __name__ == "__main__":
    unittest.main()
