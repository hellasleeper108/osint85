"""Database schema and models for osint85."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class Target:
    """Represents a target for OSINT reconnaissance."""
    id: Optional[int] = None
    name: str = ""
    primary_domain: str = ""
    notes: str = ""
    scope: str = ""
    created_at: Optional[str] = None


@dataclass
class Query:
    """Represents a generated dork query."""
    id: Optional[int] = None
    target_id: int = 0
    category: str = ""
    risk_level: str = "medium"
    description: str = ""
    query: str = ""
    enabled: bool = True
    created_at: Optional[str] = None


@dataclass
class Result:
    """Represents a search result from a query."""
    id: Optional[int] = None
    query_id: int = 0
    url: str = ""
    title: str = ""
    snippet: str = ""
    source_engine: str = ""
    tags: str = ""  # Comma-separated
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None
    # Deduplication fields
    is_duplicate: bool = False
    duplicate_of_id: Optional[int] = None
    similarity_score: Optional[float] = None


class Database:
    """SQLite database manager for osint85 projects."""

    SCHEMA_VERSION = 3  # Updated for performance optimizations

    def __init__(self, db_path: str = ".osint85/project.db"):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._init_schema()

    def _connect(self):
        """Establish database connection."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

    def _init_schema(self):
        """Initialize database schema if not exists."""
        if not self.conn:
            raise RuntimeError("Database connection not established")

        cursor = self.conn.cursor()

        # Targets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                primary_domain TEXT NOT NULL,
                notes TEXT DEFAULT '',
                scope TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Queries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                risk_level TEXT DEFAULT 'medium',
                description TEXT DEFAULT '',
                query TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (target_id) REFERENCES targets (id) ON DELETE CASCADE
            )
        """)

        # Results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                title TEXT DEFAULT '',
                snippet TEXT DEFAULT '',
                source_engine TEXT DEFAULT '',
                tags TEXT DEFAULT '',
                first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (query_id) REFERENCES queries (id) ON DELETE CASCADE
            )
        """)

        # Create indexes for performance
        # Basic foreign key indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_queries_target ON queries(target_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_query ON results(query_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_url ON results(url)")

        self.conn.commit()

        # Run migrations (additional indexes added in v3)
        self._migrate_schema()

    def _migrate_schema(self):
        """Run database migrations for schema updates."""
        if not self.conn:
            raise RuntimeError("Database connection not established")

        cursor = self.conn.cursor()

        # Check if deduplication columns exist (added in schema v2)
        cursor.execute("PRAGMA table_info(results)")
        columns = [row[1] for row in cursor.fetchall()]

        if "is_duplicate" not in columns:
            # Add deduplication columns
            cursor.execute("""
                ALTER TABLE results
                ADD COLUMN is_duplicate BOOLEAN DEFAULT 0
            """)

        if "duplicate_of_id" not in columns:
            cursor.execute("""
                ALTER TABLE results
                ADD COLUMN duplicate_of_id INTEGER
            """)

        if "similarity_score" not in columns:
            cursor.execute("""
                ALTER TABLE results
                ADD COLUMN similarity_score REAL
            """)

        # Create index for duplicate lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_duplicate
            ON results(is_duplicate, duplicate_of_id)
        """)

        # Performance indexes (added in schema v3)
        # Index for category-based query filtering
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_queries_category
            ON queries(category)
        """)

        # Compound index for common query patterns
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_queries_target_category
            ON queries(target_id, category)
        """)

        # Index for enabled queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_queries_enabled
            ON queries(enabled)
        """)

        # Index for result timestamps (for sorting)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_first_seen
            ON results(first_seen_at DESC)
        """)

        # Index for filtering non-duplicates
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_not_duplicate
            ON results(is_duplicate) WHERE is_duplicate = 0
        """)

        self.conn.commit()

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    # Target operations

    def create_target(self, name: str, primary_domain: str, notes: str = "", scope: str = "") -> Target:
        """Create a new target.

        Args:
            name: Target name
            primary_domain: Primary domain to investigate
            notes: Additional notes
            scope: Authorized scope definition

        Returns:
            Created Target object
        """
        if not self.conn:
            raise RuntimeError("Database connection not established")

        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO targets (name, primary_domain, notes, scope) VALUES (?, ?, ?, ?)",
            (name, primary_domain, notes, scope)
        )
        self.conn.commit()

        target_id = cursor.lastrowid
        return self.get_target(target_id)

    def get_target(self, target_id: int) -> Target:
        """Get target by ID.

        Args:
            target_id: Target ID

        Returns:
            Target object

        Raises:
            ValueError: If target not found
        """
        if not self.conn:
            raise RuntimeError("Database connection not established")

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM targets WHERE id = ?", (target_id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Target {target_id} not found")

        return Target(
            id=row['id'],
            name=row['name'],
            primary_domain=row['primary_domain'],
            notes=row['notes'],
            scope=row['scope'],
            created_at=row['created_at']
        )

    def list_targets(self) -> List[Target]:
        """List all targets.

        Returns:
            List of Target objects
        """
        if not self.conn:
            raise RuntimeError("Database connection not established")

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM targets ORDER BY created_at DESC")
        rows = cursor.fetchall()

        return [
            Target(
                id=row['id'],
                name=row['name'],
                primary_domain=row['primary_domain'],
                notes=row['notes'],
                scope=row['scope'],
                created_at=row['created_at']
            )
            for row in rows
        ]

    # Query operations

    def save_queries(self, target_id: int, queries: List[Dict[str, Any]]) -> List[Query]:
        """Save multiple queries for a target.

        Args:
            target_id: Target ID
            queries: List of query dicts with keys: category, risk_level, description, query

        Returns:
            List of created Query objects
        """
        if not self.conn:
            raise RuntimeError("Database connection not established")

        cursor = self.conn.cursor()
        created_queries = []

        for q in queries:
            cursor.execute(
                """INSERT INTO queries (target_id, category, risk_level, description, query)
                   VALUES (?, ?, ?, ?, ?)""",
                (target_id, q['category'], q['risk_level'], q['description'], q['query'])
            )
            query_id = cursor.lastrowid
            created_queries.append(self.get_query(query_id))

        self.conn.commit()
        return created_queries

    def get_query(self, query_id: int) -> Query:
        """Get query by ID.

        Args:
            query_id: Query ID

        Returns:
            Query object

        Raises:
            ValueError: If query not found
        """
        if not self.conn:
            raise RuntimeError("Database connection not established")

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM queries WHERE id = ?", (query_id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Query {query_id} not found")

        return Query(
            id=row['id'],
            target_id=row['target_id'],
            category=row['category'],
            risk_level=row['risk_level'],
            description=row['description'],
            query=row['query'],
            enabled=bool(row['enabled']),
            created_at=row['created_at']
        )

    def get_enabled_queries(self, target_id: int) -> List[Query]:
        """Get all enabled queries for a target.

        Args:
            target_id: Target ID

        Returns:
            List of enabled Query objects
        """
        if not self.conn:
            raise RuntimeError("Database connection not established")

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM queries WHERE target_id = ? AND enabled = 1 ORDER BY created_at",
            (target_id,)
        )
        rows = cursor.fetchall()

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

    def list_queries(self, target_id: int) -> List[Query]:
        """List all queries for a target.

        Args:
            target_id: Target ID

        Returns:
            List of Query objects
        """
        if not self.conn:
            raise RuntimeError("Database connection not established")

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM queries WHERE target_id = ? ORDER BY created_at",
            (target_id,)
        )
        rows = cursor.fetchall()

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

    def toggle_query(self, query_id: int, enabled: bool):
        """Enable or disable a query.

        Args:
            query_id: Query ID
            enabled: True to enable, False to disable
        """
        if not self.conn:
            raise RuntimeError("Database connection not established")

        cursor = self.conn.cursor()
        cursor.execute("UPDATE queries SET enabled = ? WHERE id = ?", (int(enabled), query_id))
        self.conn.commit()

    # Result operations

    def save_result(self, query_id: int, url: str, title: str = "", snippet: str = "",
                   source_engine: str = "", tags: str = "") -> Result:
        """Save a search result, or update if URL exists.

        Args:
            query_id: Query ID
            url: Result URL
            title: Page title
            snippet: Search snippet
            source_engine: Search engine name
            tags: Comma-separated tags

        Returns:
            Created or updated Result object
        """
        if not self.conn:
            raise RuntimeError("Database connection not established")

        cursor = self.conn.cursor()

        # Check if result already exists
        cursor.execute("SELECT id FROM results WHERE query_id = ? AND url = ?", (query_id, url))
        existing = cursor.fetchone()

        if existing:
            # Update last_seen_at
            cursor.execute(
                "UPDATE results SET last_seen_at = CURRENT_TIMESTAMP WHERE id = ?",
                (existing['id'],)
            )
            self.conn.commit()
            return self.get_result(existing['id'])
        else:
            # Insert new result
            cursor.execute(
                """INSERT INTO results (query_id, url, title, snippet, source_engine, tags)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (query_id, url, title, snippet, source_engine, tags)
            )
            self.conn.commit()
            return self.get_result(cursor.lastrowid)

    def get_result(self, result_id: int) -> Result:
        """Get result by ID.

        Args:
            result_id: Result ID

        Returns:
            Result object

        Raises:
            ValueError: If result not found
        """
        if not self.conn:
            raise RuntimeError("Database connection not established")

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM results WHERE id = ?", (result_id,))
        row = cursor.fetchone()

        if not row:
            raise ValueError(f"Result {result_id} not found")

        return Result(
            id=row['id'],
            query_id=row['query_id'],
            url=row['url'],
            title=row['title'],
            snippet=row['snippet'],
            source_engine=row['source_engine'],
            tags=row['tags'],
            first_seen_at=row['first_seen_at'],
            last_seen_at=row['last_seen_at']
        )

    def get_results_by_query(self, query_id: int) -> List[Result]:
        """Get all results for a query.

        Args:
            query_id: Query ID

        Returns:
            List of Result objects
        """
        if not self.conn:
            raise RuntimeError("Database connection not established")

        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM results WHERE query_id = ? ORDER BY first_seen_at", (query_id,))
        rows = cursor.fetchall()

        return [
            Result(
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
            for row in rows
        ]

    def get_all_results(self, target_id: int, category: Optional[str] = None) -> List[Result]:
        """Get all results for a target.

        Args:
            target_id: Target ID
            category: Optional category to filter by

        Returns:
            List of Result objects
        """
        if not self.conn:
            raise RuntimeError("Database connection not established")

        cursor = self.conn.cursor()
        
        query = """
            SELECT r.* FROM results r
            JOIN queries q ON r.query_id = q.id
            WHERE q.target_id = ?
        """
        params = [target_id]
        
        if category:
            query += " AND q.category = ?"
            params.append(category)
            
        query += " ORDER BY r.first_seen_at"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()

        return [
            Result(
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
            for row in rows
        ]

    def mark_as_duplicate(self, result_id: int, duplicate_of_id: int,
                         similarity_score: float = 100.0):
        """Mark a result as a duplicate.

        Args:
            result_id: ID of the duplicate result
            duplicate_of_id: ID of the primary result
            similarity_score: Similarity score (0-100)
        """
        if not self.conn:
            raise RuntimeError("Database connection not established")

        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE results
            SET is_duplicate = 1,
                duplicate_of_id = ?,
                similarity_score = ?
            WHERE id = ?
        """, (duplicate_of_id, similarity_score, result_id))

        self.conn.commit()

    def delete_result(self, result_id: int):
        """Delete a result from the database.

        Args:
            result_id: Result ID to delete
        """
        if not self.conn:
            raise RuntimeError("Database connection not established")

        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM results WHERE id = ?", (result_id,))
        self.conn.commit()
