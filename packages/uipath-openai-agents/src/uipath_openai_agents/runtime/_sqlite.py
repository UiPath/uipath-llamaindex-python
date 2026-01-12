"""Async SQLite connection manager with automatic serialization."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from contextlib import asynccontextmanager
from sqlite3 import Row
from typing import Any, AsyncIterator

import aiosqlite


class AsyncSqlite:
    """Async SQLite wrapper with automatic serialization via locks.

    Provides thread-safe access to a SQLite database using asyncio locks
    to serialize operations. Maintains a single connection and ensures
    proper WAL mode configuration.
    """

    def __init__(self, db_path: str, timeout: float = 30.0):
        """
        Initialize AsyncSQLite manager.

        Args:
            db_path: Path to the SQLite database file
            timeout: Database connection timeout in seconds
        """
        self.db_path = db_path
        self.timeout = timeout
        self.conn: aiosqlite.Connection | None = None
        self.lock = asyncio.Lock()
        self.is_setup = False

    async def __aenter__(self) -> AsyncSqlite:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args) -> None:
        """Async context manager exit."""
        await self.close()

    async def connect(self) -> None:
        """Establish database connection and apply initial pragmas."""
        if self.conn is not None:
            return

        self.conn = await aiosqlite.connect(self.db_path, timeout=self.timeout)
        await self._apply_connection_pragmas()

        # WAL mode is persistent, set once
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.commit()

    async def close(self) -> None:
        """Close database connection."""
        if self.conn:
            try:
                # Commit any pending transactions before closing
                await self.conn.commit()
            except Exception:
                pass  # Best effort

            try:
                await self.conn.close()
            except Exception:
                pass  # Best effort cleanup

            self.conn = None
            self.is_setup = False

    async def execute(
        self, query: str, parameters: tuple[Any, ...] | None = None
    ) -> aiosqlite.Cursor:
        """
        Execute a single query with automatic locking.

        Args:
            query: SQL query to execute
            parameters: Query parameters

        Returns:
            Cursor with query results
        """
        if self.conn is None:
            await self.connect()

        assert self.conn is not None

        async with self.lock:
            return await self.conn.execute(query, parameters or ())

    async def executemany(
        self, query: str, parameters_list: list[tuple[Any, ...]]
    ) -> None:
        """
        Execute a query multiple times with different parameters.

        Args:
            query: SQL query to execute
            parameters_list: List of parameter tuples
        """
        if self.conn is None:
            await self.connect()

        assert self.conn is not None

        async with self.lock:
            await self.conn.executemany(query, parameters_list)
            await self.conn.commit()

    async def executescript(self, script: str) -> None:
        """
        Execute a SQL script (multiple statements).

        Args:
            script: SQL script to execute
        """
        if self.conn is None:
            await self.connect()

        assert self.conn is not None

        async with self.lock:
            await self.conn.executescript(script)
            await self.conn.commit()

    async def commit(self) -> None:
        """Commit the current transaction."""
        if self.conn is None:
            return

        assert self.conn is not None

        async with self.lock:
            await self.conn.commit()

    @asynccontextmanager
    async def cursor(self) -> AsyncIterator[aiosqlite.Cursor]:
        """
        Get a cursor with automatic locking.

        Yields:
            Database cursor
        """
        if self.conn is None:
            await self.connect()

        assert self.conn is not None

        async with self.lock:
            cursor = await self.conn.cursor()
            try:
                yield cursor
            finally:
                await cursor.close()

    async def fetchone(
        self, query: str, parameters: tuple[Any, ...] | None = None
    ) -> Row | None:
        """
        Execute query and fetch one result.

        Args:
            query: SQL query to execute
            parameters: Query parameters

        Returns:
            Single row or None
        """
        cursor = await self.execute(query, parameters)
        return await cursor.fetchone()

    async def fetchall(
        self, query: str, parameters: tuple[Any, ...] | None = None
    ) -> Iterable[Row]:
        """
        Execute query and fetch all results.

        Args:
            query: SQL query to execute
            parameters: Query parameters

        Returns:
            List of rows
        """
        cursor = await self.execute(query, parameters)
        return await cursor.fetchall()

    async def _apply_connection_pragmas(self) -> None:
        """Apply per-connection PRAGMA settings for optimal concurrency."""
        if self.conn is None:
            return

        await self.conn.execute(f"PRAGMA busy_timeout={int(self.timeout * 1000)}")
        await self.conn.execute("PRAGMA synchronous=NORMAL")
        await self.conn.execute("PRAGMA cache_size=10000")
        await self.conn.execute("PRAGMA temp_store=MEMORY")
