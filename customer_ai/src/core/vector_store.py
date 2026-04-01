"""
Vector Store Manager - Handles vector database operations
Supports ChromaDB (local/legacy) and pgvector (production) configurations
"""

import os
import logging
import re
import json
from typing import List, Dict, Any, Optional
# psycopg2 imports are loaded lazily in _init_pgvector() to avoid ImportError
# when using ChromaDB mode without PostgreSQL dependencies

logger = logging.getLogger(__name__)

# Embedding dimension for text-embedding-3-small
EMBEDDING_DIMENSION = 1536


class VectorStoreManager:
    """
    Manages vector database operations for RAG
    Supports ChromaDB (local/legacy) and pgvector (production)
    """
    
    def __init__(self, storage_mode: str = "pgvector", persist_directory: str = "./chroma_db"):
        """
        Initialize vector store
        
        Args:
            storage_mode: 'pgvector' for PostgreSQL with pgvector (default, recommended for production),
                         'local' for ChromaDB (development only)
            persist_directory: Directory to store ChromaDB database (only for local mode)
        """
        self.storage_mode = storage_mode
        self.persist_directory = persist_directory
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        
        # Log storage mode selection
        env_mode = os.getenv('VECTOR_STORAGE_MODE', 'not set')
        logger.info(f"Vector storage mode: {storage_mode} (from env: {env_mode})")
        
        if storage_mode == "local":
            # Warn if ChromaDB is used in production-like environments
            if os.getenv('ENVIRONMENT') in ('production', 'staging', 'prod', 'stage') or \
               os.getenv('FLASK_ENV') == 'production' or \
               os.getenv('PYTHON_ENV') == 'production':
                logger.warning(
                    "⚠️  ChromaDB (local mode) is being used in a production-like environment! "
                    "This is not recommended. Please set VECTOR_STORAGE_MODE=pgvector for production. "
                    "ChromaDB is intended for local development only."
                )
            else:
                logger.warning(
                    "ChromaDB (local mode) is being used. This is legacy and not recommended for production. "
                    "For production, use VECTOR_STORAGE_MODE=pgvector"
                )
            self._init_chroma()
        elif storage_mode == "pgvector":
            self._init_pgvector()
        elif storage_mode == "production":
            # Legacy: "production" now maps to pgvector
            logger.warning("storage_mode='production' is deprecated. Use 'pgvector' instead.")
            self._init_pgvector()
        else:
            raise ValueError(f"Invalid storage_mode: {storage_mode}. Use 'local' (ChromaDB) or 'pgvector' (PostgreSQL)")
    
    def _sanitize_table_name(self, business_id: str) -> str:
        """
        Sanitize business_id to create a valid PostgreSQL table name
        
        Args:
            business_id: Original business identifier
            
        Returns:
            Sanitized table name
        """
        # Replace any invalid characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', str(business_id))
        
        # Ensure it starts with a letter or underscore
        if not re.match(r'^[a-zA-Z_]', sanitized):
            sanitized = f"biz_{sanitized}"
        
        # Ensure it's not empty
        if not sanitized:
            sanitized = f"biz_{business_id}"
        
        # PostgreSQL identifier limit is 63 characters
        if len(sanitized) > 63:
            sanitized = sanitized[:63]
        
        return sanitized.lower()
    
    def _init_chroma(self):
        """Initialize ChromaDB vector database (legacy/local mode)."""
        try:
            # Disable ChromaDB telemetry to avoid posthog errors and log noise
            os.environ["ANONYMIZED_TELEMETRY"] = "False"
            # Import custom embeddings first
            from .custom_embeddings import OpenAIEmbeddings
            import sys
            # Windows workaround: fake onnxruntime so ChromaDB does not load it (DLL issues)
            if 'onnxruntime' not in sys.modules:
                class FakeOnnxRuntime:
                    pass
                sys.modules['onnxruntime'] = FakeOnnxRuntime()
            import chromadb
            from chromadb.config import Settings
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                    is_persistent=True
                )
            )
            
            # Use our custom OpenAI embeddings (avoids Windows DLL issues)
            if self.openai_api_key:
                self.embedding_function = OpenAIEmbeddings(
                    api_key=self.openai_api_key,
                    model="text-embedding-3-small"
                )
                logger.info("Using OpenAI embeddings (text-embedding-3-small)")
            else:
                raise ValueError("OpenAI API key is required for embeddings")
            
            logger.info("ChromaDB vector store initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            raise
    
    def _init_pgvector(self):
        """Initialize PostgreSQL with pgvector extension"""
        # Lazy import psycopg2 to avoid ImportError when using ChromaDB mode
        # without PostgreSQL dependencies
        try:
            import psycopg2
            from psycopg2.extras import execute_values, Json
            from psycopg2.pool import ThreadedConnectionPool
            from psycopg2 import sql as psql
            
            # Store as instance variables for use in other methods
            self.psycopg2 = psycopg2
            self.execute_values = execute_values
            self.Json = Json
            self.ThreadedConnectionPool = ThreadedConnectionPool
            self.psql = psql
        except ImportError as e:
            raise ImportError(
                "psycopg2 is required for pgvector mode. "
                "Install it with: pip install psycopg2-binary"
            ) from e
        
        try:
            # Get PostgreSQL connection parameters
            self.db_host = os.getenv('POSTGRES_HOST', 'localhost')
            db_port_str = os.getenv('POSTGRES_PORT', '5432')
            # Convert port to integer (ThreadedConnectionPool requires int, not string)
            try:
                self.db_port = int(db_port_str)
            except ValueError:
                raise ValueError(f"POSTGRES_PORT must be a valid integer, got: {db_port_str}")
            self.db_name = os.getenv('POSTGRES_DB', 'customer_ai')
            self.db_user = os.getenv('POSTGRES_USER', 'postgres')
            self.db_password = os.getenv('POSTGRES_PASSWORD', '')
            
            # Validate required parameters
            if not self.db_password:
                raise ValueError("POSTGRES_PASSWORD environment variable is required for pgvector mode")
            
            # Import custom embeddings for generating query embeddings
            from .custom_embeddings import OpenAIEmbeddings
            
            if self.openai_api_key:
                self.embedding_function = OpenAIEmbeddings(
                    api_key=self.openai_api_key,
                    model="text-embedding-3-small"
                )
                logger.info("Using OpenAI embeddings (text-embedding-3-small)")
            else:
                raise ValueError("OpenAI API key is required for embeddings")
            
            # Create connection pool
            self.connection_pool = self.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password
            )
            
            # Ensure pgvector extension is enabled
            self._ensure_pgvector_extension()
            
            logger.info(f"pgvector initialized successfully (PostgreSQL: {self.db_host}:{self.db_port}/{self.db_name})")
            
        except Exception as e:
            logger.error(f"Error initializing pgvector: {e}")
            raise
    
    def _ensure_pgvector_extension(self):
        """Ensure pgvector extension is installed and enabled"""
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                # Enable pgvector extension
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                conn.commit()
                logger.info("pgvector extension enabled")
        except Exception as e:
            logger.error(f"Error enabling pgvector extension: {e}")
            raise
        finally:
            self.connection_pool.putconn(conn)
    
    def _get_table_name(self, business_id: str) -> str:
        """Get table name for a business"""
        return f"vector_store_{self._sanitize_table_name(business_id)}"
    
    def _table_exists(self, business_id: str) -> bool:
        """
        Check if table exists for a business (without creating it)
        
        Args:
            business_id: Business identifier
            
        Returns:
            True if table exists, False otherwise
        """
        table_name = self._get_table_name(business_id)
        
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                # Check if table exists using information_schema
                # Use parameterized query to prevent SQL injection
                check_sql = """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    )
                """
                cur.execute(check_sql, (table_name,))
                exists = cur.fetchone()[0]
                return exists
        except Exception as e:
            logger.error(f"Error checking table existence for {business_id}: {e}")
            return False
        finally:
            self.connection_pool.putconn(conn)
    
    def _ensure_table_exists(self, business_id: str):
        """Create table for business if it doesn't exist"""
        table_name = self._get_table_name(business_id)
        table_identifier = self.psql.Identifier(table_name)
        embedding_idx_name = self.psql.Identifier(f"{table_name}_embedding_idx")
        metadata_idx_name = self.psql.Identifier(f"{table_name}_metadata_idx")
        
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                # Create table with vector column - use proper identifier escaping
                # NOTE: psycopg2's execute() only executes the first statement in a multi-statement string.
                # Therefore, we must execute each statement separately.
                create_table_sql = self.psql.SQL("""
                CREATE TABLE IF NOT EXISTS {table} (
                    id VARCHAR(255) PRIMARY KEY,
                    document TEXT NOT NULL,
                    embedding vector({dimension}) NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """).format(
                    table=table_identifier,
                    dimension=self.psql.SQL(str(EMBEDDING_DIMENSION))
                )
                cur.execute(create_table_sql)
                
                # Create index for vector similarity search using HNSW
                # HNSW is preferred over IVFFlat for small-to-medium datasets:
                #   - No training step required (IVFFlat needs rows before building)
                #   - Better recall on small tables (IVFFlat with lists=100 on <1000 rows is wasteful)
                #   - Slightly more memory but much better query quality
                # Operator class must match the query operator:
                #   <=> operator: Cosine distance, uses vector_cosine_ops
                create_embedding_idx_sql = self.psql.SQL("""
                CREATE INDEX IF NOT EXISTS {embedding_idx}
                ON {table}
                USING hnsw (embedding vector_cosine_ops)
                """).format(
                    table=table_identifier,
                    embedding_idx=embedding_idx_name
                )
                cur.execute(create_embedding_idx_sql)
                
                # Create index on metadata for filtering
                create_metadata_idx_sql = self.psql.SQL("""
                CREATE INDEX IF NOT EXISTS {metadata_idx} 
                ON {table} 
                USING gin (metadata)
                """).format(
                    table=table_identifier,
                    metadata_idx=metadata_idx_name
                )
                cur.execute(create_metadata_idx_sql)
                
                conn.commit()
                logger.debug(f"Table {table_name} and indexes ensured for business: {business_id}")
        except Exception as e:
            logger.error(f"Error creating table for {business_id}: {e}")
            conn.rollback()
            raise
        finally:
            self.connection_pool.putconn(conn)
    
    def create_collection(self, business_id: str, metadata: Optional[Dict] = None) -> Any:
        """
        Create a collection/table for a business
        
        Args:
            business_id: Unique identifier for the business
            metadata: Optional metadata for the collection (stored in table comment)
            
        Returns:
            Collection/table name
        """
        try:
            if self.storage_mode == "local":
                # ChromaDB mode
                collection_name = self._sanitize_collection_name(business_id)
                
                # Delete existing collection if it exists
                try:
                    self.client.delete_collection(name=collection_name)
                except Exception:
                    pass
                
                collection = self.client.create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function,
                    metadata=metadata or {"created_by": "customer_ai", "business_id": business_id}
                )
                
                logger.info(f"Created ChromaDB collection '{collection_name}' for business: {business_id}")
                return collection
            else:
                # pgvector mode
                self._ensure_table_exists(business_id)
                table_name = self._get_table_name(business_id)
                logger.info(f"Created pgvector table '{table_name}' for business: {business_id}")
                return table_name
                
        except Exception as e:
            logger.error(f"Error creating collection for {business_id}: {e}")
            raise
    
    def _sanitize_collection_name(self, business_id: str) -> str:
        """
        Sanitize business_id to create a valid ChromaDB collection name (legacy method)
        """
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', str(business_id))
        sanitized = re.sub(r'^[^a-zA-Z0-9]+', '', sanitized)
        sanitized = re.sub(r'[^a-zA-Z0-9]+$', '', sanitized)
        collection_name = f"biz_{sanitized}"
        if len(collection_name) > 63:
            collection_name = collection_name[:63]
            collection_name = re.sub(r'[^a-zA-Z0-9]+$', '', collection_name)
        if len(collection_name) < 3:
            collection_name = f"biz_{business_id}"[:63]
            collection_name = re.sub(r'[^a-zA-Z0-9]+$', '', collection_name)
        return collection_name
    
    def get_collection(self, business_id: str) -> Any:
        """
        Get existing collection/table for a business
        
        Args:
            business_id: Unique identifier for the business
            
        Returns:
            Collection object (ChromaDB) or table name (pgvector), or None if not found
        """
        try:
            if self.storage_mode == "local":
                # ChromaDB mode
                collection_name = self._sanitize_collection_name(business_id)
                collection = self.client.get_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function
                )
                return collection
            else:
                # pgvector mode - check if table exists (don't create it)
                if self._table_exists(business_id):
                    table_name = self._get_table_name(business_id)
                    return table_name
                else:
                    logger.debug(f"Table not found for {business_id}")
                    return None
                
        except Exception as e:
            logger.warning(f"Collection not found for {business_id}: {e}")
            return None
    
    def add_documents(
        self, 
        business_id: str, 
        documents: List[str], 
        metadatas: List[Dict[str, Any]], 
        ids: List[str]
    ) -> bool:
        """
        Add documents to a business's collection
        
        Args:
            business_id: Unique identifier for the business
            documents: List of text documents to add
            metadatas: List of metadata dicts for each document
            ids: List of unique IDs for each document
            
        Returns:
            Success status
        """
        try:
            if self.storage_mode == "local":
                # ChromaDB mode
                collection = self.get_collection(business_id)
                if not collection:
                    collection = self.create_collection(business_id)
                
                collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                
                logger.info(f"Added {len(documents)} documents to {business_id} (ChromaDB)")
                return True
            else:
                # pgvector mode
                self._ensure_table_exists(business_id)
                table_name = self._get_table_name(business_id)
                
                # Generate embeddings for all documents
                embeddings = self.embedding_function(documents)
                
                # Prepare data for bulk insert
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor() as cur:
                        # Prepare insert data
                        insert_data = []
                        for doc_id, doc_text, embedding, metadata in zip(ids, documents, embeddings, metadatas):
                            # Convert embedding to PostgreSQL vector format
                            embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                            insert_data.append((
                                doc_id,
                                doc_text,
                                embedding_str,
                                self.Json(metadata) if metadata else None
                            ))
                        
                        # Bulk insert - use proper identifier escaping for table name
                        table_identifier = self.psql.Identifier(table_name)
                        insert_sql = self.psql.SQL("""
                            INSERT INTO {table} (id, document, embedding, metadata)
                            VALUES %s
                            ON CONFLICT (id) 
                            DO UPDATE SET 
                                document = EXCLUDED.document,
                                embedding = EXCLUDED.embedding,
                                metadata = EXCLUDED.metadata,
                                updated_at = CURRENT_TIMESTAMP
                            """).format(table=table_identifier)
                        # Use custom template to cast embedding string to vector type
                        # Template format: (%s, %s, %s::vector, %s) for (id, document, embedding, metadata)
                        self.execute_values(
                            cur,
                            insert_sql,
                            insert_data,
                            template="(%s, %s, %s::vector, %s)"
                        )
                        conn.commit()
                        logger.info(f"Added {len(documents)} documents to {business_id} (pgvector)")
                        return True
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Error inserting documents: {e}")
                    raise
                finally:
                    self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error adding documents to {business_id}: {e}")
            return False
    
    def query(
        self, 
        business_id: str, 
        query_text: str, 
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Query documents from a business's collection
        
        Args:
            business_id: Unique identifier for the business
            query_text: Text to search for
            n_results: Number of results to return
            where: Optional metadata filter (ChromaDB format, converted to SQL WHERE for pgvector)
            
        Returns:
            Query results with documents, distances, and metadata
        """
        try:
            if self.storage_mode == "local":
                # ChromaDB mode
                collection = self.get_collection(business_id)
                if not collection:
                    logger.warning(f"No collection found for {business_id}")
                    return {"documents": [], "metadatas": [], "distances": []}
                
                results = collection.query(
                    query_texts=[query_text],
                    n_results=n_results,
                    where=where
                )
                
                return {
                    "documents": results['documents'][0] if results['documents'] else [],
                    "metadatas": results['metadatas'][0] if results['metadatas'] else [],
                    "distances": results['distances'][0] if results['distances'] else []
                }
            else:
                # pgvector mode
                table_name = self.get_collection(business_id)
                if not table_name:
                    logger.warning(f"No table found for {business_id}")
                    return {"documents": [], "metadatas": [], "distances": []}
                
                # Generate embedding for query text
                query_embedding = self.embedding_function([query_text])[0]
                
                # Build WHERE clause for metadata filtering with parameterized queries
                where_conditions = []
                where_params = []
                
                if where:
                    # Convert ChromaDB-style where to SQL with proper parameterization
                    for key, value in where.items():
                        # Both key and value are parameterized to prevent SQL injection
                        if isinstance(value, dict):
                            # Handle operators like $gt, $lt, etc.
                            for op, op_value in value.items():
                                if op == "$eq":
                                    where_conditions.append("metadata->>%s = %s")
                                    where_params.extend([key, op_value])
                                elif op == "$ne":
                                    where_conditions.append("metadata->>%s != %s")
                                    where_params.extend([key, op_value])
                                elif op == "$gt":
                                    where_conditions.append("(metadata->>%s)::numeric > %s")
                                    where_params.extend([key, op_value])
                                elif op == "$lt":
                                    where_conditions.append("(metadata->>%s)::numeric < %s")
                                    where_params.extend([key, op_value])
                                elif op == "$gte":
                                    where_conditions.append("(metadata->>%s)::numeric >= %s")
                                    where_params.extend([key, op_value])
                                elif op == "$lte":
                                    where_conditions.append("(metadata->>%s)::numeric <= %s")
                                    where_params.extend([key, op_value])
                                # Add more operators as needed
                        else:
                            # Simple equality check
                            where_conditions.append("metadata->>%s = %s")
                            where_params.extend([key, value])
                
                # Build WHERE clause string with parameterized placeholders
                where_clause = ""
                if where_conditions:
                    where_clause = " AND " + " AND ".join(where_conditions)
                
                # Build the query with proper parameterization
                # Use psycopg2.sql.Identifier for table name to prevent injection
                table_identifier = self.psql.Identifier(table_name)
                
                # Query with cosine distance - use parameterized query
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor() as cur:
                        # Use parameterized query for embedding vector
                        # Convert embedding to string format for PostgreSQL vector type
                        # PostgreSQL vector type expects string format: '[1,2,3]'::vector
                        # This is parameterized, not interpolated, so it's safe
                        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
                        
                        # Build query with proper escaping
                        # Return distance directly (not similarity) to avoid double negation
                        # Table name is sanitized by _sanitize_table_name() which ensures it's safe
                        # All values (embedding, where params) are parameterized with %s
                        # IMPORTANT: <=> operator is cosine distance, matches vector_cosine_ops index
                        #            <-> operator is L2/Euclidean distance, would use vector_l2_ops
                        # NOTE: Cannot wrap WHERE clause with %s placeholders in psql.SQL() because
                        #       psql.SQL() treats %s as literal text, not parameter markers.
                        #       Instead, build query as string with table identifier properly escaped.
                        #       The table identifier is safely escaped via psql.Identifier().
                        # Convert table identifier to properly escaped string using the cursor
                        # This safely escapes the table name to prevent SQL injection
                        escaped_table = self.psql.SQL("{}").format(table_identifier).as_string(cur)
                        
                        # Build query string with properly escaped table name
                        # WHERE clause already contains %s placeholders for parameters
                        query_str = (
                            f"SELECT id, document, metadata, embedding <=> %s::vector as distance "
                            f"FROM {escaped_table} "
                            f"WHERE 1=1{where_clause} "
                            f"ORDER BY embedding <=> %s::vector LIMIT %s"
                        )
                        
                        # Execute with all parameters
                        # embedding_str appears twice (once for distance calc, once for ordering)
                        execute_params = [embedding_str] + where_params + [embedding_str, n_results]
                        cur.execute(query_str, execute_params)
                        rows = cur.fetchall()
                        
                        documents = []
                        metadatas = []
                        distances = []
                        
                        for row in rows:
                            documents.append(row[1])  # document
                            metadatas.append(row[2] if row[2] else {})  # metadata
                            distances.append(float(row[3]))  # distance (already distance, not similarity)
                        
                        return {
                            "documents": documents,
                            "metadatas": metadatas,
                            "distances": distances
                        }
                finally:
                    self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error querying {business_id}: {e}")
            return {"documents": [], "metadatas": [], "distances": []}
    
    def update_document(
        self, 
        business_id: str, 
        doc_id: str, 
        document: str, 
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update a specific document in the collection
        
        Args:
            business_id: Unique identifier for the business
            doc_id: Document ID to update
            document: New document text
            metadata: New metadata
            
        Returns:
            Success status
        """
        try:
            if self.storage_mode == "local":
                # ChromaDB mode
                collection = self.get_collection(business_id)
                if not collection:
                    logger.warning(f"No collection found for {business_id}")
                    return False
                
                collection.update(
                    ids=[doc_id],
                    documents=[document],
                    metadatas=[metadata]
                )
                
                logger.info(f"Updated document {doc_id} in {business_id} (ChromaDB)")
                return True
            else:
                # pgvector mode
                table_name = self.get_collection(business_id)
                if not table_name:
                    logger.warning(f"No table found for {business_id}")
                    return False
                
                # Generate new embedding for updated document
                embedding = self.embedding_function([document])[0]
                embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor() as cur:
                        # Use proper identifier escaping for table name
                        table_identifier = self.psql.Identifier(table_name)
                        update_sql = self.psql.SQL("""
                            UPDATE {table}
                            SET document = %s,
                                embedding = %s::vector,
                                metadata = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                            """).format(table=table_identifier)
                        cur.execute(
                            update_sql,
                            (document, embedding_str, self.Json(metadata), doc_id)
                        )
                        conn.commit()
                        logger.info(f"Updated document {doc_id} in {business_id} (pgvector)")
                        return cur.rowcount > 0
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Error updating document: {e}")
                    return False
                finally:
                    self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error updating document in {business_id}: {e}")
            return False
    
    def delete_documents(self, business_id: str, doc_ids: List[str]) -> bool:
        """
        Delete specific documents from collection
        
        Args:
            business_id: Unique identifier for the business
            doc_ids: List of document IDs to delete
            
        Returns:
            Success status
        """
        try:
            if self.storage_mode == "local":
                # ChromaDB mode
                collection = self.get_collection(business_id)
                if not collection:
                    logger.warning(f"No collection found for {business_id}")
                    return False
                
                collection.delete(ids=doc_ids)
                
                logger.info(f"Deleted {len(doc_ids)} documents from {business_id} (ChromaDB)")
                return True
            else:
                # pgvector mode
                table_name = self.get_collection(business_id)
                if not table_name:
                    logger.warning(f"No table found for {business_id}")
                    return False
                
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor() as cur:
                        # Use proper identifier escaping for table name
                        table_identifier = self.psql.Identifier(table_name)
                        delete_sql = self.psql.SQL("DELETE FROM {table} WHERE id = ANY(%s)").format(
                            table=table_identifier
                        )
                        cur.execute(delete_sql, (doc_ids,))
                        conn.commit()
                        logger.info(f"Deleted {len(doc_ids)} documents from {business_id} (pgvector)")
                        return cur.rowcount > 0
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Error deleting documents: {e}")
                    return False
                finally:
                    self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error deleting documents from {business_id}: {e}")
            return False
    
    def delete_collection(self, business_id: str) -> bool:
        """
        Delete entire collection/table for a business
        
        Args:
            business_id: Unique identifier for the business
            
        Returns:
            Success status
        """
        try:
            if self.storage_mode == "local":
                # ChromaDB mode
                collection_name = self._sanitize_collection_name(business_id)
                self.client.delete_collection(name=collection_name)
                logger.info(f"Deleted ChromaDB collection '{collection_name}' for business: {business_id}")
                return True
            else:
                # pgvector mode
                table_name = self._get_table_name(business_id)
                table_identifier = self.psql.Identifier(table_name)
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor() as cur:
                        # Use proper identifier escaping for table name
                        drop_sql = self.psql.SQL("DROP TABLE IF EXISTS {table} CASCADE").format(
                            table=table_identifier
                        )
                        cur.execute(drop_sql)
                        conn.commit()
                        logger.info(f"Deleted pgvector table '{table_name}' for business: {business_id}")
                        return True
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Error deleting table: {e}")
                    return False
                finally:
                    self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error deleting collection for {business_id}: {e}")
            return False
    
    def get_collection_stats(self, business_id: str) -> Dict[str, Any]:
        """
        Get statistics about a collection
        
        Args:
            business_id: Unique identifier for the business
            
        Returns:
            Collection statistics
        """
        try:
            if self.storage_mode == "local":
                # ChromaDB mode
                collection = self.get_collection(business_id)
                if not collection:
                    return {"exists": False, "count": 0}
                
                count = collection.count()
                
                return {
                    "exists": True,
                    "count": count,
                    "name": business_id
                }
            else:
                # pgvector mode
                table_name = self.get_collection(business_id)
                if not table_name:
                    return {"exists": False, "count": 0}
                
                conn = self.connection_pool.getconn()
                try:
                    with conn.cursor() as cur:
                        # Use proper identifier escaping for table name
                        table_identifier = self.psql.Identifier(table_name)
                        count_sql = self.psql.SQL("SELECT COUNT(*) FROM {table}").format(
                            table=table_identifier
                        )
                        cur.execute(count_sql)
                        count = cur.fetchone()[0]
                        return {
                            "exists": True,
                            "count": count,
                            "name": table_name
                        }
                finally:
                    self.connection_pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error getting stats for {business_id}: {e}")
            return {"exists": False, "count": 0, "error": str(e)}


_vector_store_instance: Optional[VectorStoreManager] = None


def get_vector_store(storage_mode: Optional[str] = None) -> VectorStoreManager:
    """
    Factory function to get vector store singleton.

    Args:
        storage_mode: 'pgvector' for PostgreSQL with pgvector (default, recommended for production),
                     'local' for ChromaDB (development only).
                     If None, reads from VECTOR_STORAGE_MODE environment variable (defaults to 'pgvector')

    Returns:
        VectorStoreManager instance (singleton)
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        if storage_mode is None:
            storage_mode = os.getenv('VECTOR_STORAGE_MODE', 'pgvector')
        _vector_store_instance = VectorStoreManager(storage_mode=storage_mode)
    return _vector_store_instance
