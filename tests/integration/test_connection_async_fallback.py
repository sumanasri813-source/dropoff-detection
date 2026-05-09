from __future__ import annotations

import asyncio
import unittest

from src.db import connection


class AsyncConnectionFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_get_database_url = connection.get_database_url
        connection.get_database_url.cache_clear()
        connection.get_engine.cache_clear()
        connection.get_session_factory.cache_clear()
        connection.get_async_database_url.cache_clear()
        connection.get_async_engine.cache_clear()
        connection.get_async_session_factory.cache_clear()

    def tearDown(self) -> None:
        connection.get_database_url = self.original_get_database_url
        connection.get_database_url.cache_clear()
        connection.get_engine.cache_clear()
        connection.get_session_factory.cache_clear()
        connection.get_async_database_url.cache_clear()
        connection.get_async_engine.cache_clear()
        connection.get_async_session_factory.cache_clear()

    def test_async_url_builder_for_sqlite(self) -> None:
        def mock_get_database_url() -> str:
            return "sqlite:///:memory:"

        connection.get_database_url = mock_get_database_url
        connection.get_async_database_url.cache_clear()

        self.assertEqual(connection.get_async_database_url(), "sqlite+aiosqlite:///:memory:")

    def test_get_async_session_falls_back_to_sync_session(self) -> None:
        def mock_get_database_url() -> str:
            return "sqlite:///:memory:"

        connection.get_database_url = mock_get_database_url
        connection.get_engine.cache_clear()
        connection.get_session_factory.cache_clear()
        connection.get_async_database_url.cache_clear()
        connection.get_async_engine.cache_clear()
        connection.get_async_session_factory.cache_clear()

        async def _acquire_session_type_name() -> str:
            async with connection.get_async_session() as session:
                return type(session).__name__

        session_type_name = asyncio.run(_acquire_session_type_name())
        self.assertEqual(session_type_name, "Session")


if __name__ == "__main__":
    unittest.main()
