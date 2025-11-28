"""
Async database helpers for OSINT-85 performance optimization.

Provides async versions of database operations to avoid blocking the event loop.
"""

import aiosqlite
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import asdict

from .database import Target, Query, Result


class AsyncDatabase:
    """Async SQLite database operations for TUI responsiveness."""

    def __init__(self, db_path: str = ".osint85/project.db"):
        """
        Initialize async database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Establish async database connection."""
        self._conn = await aiosqlite.connect(str(self.db_path))
        self._conn.row_factory = aiosqlite.Row

    async def close(self):
        """Close async database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    # Async query operations

    async def get_queries_by_category_async(
        self,
        target_id: int,
        category: str,
        enabled_only: bool = True
    ) -> List[Query]:
        """
        Get queries for a category asynchronously.

        Args:
            target_id: Target ID
            category: Category name
            enabled_only: Only return enabled queries

        Returns:
            List of Query objects
        """
        if not self._conn:
            raise RuntimeError("Database connection not established")

        cursor = await self._conn.cursor()

        if enabled_only:
            await cursor.execute(
                """SELECT * FROM queries
                   WHERE target_id = ? AND category = ? AND enabled = 1
                   ORDER BY created_at""",
                (target_id, category)
            )
        else:
            await cursor.execute(
                """SELECT * FROM queries
                   WHERE target_id = ? AND category = ?
                   ORDER BY created_at""",
                (target_id, category)
            )

        rows = await cursor.fetchall()
        await cursor.close()

        return [
            Query(
                id=row['id'],
                target_id=row['target_id'],
                category=row['category'],
                risk_level=row['risk_level'],
                description=row['description'],
                query=row['query'],
                enabled=bool(row['enabled']),
                created_at=row['created_at']
            )
            for row in rows
        ]

    async def get_all_queries_async(self, target_id: int) -> List[Query]:
        """
        Get all queries for a target asynchronously.

        Args:
            target_id: Target ID

        Returns:
            List of Query objects
        """
        if not self._conn:
            raise RuntimeError("Database connection not established")

        cursor = await self._conn.cursor()
        await cursor.execute(
            "SELECT * FROM queries WHERE target_id = ? ORDER BY created_at",
            (target_id,)
        )
        rows = await cursor.fetchall()
        await cursor.close()

        return [
            Query(
                id=row['id'],
                target_id=row['target_id'],
                category=row['category'],
                risk_level=row['risk_level'],
                description=row['description'],
                query=row['query'],
                enabled=bool(row['enabled']),
                created_at=row['created_at']
            )
            for row in rows
        ]

    # Async result operations

    async def get_results_by_query_async(
        self,
        query_id: int,
        limit: Optional[int] = None,
        offset: int = 0,
        exclude_duplicates: bool = True
    ) -> List[Result]:
        """
        Get results for a query asynchronously with pagination.

        Args:
            query_id: Query ID
            limit: Maximum number of results to return
            offset: Number of results to skip
            exclude_duplicates: Exclude duplicate results

        Returns:
            List of Result objects
        """
        if not self._conn:
            raise RuntimeError("Database connection not established")

        cursor = await self._conn.cursor()

        # Build query
        sql = "SELECT * FROM results WHERE query_id = ?"
        params = [query_id]

        if exclude_duplicates:
            sql += " AND is_duplicate = 0"

        sql += " ORDER BY first_seen_at DESC"

        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        await cursor.execute(sql, params)
        rows = await cursor.fetchall()
        await cursor.close()

        return [self._row_to_result(row) for row in rows]

    async def get_all_results_async(
        self,
        target_id: int,
        category: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        exclude_duplicates: bool = True
    ) -> List[Result]:
        """
        Get all results for a target asynchronously with pagination.

        Args:
            target_id: Target ID
            category: Optional category filter
            limit: Maximum number of results to return
            offset: Number of results to skip
            exclude_duplicates: Exclude duplicate results

        Returns:
            List of Result objects
        """
        if not self._conn:
            raise RuntimeError("Database connection not established")

        cursor = await self._conn.cursor()

        # Build query
        sql = """
            SELECT r.*
            FROM results r
            JOIN queries q ON r.query_id = q.id
            WHERE q.target_id = ?
        """
        params = [target_id]

        if category:
            sql += " AND q.category = ?"
            params.append(category)

        if exclude_duplicates:
            sql += " AND r.is_duplicate = 0"

        sql += " ORDER BY r.first_seen_at DESC"

        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        await cursor.execute(sql, params)
        rows = await cursor.fetchall()
        await cursor.close()

        return [self._row_to_result(row) for row in rows]

    async def count_results_async(
        self,
        target_id: int,
        category: Optional[str] = None,
        exclude_duplicates: bool = True
    ) -> int:
        """
        Count results for a target asynchronously.

        Args:
            target_id: Target ID
            category: Optional category filter
            exclude_duplicates: Exclude duplicate results

        Returns:
            Number of results
        """
        if not self._conn:
            raise RuntimeError("Database connection not established")

        cursor = await self._conn.cursor()

        # Build query
        sql = """
            SELECT COUNT(*)
            FROM results r
            JOIN queries q ON r.query_id = q.id
            WHERE q.target_id = ?
        """
        params = [target_id]

        if category:
            sql += " AND q.category = ?"
            params.append(category)

        if exclude_duplicates:
            sql += " AND r.is_duplicate = 0"

        await cursor.execute(sql, params)
        row = await cursor.fetchone()
        await cursor.close()

        return row[0] if row else 0

    async def get_result_async(self, result_id: int) -> Optional[Result]:
        """
        Get single result by ID asynchronously.

        Args:
            result_id: Result ID

        Returns:
            Result object or None if not found
        """
        if not self._conn:
            raise RuntimeError("Database connection not established")

        cursor = await self._conn.cursor()
        await cursor.execute("SELECT * FROM results WHERE id = ?", (result_id,))
        row = await cursor.fetchone()
        await cursor.close()

        return self._row_to_result(row) if row else None

    # Helper methods

    def _row_to_result(self, row) -> Result:
        """Convert database row to Result object."""
        return Result(
            id=row['id'],
            query_id=row['query_id'],
            url=row['url'],
            title=row['title'],
            snippet=row['snippet'],
            source_engine=row['source_engine'],
            tags=row['tags'],
            first_seen_at=row['first_seen_at'],
            last_seen_at=row['last_seen_at'],
            is_duplicate=bool(row['is_duplicate'] if 'is_duplicate' in row.keys() else 0),
            duplicate_of_id=row['duplicate_of_id'] if 'duplicate_of_id' in row.keys() else None,
            similarity_score=row['similarity_score'] if 'similarity_score' in row.keys() else None
        )
