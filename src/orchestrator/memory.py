"""Memory management for conversational travel assistant
Handles conversation history, context retrieval, and session persistence.
"""
from __future__ import annotations

import json
import sqlite3
import hashlib
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.utils.logger import get_logger
from src.utils.config import Settings


@dataclass
class ConversationMessage:
    """Single message in conversation"""
    timestamp: str
    role: str  # 'user' | 'assistant'
    content: str
    message_type: str = "text"  # 'text' | 'itinerary' | 'refinement'
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TripContext:
    """Current trip planning context"""
    query: str
    destinations: List[str]
    duration_days: int
    budget_range: str
    preferences: List[str]
    current_itinerary: Optional[str] = None
    refinements: List[str] = None

    def __post_init__(self):
        if self.refinements is None:
            self.refinements = []


class MemoryManager:
    """Manages conversation memory and context for travel assistant"""

    def __init__(self, settings: Settings, data_dir: Path = None):
        self.settings = settings
        self.logger = get_logger("memory_manager")
        self.data_dir = data_dir or Path("src/data/sessions")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize SQLite database
        self.db_path = self.data_dir / "conversations.db"
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for conversations"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT,
                    last_updated TEXT,
                    trip_context TEXT,
                    message_count INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp TEXT,
                    role TEXT,
                    content TEXT,
                    message_type TEXT,
                    metadata TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            """)
            conn.commit()

    def create_session(self, initial_query: str = None) -> str:
        """Create new conversation session"""
        session_id = hashlib.md5(f"{datetime.now().isoformat()}{initial_query or ''}".encode()).hexdigest()[:12]
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO sessions (session_id, created_at, last_updated, trip_context, message_count)
                VALUES (?, ?, ?, ?, 0)
            """, (
                session_id,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                json.dumps({}),
            ))
            conn.commit()
        
        self.logger.info(f"Created new session: {session_id}")
        return session_id

    def add_message(self, session_id: str, role: str, content: str, 
                   message_type: str = "text", metadata: Dict[str, Any] = None) -> None:
        """Add message to conversation history"""
        message = ConversationMessage(
            timestamp=datetime.now().isoformat(),
            role=role,
            content=content,
            message_type=message_type,
            metadata=metadata or {}
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO messages (session_id, timestamp, role, content, message_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                message.timestamp,
                message.role,
                message.content,
                message.message_type,
                json.dumps(message.metadata)
            ))
            
            # Update session last_updated and message count
            conn.execute("""
                UPDATE sessions 
                SET last_updated = ?, message_count = message_count + 1
                WHERE session_id = ?
            """, (datetime.now().isoformat(), session_id))
            conn.commit()

    def get_conversation_history(self, session_id: str, limit: int = 50) -> List[ConversationMessage]:
        """Retrieve conversation history for session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp, role, content, message_type, metadata
                FROM messages 
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit))
            
            messages = []
            for row in cursor.fetchall():
                timestamp, role, content, message_type, metadata_str = row
                metadata = json.loads(metadata_str) if metadata_str else {}
                messages.append(ConversationMessage(
                    timestamp=timestamp,
                    role=role,
                    content=content,
                    message_type=message_type,
                    metadata=metadata
                ))
            
            # Reverse to get chronological order
            return list(reversed(messages))

    def update_trip_context(self, session_id: str, context: TripContext) -> None:
        """Update trip planning context for session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sessions 
                SET trip_context = ?, last_updated = ?
                WHERE session_id = ?
            """, (
                json.dumps(asdict(context)),
                datetime.now().isoformat(),
                session_id
            ))
            conn.commit()

    def get_trip_context(self, session_id: str) -> Optional[TripContext]:
        """Retrieve trip context for session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT trip_context FROM sessions WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            if row and row[0]:
                try:
                    context_data = json.loads(row[0])
                    return TripContext(**context_data)
                except (json.JSONDecodeError, TypeError) as e:
                    self.logger.warning(f"Failed to parse trip context: {e}")
                    return None
            return None

    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recent sessions with basic info"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT session_id, created_at, last_updated, message_count, trip_context
                FROM sessions 
                ORDER BY last_updated DESC
                LIMIT ?
            """, (limit,))
            
            sessions = []
            for row in cursor.fetchall():
                session_id, created_at, last_updated, msg_count, trip_context_str = row
                
                # Extract basic trip info for preview
                trip_info = "New session"
                if trip_context_str:
                    try:
                        context = json.loads(trip_context_str)
                        if context.get('query'):
                            trip_info = context['query'][:50] + ("..." if len(context.get('query', '')) > 50 else "")
                    except:
                        pass
                
                sessions.append({
                    'session_id': session_id,
                    'created_at': created_at,
                    'last_updated': last_updated,
                    'message_count': msg_count,
                    'trip_info': trip_info
                })
            
            return sessions

    def get_context_summary(self, session_id: str) -> str:
        """Generate context summary for LLM consumption"""
        history = self.get_conversation_history(session_id, limit=10)
        context = self.get_trip_context(session_id)
        
        summary_parts = []
        
        if context:
            summary_parts.append(f"Current Trip: {context.query}")
            if context.current_itinerary:
                summary_parts.append("✓ Itinerary generated")
            if context.refinements:
                summary_parts.append(f"Refinements: {', '.join(context.refinements[-3:])}")
        
        if history:
            recent_messages = []
            for msg in history[-5:]:
                role_icon = "👤" if msg.role == "user" else "🤖"
                content_preview = msg.content[:100] + ("..." if len(msg.content) > 100 else "")
                recent_messages.append(f"{role_icon} {content_preview}")
            
            summary_parts.append("Recent conversation:")
            summary_parts.extend(recent_messages)
        
        return "\n".join(summary_parts) if summary_parts else "New conversation"

    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Clean up sessions older than specified days"""
        cutoff_date = datetime.now().replace(microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days_old)
        
        with sqlite3.connect(self.db_path) as conn:
            # Delete old messages first (foreign key constraint)
            cursor = conn.execute("""
                DELETE FROM messages 
                WHERE session_id IN (
                    SELECT session_id FROM sessions 
                    WHERE last_updated < ?
                )
            """, (cutoff_date.isoformat(),))
            deleted_messages = cursor.rowcount
            
            # Delete old sessions
            cursor = conn.execute("""
                DELETE FROM sessions WHERE last_updated < ?
            """, (cutoff_date.isoformat(),))
            deleted_sessions = cursor.rowcount
            
            conn.commit()
        
        self.logger.info(f"Cleaned up {deleted_sessions} old sessions, {deleted_messages} messages")
        return deleted_sessions