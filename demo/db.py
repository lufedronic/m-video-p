"""
Database module for m(video)p session persistence.
Uses SQLite for simple, file-based storage.
"""
import os
import json
import sqlite3
import uuid
from datetime import datetime
from contextlib import contextmanager

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "mvideop.db")


def init_db():
    """Initialize database and create tables if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                name TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                product_understanding TEXT,
                confidence REAL DEFAULT 0.0,
                is_ready INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                script TEXT,
                keyframe_urls TEXT,
                segment_urls TEXT,
                stitched_url TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
            CREATE INDEX IF NOT EXISTS idx_videos_session ON videos(session_id);

            CREATE TABLE IF NOT EXISTS consistency_states (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL UNIQUE,
                state_data TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_consistency_session ON consistency_states(session_id);
        """)


@contextmanager
def get_connection():
    """Get a database connection with foreign key support."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ============ Session Functions ============

def create_session(name=None):
    """Create a new session and return its ID."""
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (session_id, name, now, now)
        )

    return session_id


def get_session(session_id):
    """Get a session by ID with all related data."""
    with get_connection() as conn:
        # Get session
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()

        if not row:
            return None

        session = dict(row)
        session["product_understanding"] = json.loads(session["product_understanding"]) if session["product_understanding"] else {}
        session["is_ready"] = bool(session["is_ready"])

        # Get conversations
        convs = conn.execute(
            "SELECT role, content, created_at FROM conversations WHERE session_id = ? ORDER BY id",
            (session_id,)
        ).fetchall()
        session["conversation"] = [dict(c) for c in convs]

        # Get latest video
        video = conn.execute(
            "SELECT * FROM videos WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
            (session_id,)
        ).fetchone()

        if video:
            video_dict = dict(video)
            video_dict["script"] = json.loads(video_dict["script"]) if video_dict["script"] else None
            video_dict["keyframe_urls"] = json.loads(video_dict["keyframe_urls"]) if video_dict["keyframe_urls"] else {}
            video_dict["segment_urls"] = json.loads(video_dict["segment_urls"]) if video_dict["segment_urls"] else []
            session["video"] = video_dict
        else:
            session["video"] = None

        return session


def list_sessions():
    """List all sessions with summary info."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                s.id, s.name, s.created_at, s.updated_at, s.confidence,
                (SELECT COUNT(*) FROM videos v WHERE v.session_id = s.id AND v.stitched_url IS NOT NULL) > 0 AS has_video
            FROM sessions s
            ORDER BY s.updated_at DESC
        """).fetchall()

        return [dict(row) for row in rows]


def update_session(session_id, **kwargs):
    """Update session fields."""
    allowed = {"name", "product_understanding", "confidence", "is_ready"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}

    if not updates:
        return

    # Serialize JSON fields
    if "product_understanding" in updates:
        updates["product_understanding"] = json.dumps(updates["product_understanding"])

    updates["updated_at"] = datetime.utcnow().isoformat()

    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [session_id]

    with get_connection() as conn:
        conn.execute(f"UPDATE sessions SET {set_clause} WHERE id = ?", values)


def delete_session(session_id):
    """Delete a session and all related data."""
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


def rename_session(session_id, name):
    """Rename a session."""
    update_session(session_id, name=name)


# ============ Conversation Functions ============

def add_message(session_id, role, content):
    """Add a message to a session's conversation."""
    now = datetime.utcnow().isoformat()

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO conversations (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now)
        )
        # Update session's updated_at
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, session_id)
        )


def get_conversation(session_id):
    """Get all messages for a session."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY id",
            (session_id,)
        ).fetchall()

        return [{"role": row["role"], "content": row["content"]} for row in rows]


# ============ Video Functions ============

def create_video(session_id, script=None):
    """Create a new video record for a session."""
    video_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO videos (id, session_id, script, created_at) VALUES (?, ?, ?, ?)",
            (video_id, session_id, json.dumps(script) if script else None, now)
        )
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, session_id)
        )

    return video_id


def update_video(video_id, **kwargs):
    """Update video fields."""
    allowed = {"script", "keyframe_urls", "segment_urls", "stitched_url", "status"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}

    if not updates:
        return

    # Serialize JSON fields
    for key in ("script", "keyframe_urls", "segment_urls"):
        if key in updates and updates[key] is not None:
            updates[key] = json.dumps(updates[key])

    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [video_id]

    with get_connection() as conn:
        conn.execute(f"UPDATE videos SET {set_clause} WHERE id = ?", values)


def get_video(video_id):
    """Get a video by ID."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()

        if not row:
            return None

        video = dict(row)
        video["script"] = json.loads(video["script"]) if video["script"] else None
        video["keyframe_urls"] = json.loads(video["keyframe_urls"]) if video["keyframe_urls"] else {}
        video["segment_urls"] = json.loads(video["segment_urls"]) if video["segment_urls"] else []

        return video


def get_session_video(session_id):
    """Get the latest video for a session."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM videos WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
            (session_id,)
        ).fetchone()

        if not row:
            return None

        video = dict(row)
        video["script"] = json.loads(video["script"]) if video["script"] else None
        video["keyframe_urls"] = json.loads(video["keyframe_urls"]) if video["keyframe_urls"] else {}
        video["segment_urls"] = json.loads(video["segment_urls"]) if video["segment_urls"] else []

        return video


# ============ Consistency State Functions ============

def save_consistency_state(state):
    """
    Save a VideoConsistencyState to the database.

    Args:
        state: VideoConsistencyState instance (will be serialized to JSON)
    """
    now = datetime.utcnow().isoformat()

    # Serialize state to JSON
    if hasattr(state, "model_dump"):
        # Pydantic v2
        state_data = json.dumps(state.model_dump(mode="json"))
    elif hasattr(state, "dict"):
        # Pydantic v1
        state_data = json.dumps(state.dict())
    else:
        # Already a dict
        state_data = json.dumps(state)

    state_id = state.id if hasattr(state, "id") else str(uuid.uuid4())
    session_id = state.session_id if hasattr(state, "session_id") else None
    version = state.version if hasattr(state, "version") else 1

    if not session_id:
        raise ValueError("state must have a session_id")

    with get_connection() as conn:
        # Check if exists
        existing = conn.execute(
            "SELECT id FROM consistency_states WHERE session_id = ?",
            (session_id,)
        ).fetchone()

        if existing:
            # Update existing
            conn.execute("""
                UPDATE consistency_states
                SET state_data = ?, version = ?, updated_at = ?
                WHERE session_id = ?
            """, (state_data, version, now, session_id))
        else:
            # Insert new
            conn.execute("""
                INSERT INTO consistency_states (id, session_id, state_data, version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (state_id, session_id, state_data, version, now, now))

        # Update session's updated_at
        conn.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now, session_id)
        )


def get_consistency_state(session_id):
    """
    Get the consistency state for a session.

    Args:
        session_id: The session ID

    Returns:
        VideoConsistencyState instance or None if not found
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM consistency_states WHERE session_id = ?",
            (session_id,)
        ).fetchone()

        if not row:
            return None

        state_data = json.loads(row["state_data"])

        # Try to return as VideoConsistencyState if available
        try:
            from consistency.schemas import VideoConsistencyState
            return VideoConsistencyState.model_validate(state_data)
        except ImportError:
            # Return raw dict if schemas not available
            return state_data


def delete_consistency_state(session_id):
    """
    Delete the consistency state for a session.

    Args:
        session_id: The session ID
    """
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM consistency_states WHERE session_id = ?",
            (session_id,)
        )


def get_consistency_state_version(session_id):
    """
    Get the current version of a consistency state without loading full data.

    Args:
        session_id: The session ID

    Returns:
        Version number or None if not found
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT version FROM consistency_states WHERE session_id = ?",
            (session_id,)
        ).fetchone()

        return row["version"] if row else None


# Initialize DB on import
init_db()
