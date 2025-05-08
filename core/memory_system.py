"""
Friday AI - Memory System
Three-tier memory architecture for Friday's knowledge management:
- Short-term: Redis-based cache for immediate context (with fallback to in-memory dict)
- Mid-term: SQLite for session summaries and recent interactions (with thread safety)
- Long-term: Chroma vector database for semantic search (with updated client configuration)
"""

import os
import json
import uuid
import threading
import redis
import sqlite3
import datetime
from typing import Dict, List, Any, Optional, Tuple
import logging
import chromadb
from chromadb.config import Settings

logger = logging.getLogger("memory_system")

class ThreadSafeSQLite:
    """Thread-safe wrapper for SQLite connections."""
    
    def __init__(self, db_path: str):
        """Initialize the thread-safe SQLite wrapper.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.local = threading.local()
        
    def get_connection(self) -> sqlite3.Connection:
        """Get a thread-local SQLite connection.
        
        Returns:
            SQLite connection for the current thread
        """
        if not hasattr(self.local, 'connection'):
            self.local.connection = sqlite3.connect(self.db_path)
        return self.local.connection
        
    def close_all(self):
        """Close all connections (if possible)."""
        # This method is limited because we can't access 
        # connections from other threads
        if hasattr(self.local, 'connection'):
            self.local.connection.close()
            delattr(self.local, 'connection')

class MemorySystem:
    def __init__(self, config_path: str = None):
        """Initialize the three-tier memory system.
        
        Args:
            config_path: Path to memory configuration file
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize short-term memory (Redis with in-memory fallback)
        self.short_term = self._init_short_term_memory()
        self._short_term_dict = {}  # In-memory fallback always available
        
        # Initialize mid-term memory (Thread-safe SQLite)
        self.mid_term_manager = self._init_mid_term_memory()
        
        # Initialize long-term memory (Chroma)
        self.long_term, self.knowledge_collection, self.interaction_collection, self.persona_collection = self._init_long_term_memory()
        
        logger.info("Memory system initialized successfully")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load memory system configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        default_config = {
            "short_term": {
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "ttl": 3600  # Time-to-live in seconds (1 hour)
            },
            "mid_term": {
                "db_path": "data/memory/mid_term.db",
                "retention_days": 30
            },
            "long_term": {
                "db_path": "data/memory/long_term",
                "similarity_threshold": 0.75
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                
                # Merge with default config to ensure all fields exist
                for section in default_config:
                    if section in loaded_config:
                        default_config[section].update(loaded_config[section])
            except Exception as e:
                logger.error(f"Error loading memory config: {e}. Using defaults.")
        
        # Ensure data directories exist
        os.makedirs(os.path.dirname(default_config["mid_term"]["db_path"]), exist_ok=True)
        os.makedirs(default_config["long_term"]["db_path"], exist_ok=True)
            
        return default_config
    
    def _init_short_term_memory(self) -> Optional[redis.Redis]:
        """Initialize the Redis connection for short-term memory.
        
        Returns:
            Redis connection or None if not available
        """
        try:
            config = self.config["short_term"]
            redis_client = redis.Redis(
                host=config["host"],
                port=config["port"],
                db=config["db"],
                decode_responses=True,
                socket_connect_timeout=2,  # Add timeout to avoid long waits
                socket_timeout=2
            )
            # Test connection
            redis_client.ping()
            logger.info("Redis connected successfully for short-term memory")
            return redis_client
        except Exception as e:
            logger.warning(f"Could not connect to Redis for short-term memory: {e}")
            logger.info("Short-term memory will be simulated with an in-memory dictionary")
            return None
    
    def _init_mid_term_memory(self) -> ThreadSafeSQLite:
        """Initialize the SQLite database for mid-term memory.
        
        Returns:
            Thread-safe SQLite manager
        """
        try:
            db_path = self.config["mid_term"]["db_path"]
            # Create thread-safe SQLite manager
            sqlite_manager = ThreadSafeSQLite(db_path)
            
            # Initialize tables using the manager
            conn = sqlite_manager.get_connection()
            self._create_mid_term_tables(conn)
            
            logger.info("Mid-term memory initialized with thread-safe SQLite")
            return sqlite_manager
        except Exception as e:
            logger.error(f"Error initializing mid-term memory: {e}")
            raise
    
    def _create_mid_term_tables(self, conn: sqlite3.Connection) -> None:
        """Create necessary tables for mid-term memory if they don't exist.
        
        Args:
            conn: SQLite connection
        """
        cursor = conn.cursor()
        
        # Interactions table for storing conversations
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            id TEXT PRIMARY KEY,
            timestamp DATETIME NOT NULL,
            user_input TEXT NOT NULL,
            friday_response TEXT NOT NULL,
            context TEXT,
            metadata TEXT
        )
        ''')
        
        # Session summaries table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_summaries (
            id TEXT PRIMARY KEY,
            start_time DATETIME NOT NULL,
            end_time DATETIME,
            summary TEXT,
            metadata TEXT
        )
        ''')
        
        # User preferences table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            last_updated DATETIME NOT NULL
        )
        ''')
        
        # Commit changes
        conn.commit()
        logger.debug("Mid-term tables created/verified")
    
    def _init_long_term_memory(self) -> Tuple[Any, Any, Any, Any]:
        """Initialize the Chroma vector database for long-term memory.
        
        Returns:
            Tuple of (chroma_client, knowledge_collection, interaction_collection, persona_collection)
        """
        try:
            db_path = self.config["long_term"]["db_path"]
            
            # Initialize Chroma client with persistent storage - updated for newer version
            client = chromadb.PersistentClient(path=db_path)
            
            # Create collections if they don't exist
            knowledge_collection = client.get_or_create_collection("knowledge")
            interaction_collection = client.get_or_create_collection("interactions")
            persona_collection = client.get_or_create_collection("persona")
            
            logger.info("Long-term memory initialized with Chroma")
            return client, knowledge_collection, interaction_collection, persona_collection
        except Exception as e:
            logger.warning(f"Could not initialize Chroma for long-term memory: {e}")
            logger.warning("Long-term memory will have limited functionality")
            return None, None, None, None
    
    # Short-term memory operations
    
    async def store_short_term(self, key: str, value: Any, ttl: int = None) -> bool:
        """Store a value in short-term memory.
        
        Args:
            key: Unique identifier for the data
            value: Value to store (will be JSON serialized)
            ttl: Time-to-live in seconds, defaults to config value
            
        Returns:
            Success flag
        """
        if ttl is None:
            ttl = self.config["short_term"]["ttl"]
            
        try:
            # Serialize value to JSON
            serialized_value = json.dumps(value)
            
            # Always store in in-memory dict as a fallback
            self._short_term_dict[key] = serialized_value
            
            # If Redis is available, store there too
            if self.short_term:
                try:
                    self.short_term.set(key, serialized_value, ex=ttl)
                except Exception as e:
                    logger.warning(f"Redis store failed, using in-memory fallback: {e}")
                
            return True
        except Exception as e:
            logger.error(f"Error storing in short-term memory: {e}")
            return False
    
    async def get_short_term(self, key: str) -> Optional[Any]:
        """Retrieve a value from short-term memory.
        
        Args:
            key: Unique identifier for the data
            
        Returns:
            Retrieved value or None if not found
        """
        try:
            value = None
            
            # Try Redis first if available
            if self.short_term:
                try:
                    value = self.short_term.get(key)
                except Exception as e:
                    logger.warning(f"Redis retrieval failed, falling back to in-memory: {e}")
            
            # Fall back to in-memory if Redis failed or returned None
            if value is None:
                value = self._short_term_dict.get(key)
                
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error retrieving from short-term memory: {e}")
            return None
    
    # Mid-term memory operations
    
    async def store_interaction(self, data):
        """Store an interaction in mid-term memory.
        
        Args can be:
            - dict with user_input and friday_response keys
            - dict with role and content keys (for compatibility)
            - individual parameters
            
        Returns:
            Interaction ID
        """
        try:
            # Handle different input formats
            if isinstance(data, dict):
                if "role" in data and "content" in data:
                    # Handle role/content format
                    if data["role"] == "user":
                        user_input = data["content"]
                        friday_response = None
                    elif data["role"] == "friday":
                        user_input = None
                        friday_response = data["content"]
                    else:
                        user_input = str(data)
                        friday_response = None
                    
                    context = data.get("context")
                    metadata = {"timestamp": data.get("timestamp")}
                elif "user_input" in data:
                    # Handle explicit format
                    user_input = data["user_input"]
                    friday_response = data.get("friday_response")
                    context = data.get("context")
                    metadata = data.get("metadata")
                else:
                    # Fallback
                    user_input = str(data)
                    friday_response = None
                    context = None
                    metadata = None
            else:
                # Direct string input
                user_input = str(data)
                friday_response = None
                context = None
                metadata = None
            
            # If we don't have user_input set, use empty string
            if user_input is None:
                user_input = ""
                
            # If we don't have friday_response set, use empty string  
            if friday_response is None:
                friday_response = ""
                
            interaction_id = str(uuid.uuid4())
            timestamp = datetime.datetime.now().isoformat()
            
            # Store in SQLite with thread safety
            try:
                conn = self.mid_term_manager.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO interactions VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        interaction_id,
                        timestamp,
                        str(user_input),
                        str(friday_response),
                        json.dumps(context) if context else None,
                        json.dumps(metadata) if metadata else None
                    )
                )
                conn.commit()
                logger.debug(f"Interaction stored in mid-term memory: {interaction_id}")
            except Exception as e:
                logger.error(f"Error storing interaction in SQLite: {e}")
                # Continue to try long-term memory
            
            # Also store in long-term if available, for semantic search
            if self.long_term and self.interaction_collection:
                try:
                    # Combine user input and response for context
                    full_text = f"User: {user_input}"
                    if friday_response:
                        full_text += f"\nFriday: {friday_response}"
                    
                    # Store in Chroma
                    metadata_dict = {
                        "timestamp": timestamp,
                        "type": "interaction"
                    }
                    if metadata:
                        if isinstance(metadata, dict):
                            metadata_dict.update(metadata)
                        else:
                            metadata_dict["additional"] = str(metadata)
                            
                    self.interaction_collection.add(
                        ids=[interaction_id],
                        documents=[full_text],
                        metadatas=[metadata_dict]
                    )
                    logger.debug(f"Interaction stored in long-term memory: {interaction_id}")
                except Exception as e:
                    logger.error(f"Error storing interaction in Chroma: {e}")
            
            return interaction_id
        except Exception as e:
            logger.error(f"Error storing interaction: {e}")
            # Don't re-raise the exception to avoid disrupting the main flow
            return None
    
    async def get_recent_interactions(self, count: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent interactions from mid-term memory.
        
        Args:
            count: Maximum number of interactions to retrieve
            
        Returns:
            List of recent interactions
        """
        try:
            # Use thread-safe connection
            conn = self.mid_term_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM interactions ORDER BY timestamp DESC LIMIT ?",
                (count,)
            )
            
            # Process results
            interactions = []
            for row in cursor.fetchall():
                id, timestamp, user_input, friday_response, context, metadata = row
                interactions.append({
                    "id": id,
                    "timestamp": timestamp,
                    "user_input": user_input,
                    "friday_response": friday_response,
                    "context": json.loads(context) if context else None,
                    "metadata": json.loads(metadata) if metadata else None
                })
            
            logger.debug(f"Retrieved {len(interactions)} recent interactions")
            return interactions
        except Exception as e:
            logger.error(f"Error retrieving recent interactions: {e}")
            return []
    
    async def store_user_preference(self, key: str, value: Any) -> bool:
        """Store a user preference in mid-term memory.
        
        Args:
            key: Preference identifier
            value: Preference value (will be JSON serialized)
            
        Returns:
            Success flag
        """
        try:
            timestamp = datetime.datetime.now().isoformat()
            serialized_value = json.dumps(value)
            
            # Use thread-safe connection
            conn = self.mid_term_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO user_preferences VALUES (?, ?, ?)",
                (key, serialized_value, timestamp)
            )
            conn.commit()
            logger.debug(f"User preference stored: {key}")
            return True
        except Exception as e:
            logger.error(f"Error storing user preference: {e}")
            return False
    
    async def get_user_preference(self, key: str, default: Any = None) -> Any:
        """Retrieve a user preference from mid-term memory.
        
        Args:
            key: Preference identifier
            default: Default value if preference not found
            
        Returns:
            Preference value or default
        """
        try:
            # Use thread-safe connection
            conn = self.mid_term_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT value FROM user_preferences WHERE key = ?",
                (key,)
            )
            
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return default
        except Exception as e:
            logger.error(f"Error retrieving user preference: {e}")
            return default
    
    async def get_user_profile(self) -> Dict[str, Any]:
        """Retrieve the complete user profile from preferences.
        
        Returns:
            User profile dictionary
        """
        try:
            # Use thread-safe connection
            conn = self.mid_term_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM user_preferences")
            
            profile = {}
            for key, value in cursor.fetchall():
                profile[key] = json.loads(value)
            
            logger.debug(f"Retrieved complete user profile with {len(profile)} preferences")
            return profile
        except Exception as e:
            logger.error(f"Error retrieving user profile: {e}")
            return {}
    
    # Long-term memory operations
    
    async def store_knowledge(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """Store knowledge in long-term memory for future retrieval.
        
        Args:
            text: Knowledge text to store
            metadata: Additional information about the knowledge
            
        Returns:
            Knowledge ID
        """
        if not self.long_term or not self.knowledge_collection:
            logger.warning("Long-term memory not available for storing knowledge")
            return None
            
        try:
            knowledge_id = str(uuid.uuid4())
            
            # Prepare metadata
            metadata_dict = {
                "timestamp": datetime.datetime.now().isoformat(),
                "type": "knowledge"
            }
            if metadata:
                metadata_dict.update(metadata)
            
            # Store in Chroma
            self.knowledge_collection.add(
                ids=[knowledge_id],
                documents=[text],
                metadatas=[metadata_dict]
            )
            
            logger.debug(f"Knowledge stored in long-term memory: {knowledge_id}")
            return knowledge_id
        except Exception as e:
            logger.error(f"Error storing knowledge: {e}")
            return None
    
    async def search_knowledge(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search long-term memory for relevant knowledge.
        
        Args:
            query: Search query text
            n_results: Maximum number of results
            
        Returns:
            List of relevant knowledge items
        """
        if not self.long_term or not self.knowledge_collection:
            logger.warning("Long-term memory not available for searching knowledge")
            return []
            
        try:
            # Search in Chroma
            results = self.knowledge_collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Process results
            knowledge_items = []
            for i, (id, document, metadata) in enumerate(zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0]
            )):
                knowledge_items.append({
                    "id": id,
                    "text": document,
                    "metadata": metadata
                })
            
            logger.debug(f"Knowledge search found {len(knowledge_items)} results for: {query}")
            return knowledge_items
        except Exception as e:
            logger.error(f"Error searching knowledge: {e}")
            return []
    
    async def semantic_search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search across all long-term collections for relevant information.
        
        Args:
            query: Search query text
            n_results: Maximum number of results per collection
            
        Returns:
            List of relevant items from all collections
        """
        if not self.long_term:
            logger.warning("Long-term memory not available for semantic search")
            return []
            
        results = []
        
        try:
            # Search in all available collections
            collections = []
            if self.knowledge_collection:
                collections.append(("knowledge", self.knowledge_collection))
            if self.interaction_collection:
                collections.append(("interactions", self.interaction_collection))
            if self.persona_collection:
                collections.append(("persona", self.persona_collection))
                
            for collection_name, collection in collections:
                try:
                    collection_results = collection.query(
                        query_texts=[query],
                        n_results=n_results
                    )
                    
                    if collection_results["ids"][0]:  # Check if any results
                        # Process results
                        for i, (id, document, metadata) in enumerate(zip(
                            collection_results["ids"][0],
                            collection_results["documents"][0],
                            collection_results["metadatas"][0]
                        )):
                            results.append({
                                "id": id,
                                "text": document,
                                "metadata": metadata,
                                "collection": collection_name,
                                "distance": collection_results.get("distances", [[]])[0][i] if "distances" in collection_results else None
                            })
                except Exception as e:
                    logger.error(f"Error searching {collection_name} collection: {e}")
            
            # Sort by relevance (if distances available)
            results.sort(key=lambda x: x.get("distance", float('inf')) if x.get("distance") is not None else float('inf'))
            
            logger.debug(f"Semantic search found {len(results)} results for: {query}")
            return results
        except Exception as e:
            logger.error(f"Error performing semantic search: {e}")
            return []
    
    # Memory management operations
    
    async def cleanup_expired_data(self) -> Tuple[int, int, int]:
        """Clean up expired data across all memory tiers.
        
        Returns:
            Tuple of (short_term_cleaned, mid_term_cleaned, long_term_cleaned) counts
        """
        short_cleaned = mid_cleaned = long_cleaned = 0
        
        # Short-term cleaning happens automatically with TTL in Redis
        
        # For mid-term, remove interactions older than retention period
        try:
            retention_days = self.config["mid_term"]["retention_days"]
            cutoff_date = (datetime.datetime.now() - 
                          datetime.timedelta(days=retention_days)).isoformat()
            
            # Use thread-safe connection
            conn = self.mid_term_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM interactions WHERE timestamp < ?",
                (cutoff_date,)
            )
            mid_cleaned = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {mid_cleaned} expired interactions from mid-term memory")
        except Exception as e:
            logger.error(f"Error cleaning mid-term memory: {e}")
        
        # Long-term cleaning would be based on specific criteria
        # This is a placeholder for future implementation
        
        return (short_cleaned, mid_cleaned, long_cleaned)
    
    async def get_memory_status(self) -> Dict[str, Any]:
        """Get current status and statistics of the memory system.
        
        Returns:
            Memory status information
        """
        status = {
            "short_term": {
                "available": self.short_term is not None,
                "fallback_available": True,  # In-memory dict is always available
                "count": 0,
                "in_memory_count": len(self._short_term_dict)
            },
            "mid_term": {
                "available": self.mid_term_manager is not None,
                "interactions": 0,
                "sessions": 0,
                "preferences": 0
            },
            "long_term": {
                "available": self.long_term is not None,
                "knowledge_collection_available": self.knowledge_collection is not None,
                "interaction_collection_available": self.interaction_collection is not None,
                "persona_collection_available": self.persona_collection is not None,
                "knowledge_count": 0,
                "interaction_count": 0,
                "persona_count": 0
            }
        }
        
        # Get short-term stats
        if self.short_term:
            try:
                status["short_term"]["count"] = self.short_term.dbsize()
            except Exception as e:
                logger.warning(f"Error getting Redis stats: {e}")
        
        # Get mid-term stats
        if self.mid_term_manager:
            try:
                # Use thread-safe connection
                conn = self.mid_term_manager.get_connection()
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM interactions")
                status["mid_term"]["interactions"] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM session_summaries")
                status["mid_term"]["sessions"] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM user_preferences")
                status["mid_term"]["preferences"] = cursor.fetchone()[0]
            except Exception as e:
                logger.warning(f"Error getting SQLite stats: {e}")
        
        # Get long-term stats
        if self.long_term:
            if self.knowledge_collection:
                try:
                    status["long_term"]["knowledge_count"] = self.knowledge_collection.count()
                except Exception as e:
                    logger.warning(f"Error getting knowledge collection stats: {e}")
                    
            if self.interaction_collection:
                try:
                    status["long_term"]["interaction_count"] = self.interaction_collection.count()
                except Exception as e:
                    logger.warning(f"Error getting interaction collection stats: {e}")
                    
            if self.persona_collection:
                try:
                    status["long_term"]["persona_count"] = self.persona_collection.count()
                except Exception as e:
                    logger.warning(f"Error getting persona collection stats: {e}")
        
        return status