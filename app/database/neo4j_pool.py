"""Neo4j connection pool with context manager support."""

import logging
from contextlib import contextmanager
from typing import Any, Dict, List

from neo4j import GraphDatabase, Driver, Session
from app.models.config import settings

logger = logging.getLogger(__name__)


class Neo4jConnectionPool:
    """
    Managed Neo4j connection pool with proper lifecycle management.
    
    Provides connection pooling, automatic cleanup, and context managers
    for safe session handling in concurrent environments.
    """
    
    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        max_connections: int = 50,
        connection_timeout: int = 30
    ):
        """
        Initialize Neo4j connection pool.
        
        Args:
            uri: Neo4j URI (defaults to settings.neo4j_uri)
            user: Neo4j username (defaults to settings.neo4j_user)
            password: Neo4j password (defaults to settings.neo4j_password)
            max_connections: Maximum connections in pool
            connection_timeout: Connection acquisition timeout in seconds
        """
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password
        
        self.driver: Driver | None = None
        self._max_connections = max_connections
        self._connection_timeout = connection_timeout
        
        logger.info(f"Initializing Neo4j connection pool: {self.uri}")
    
    def connect(self) -> Driver:
        """
        Create or return existing driver with connection pool.
        
        Returns:
            Neo4j driver instance with connection pool configured
        """
        if self.driver is None:
            try:
                self.driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.user, self.password),
                    max_connection_pool_size=self._max_connections,
                    connection_acquisition_timeout=self._connection_timeout,
                    encrypted=False  # Set True for production with SSL
                )
                # Verify connectivity
                self.driver.verify_connectivity()
                logger.info("Neo4j connection pool established successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                raise
        
        return self.driver
    
    @contextmanager
    def get_session(self, database: str | None = None):
        """
        Context manager for Neo4j sessions with automatic cleanup.
        
        Args:
            database: Database name (optional, defaults to settings.neo4j_database)
        
        Yields:
            Neo4j session instance
        
        Example:
            with neo4j_pool.get_session() as session:
                result = session.run("MATCH (n) RETURN n LIMIT 10")
                for record in result:
                    print(record)
        """
        driver = self.connect()
        db = database or settings.neo4j_database
        session: Session = driver.session(database=db)
        
        try:
            yield session
        finally:
            session.close()
    
    def execute_query(
        self,
        query: str,
        parameters: Dict[str, Any] | None = None,
        database: str | None = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results as list of dictionaries.
        
        Args:
            query: Cypher query string
            parameters: Query parameters dictionary
            database: Database name (optional)
        
        Returns:
            List of result records as dictionaries
        
        Example:
            results = neo4j_pool.execute_query(
                "MATCH (s:Site) WHERE s.name = $name RETURN s",
                parameters={"name": "Thames Estuary"}
            )
        """
        with self.get_session(database=database) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def execute_write(
        self,
        query: str,
        parameters: Dict[str, Any] | None = None,
        database: str | None = None
    ) -> Dict[str, Any]:
        """
        Execute a write transaction and return summary.
        
        Args:
            query: Cypher write query (CREATE, UPDATE, DELETE)
            parameters: Query parameters
            database: Database name (optional)
        
        Returns:
            Transaction summary with counters
        """
        with self.get_session(database=database) as session:
            result = session.run(query, parameters or {})
            summary = result.consume()
            
            return {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
                "properties_set": summary.counters.properties_set,
            }
    
    def close(self):
        """Close all connections in the pool."""
        if self.driver:
            self.driver.close()
            self.driver = None
            logger.info("Neo4j connection pool closed")
    
    def __enter__(self):
        """Context manager entry - connect to Neo4j."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close connections."""
        self.close()


# Global connection pool instance
_neo4j_pool: Neo4jConnectionPool | None = None


def get_neo4j_pool() -> Neo4jConnectionPool:
    """
    Get or create global Neo4j connection pool.
    
    Returns:
        Singleton Neo4jConnectionPool instance
    """
    global _neo4j_pool
    
    if _neo4j_pool is None:
        _neo4j_pool = Neo4jConnectionPool()
        _neo4j_pool.connect()
    
    return _neo4j_pool


def close_neo4j_pool():
    """Close global Neo4j connection pool."""
    global _neo4j_pool
    
    if _neo4j_pool:
        _neo4j_pool.close()
        _neo4j_pool = None
