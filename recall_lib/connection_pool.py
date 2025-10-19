#!/usr/bin/env python3
"""
Connection Pool - SQLite connection pooling for better performance
"""
import sqlite3
import threading
from queue import Queue, Empty
from typing import Optional
from contextlib import contextmanager
from .logger import get_logger

logger = get_logger(__name__)


class ConnectionPool:
    """
    SQLite connection pool for reusing database connections

    Note: SQLite has some limitations with threading:
    - check_same_thread must be False for thread-safe operation
    - WAL mode is recommended for concurrent access
    """

    def __init__(self, db_path: str, pool_size: int = 5, timeout: float = 30.0):
        """
        Initialize connection pool

        Args:
            db_path: Path to SQLite database
            pool_size: Maximum number of connections in pool
            timeout: Timeout for acquiring connection (seconds)
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self._pool: Queue = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._initialized = False

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimal settings"""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,  # Allow connections across threads
            timeout=self.timeout
        )

        # Enable row factory for dict-like access
        conn.row_factory = sqlite3.Row

        # Enable WAL mode for better concurrent access
        conn.execute('PRAGMA journal_mode=WAL')

        # Set busy timeout
        conn.execute(f'PRAGMA busy_timeout={int(self.timeout * 1000)}')

        # Enable foreign keys
        conn.execute('PRAGMA foreign_keys=ON')

        return conn

    def _initialize_pool(self):
        """Initialize the connection pool with connections"""
        with self._lock:
            if self._initialized:
                return

            for _ in range(self.pool_size):
                try:
                    conn = self._create_connection()
                    self._pool.put(conn, block=False)
                except Exception as e:
                    logger.error(f"Failed to create connection: {e}")

            self._initialized = True
            logger.debug(f"Connection pool initialized with {self.pool_size} connections")

    def get_connection(self, timeout: Optional[float] = None) -> sqlite3.Connection:
        """
        Get a connection from the pool

        Args:
            timeout: Override default timeout

        Returns:
            Database connection

        Raises:
            Empty: If no connection available within timeout
        """
        if not self._initialized:
            self._initialize_pool()

        timeout = timeout or self.timeout

        try:
            conn = self._pool.get(timeout=timeout)

            # Test if connection is still valid
            try:
                conn.execute('SELECT 1')
                return conn
            except sqlite3.Error:
                # Connection is stale, create a new one
                logger.warning("Stale connection detected, creating new one")
                conn.close()
                return self._create_connection()

        except Empty:
            # Pool is empty, create a new connection (overflow)
            logger.warning("Connection pool exhausted, creating overflow connection")
            return self._create_connection()

    def return_connection(self, conn: sqlite3.Connection):
        """
        Return a connection to the pool

        Args:
            conn: Connection to return
        """
        try:
            # Rollback any pending transactions
            conn.rollback()

            # Try to return to pool
            self._pool.put(conn, block=False)
        except Exception:
            # Pool is full or error occurred, close the connection
            conn.close()

    @contextmanager
    def connection(self):
        """
        Context manager for getting and returning connections

        Usage:
            with pool.connection() as conn:
                cursor = conn.execute('SELECT * FROM table')
        """
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()  # Auto-commit on success
        except Exception:
            conn.rollback()  # Auto-rollback on error
            raise
        finally:
            self.return_connection(conn)

    def close_all(self):
        """Close all connections in the pool"""
        while not self._pool.empty():
            try:
                conn = self._pool.get(block=False)
                conn.close()
            except Empty:
                break

        logger.debug("All connections closed")

    def __del__(self):
        """Cleanup connections when pool is destroyed"""
        try:
            self.close_all()
        except Exception:
            pass


# Global pool instance (lazy initialization)
_global_pool: Optional[ConnectionPool] = None
_pool_lock = threading.Lock()


def get_global_pool(db_path: str, pool_size: int = 5) -> ConnectionPool:
    """
    Get or create the global connection pool

    Args:
        db_path: Database path
        pool_size: Pool size

    Returns:
        Global ConnectionPool instance
    """
    global _global_pool

    with _pool_lock:
        if _global_pool is None or _global_pool.db_path != db_path:
            if _global_pool is not None:
                _global_pool.close_all()

            _global_pool = ConnectionPool(db_path, pool_size)

    return _global_pool
