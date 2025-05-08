import sqlite3
import json
import logging
from datetime import datetime

class UserPreferences:
    """Manages user preferences and learning patterns."""
    
    def __init__(self, db_path="personality/preferences.db"):
        """Initialize the user preferences manager."""
        self.db_path = db_path
        self.logger = logging.getLogger('friday.preferences')
        self._initialize_db()
    
    def _initialize_db(self):
        """Create database tables if they don't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create preferences table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                category TEXT,
                last_updated TIMESTAMP
            )
            ''')
            
            # Create routines table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS routines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                pattern TEXT,
                confidence REAL,
                last_observed TIMESTAMP,
                observation_count INTEGER
            )
            ''')
            
            # Create learning patterns table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT,
                interest_level REAL,
                engagement_pattern TEXT,
                last_updated TIMESTAMP
            )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Error initializing preferences database: {e}")
    
    def get_preference(self, key, default=None):
        """Get a user preference by key."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                return json.loads(result[0])
            return default
        except Exception as e:
            self.logger.error(f"Error getting preference {key}: {e}")
            return default
    
    def set_preference(self, key, value, category="general"):
        """Set a user preference."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            serialized_value = json.dumps(value)
            timestamp = datetime.now().isoformat()
            
            cursor.execute(
                "INSERT OR REPLACE INTO preferences (key, value, category, last_updated) VALUES (?, ?, ?, ?)",
                (key, serialized_value, category, timestamp)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"Error setting preference {key}: {e}")
            return False
    
    def get_preferences_by_category(self, category):
        """Get all preferences in a specific category."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT key, value FROM preferences WHERE category = ?", (category,))
            results = cursor.fetchall()
            
            conn.close()
            
            preferences = {}
            for key, value in results:
                preferences[key] = json.loads(value)
            
            return preferences
        except Exception as e:
            self.logger.error(f"Error getting preferences for category {category}: {e}")
            return {}
    
    def track_routine(self, name, pattern):
        """Track a user routine pattern."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if routine exists
            cursor.execute("SELECT id, confidence, observation_count FROM routines WHERE name = ?", (name,))
            result = cursor.fetchone()
            
            timestamp = datetime.now().isoformat()
            
            if result:
                # Update existing routine
                routine_id, confidence, count = result
                new_count = count + 1
                new_confidence = ((confidence * count) + 1.0) / new_count  # Simple confidence update
                
                cursor.execute(
                    "UPDATE routines SET pattern = ?, confidence = ?, last_observed = ?, observation_count = ? WHERE id = ?",
                    (pattern, new_confidence, timestamp, new_count, routine_id)
                )
            else:
                # Create new routine
                cursor.execute(
                    "INSERT INTO routines (name, pattern, confidence, last_observed, observation_count) VALUES (?, ?, ?, ?, ?)",
                    (name, pattern, 0.5, timestamp, 1)
                )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"Error tracking routine {name}: {e}")
            return False
    
    def get_routines(self, min_confidence=0.0):
        """Get user routines above a confidence threshold."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT name, pattern, confidence, last_observed, observation_count FROM routines WHERE confidence >= ?",
                (min_confidence,)
            )
            results = cursor.fetchall()
            
            conn.close()
            
            routines = []
            for name, pattern, confidence, last_observed, count in results:
                routines.append({
                    "name": name,
                    "pattern": pattern,
                    "confidence": confidence,
                    "last_observed": last_observed,
                    "observation_count": count
                })
            
            return routines
        except Exception as e:
            self.logger.error(f"Error getting routines: {e}")
            return []
    
    def update_learning_pattern(self, domain, interest_level, engagement_pattern):
        """Update user learning pattern for a knowledge domain."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = datetime.now().isoformat()
            
            cursor.execute(
                "INSERT OR REPLACE INTO learning_patterns (domain, interest_level, engagement_pattern, last_updated) VALUES (?, ?, ?, ?)",
                (domain, interest_level, engagement_pattern, timestamp)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            self.logger.error(f"Error updating learning pattern for {domain}: {e}")
            return False
    
    def get_learning_patterns(self):
        """Get user learning patterns."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT domain, interest_level, engagement_pattern, last_updated FROM learning_patterns")
            results = cursor.fetchall()
            
            conn.close()
            
            patterns = []
            for domain, interest_level, engagement_pattern, last_updated in results:
                patterns.append({
                    "domain": domain,
                    "interest_level": interest_level,
                    "engagement_pattern": engagement_pattern,
                    "last_updated": last_updated
                })
            
            return patterns
        except Exception as e:
            self.logger.error(f"Error getting learning patterns: {e}")
            return []