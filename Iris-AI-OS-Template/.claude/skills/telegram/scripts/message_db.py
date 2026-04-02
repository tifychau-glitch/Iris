"""
Message Database — SQLite storage for message history and conversation tracking.

Usage:
    python .claude/skills/telegram/scripts/message_db.py --action log --platform telegram --direction inbound --chat-id 123 --content "Hello"
    python .claude/skills/telegram/scripts/message_db.py --action history --chat-id 123 --limit 20
    python .claude/skills/telegram/scripts/message_db.py --action stats
    python .claude/skills/telegram/scripts/message_db.py --action recent --hours 24
"""

import sys
import json
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _find_project_root():
    path = Path(__file__).resolve().parent
    while path != path.parent:
        if (path / ".env").exists() or (path / "CLAUDE.md").exists():
            return path
        path = path.parent
    raise RuntimeError("Could not find project root")

PROJECT_ROOT = _find_project_root()
DB_PATH = PROJECT_ROOT / "data" / "messages.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL CHECK(platform IN ('telegram', 'slack', 'discord', 'other')),
            direction TEXT NOT NULL CHECK(direction IN ('inbound', 'outbound')),
            chat_id TEXT NOT NULL,
            user_id TEXT,
            username TEXT,
            content TEXT,
            message_type TEXT DEFAULT 'text',
            external_message_id TEXT,
            reply_to_id INTEGER,
            metadata TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            processed_at DATETIME,
            status TEXT DEFAULT 'received' CHECK(status IN ('received', 'processing', 'processed', 'failed', 'rejected'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            chat_id TEXT NOT NULL UNIQUE,
            chat_type TEXT DEFAULT 'private',
            title TEXT,
            first_message_at DATETIME,
            last_message_at DATETIME,
            message_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            metadata TEXT
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(platform, chat_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_chat ON conversations(platform, chat_id)")

    conn.commit()
    return conn


def row_to_dict(row) -> Optional[Dict]:
    if row is None:
        return None
    return dict(row)


def log_message(
    platform: str,
    direction: str,
    chat_id: str,
    content: str,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    message_type: str = "text",
    external_message_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
    status: str = "received",
) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    metadata_json = json.dumps(metadata) if metadata else None

    cursor.execute(
        """
        INSERT INTO messages
        (platform, direction, chat_id, user_id, username, content, message_type,
         external_message_id, metadata, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            platform, direction, chat_id, user_id, username, content,
            message_type, external_message_id, metadata_json, status,
        ),
    )

    message_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO conversations (platform, chat_id, first_message_at, last_message_at, message_count)
        VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 1)
        ON CONFLICT(chat_id) DO UPDATE SET
            last_message_at = CURRENT_TIMESTAMP,
            message_count = message_count + 1
    """,
        (platform, chat_id),
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message_id": message_id,
        "platform": platform,
        "direction": direction,
        "chat_id": chat_id,
    }


def get_history(
    chat_id: str,
    platform: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    if platform:
        cursor.execute(
            "SELECT * FROM messages WHERE chat_id = ? AND platform = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (chat_id, platform, limit, offset),
        )
    else:
        cursor.execute(
            "SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (chat_id, limit, offset),
        )

    messages = [row_to_dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT * FROM conversations WHERE chat_id = ?", (chat_id,))
    conversation = row_to_dict(cursor.fetchone())

    conn.close()

    return {
        "success": True,
        "chat_id": chat_id,
        "conversation": conversation,
        "messages": messages,
        "count": len(messages),
    }


def get_recent(hours: int = 24, platform: Optional[str] = None) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()

    if platform:
        cursor.execute(
            "SELECT * FROM messages WHERE created_at >= ? AND platform = ? ORDER BY created_at DESC",
            (cutoff, platform),
        )
    else:
        cursor.execute(
            "SELECT * FROM messages WHERE created_at >= ? ORDER BY created_at DESC",
            (cutoff,),
        )

    messages = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()

    return {"success": True, "hours": hours, "messages": messages, "count": len(messages)}


def get_stats() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM messages")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT platform, COUNT(*) as count FROM messages GROUP BY platform")
    by_platform = {row["platform"]: row["count"] for row in cursor.fetchall()}

    cursor.execute("SELECT direction, COUNT(*) as count FROM messages GROUP BY direction")
    by_direction = {row["direction"]: row["count"] for row in cursor.fetchall()}

    cursor.execute("SELECT COUNT(*) as count FROM conversations WHERE is_active = 1")
    active_conversations = cursor.fetchone()["count"]

    today = datetime.now().date().isoformat()
    cursor.execute("SELECT COUNT(*) as count FROM messages WHERE date(created_at) = ?", (today,))
    today_count = cursor.fetchone()["count"]

    conn.close()

    return {
        "success": True,
        "stats": {
            "total_messages": total,
            "by_platform": by_platform,
            "by_direction": by_direction,
            "active_conversations": active_conversations,
            "messages_today": today_count,
        },
    }


def update_status(message_id: int, status: str) -> Dict[str, Any]:
    valid_statuses = ["received", "processing", "processed", "failed", "rejected"]
    if status not in valid_statuses:
        return {"success": False, "error": f"Invalid status. Must be one of: {valid_statuses}"}

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE messages SET status = ?, processed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, message_id),
    )

    if cursor.rowcount == 0:
        conn.close()
        return {"success": False, "error": f"Message {message_id} not found"}

    conn.commit()
    conn.close()

    return {"success": True, "message_id": message_id, "status": status}


def get_conversations(
    platform: Optional[str] = None, active_only: bool = True, limit: int = 50
) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    conditions = []
    params = []

    if platform:
        conditions.append("platform = ?")
        params.append(platform)

    if active_only:
        conditions.append("is_active = 1")

    where = " AND ".join(conditions) if conditions else "1=1"

    cursor.execute(
        f"SELECT * FROM conversations WHERE {where} ORDER BY last_message_at DESC LIMIT ?",
        params + [limit],
    )

    conversations = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()

    return {"success": True, "conversations": conversations, "count": len(conversations)}


def main():
    parser = argparse.ArgumentParser(description="Message Database Manager")
    parser.add_argument(
        "--action", required=True,
        choices=["log", "history", "recent", "stats", "update-status", "conversations"],
    )
    parser.add_argument("--platform", choices=["telegram", "slack", "discord", "other"])
    parser.add_argument("--direction", choices=["inbound", "outbound"])
    parser.add_argument("--chat-id")
    parser.add_argument("--user-id")
    parser.add_argument("--username")
    parser.add_argument("--content")
    parser.add_argument("--message-id", type=int)
    parser.add_argument("--status")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)

    args = parser.parse_args()
    result = None

    if args.action == "log":
        if not all([args.platform, args.direction, args.chat_id, args.content]):
            print("Error: --platform, --direction, --chat-id, and --content required for log")
            sys.exit(1)
        result = log_message(
            platform=args.platform, direction=args.direction,
            chat_id=args.chat_id, content=args.content,
            user_id=args.user_id, username=args.username,
        )
    elif args.action == "history":
        if not args.chat_id:
            print("Error: --chat-id required for history")
            sys.exit(1)
        result = get_history(chat_id=args.chat_id, platform=args.platform, limit=args.limit, offset=args.offset)
    elif args.action == "recent":
        result = get_recent(hours=args.hours, platform=args.platform)
    elif args.action == "stats":
        result = get_stats()
    elif args.action == "update-status":
        if not args.message_id or not args.status:
            print("Error: --message-id and --status required")
            sys.exit(1)
        result = update_status(args.message_id, args.status)
    elif args.action == "conversations":
        result = get_conversations(platform=args.platform, limit=args.limit)

    if result:
        if result.get("success"):
            print("OK")
        else:
            print(f"ERROR {result.get('error')}")
            sys.exit(1)
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
