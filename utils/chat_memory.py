"""
历史会话记忆模块 —— SQLite 持久化层

职责：
- 会话的 CRUD（创建/查询/删除）
- 消息的持久化存储与读取
- 为 Agent 提供最近消息上下文

数据流：
    app.py → chat_memory.save_message() → SQLite
    app.py → chat_memory.get_messages() → Agent 上下文
"""

import sqlite3
import uuid
import os
from datetime import datetime
from typing import Optional
from utils.path import get_abs_path

# 数据库文件存放在项目根目录
DB_PATH = get_abs_path("chat_history.db")


def _get_connection() -> sqlite3.Connection:
    """获取数据库连接（每次调用创建新连接，避免多线程问题）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 让查询结果支持列名访问
    conn.execute("PRAGMA journal_mode=WAL")  # WAL 模式提升并发性能
    return conn


def init_db():
    """
    初始化数据库表结构。

    如果表已存在则跳过，保证幂等性。
    在应用启动时调用一次即可。
    """
    conn = _get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT DEFAULT 'default',
                title TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conv
                ON messages(conversation_id, created_at);
        """)
        conn.commit()
    finally:
        conn.close()


def create_conversation(title: str = "") -> str:
    """
    创建新会话。

    Args:
        title: 会话标题，为空时后续会用首条消息自动填充。

    Returns:
        新会话的 UUID 字符串。
    """
    conv_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (conv_id, title, now, now),
        )
        conn.commit()
        return conv_id
    finally:
        conn.close()


def get_conversations() -> list[dict]:
    """
    获取所有会话，按更新时间倒序排列（最近的在前）。

    Returns:
        会话字典列表，每个字典包含 id, title, created_at, updated_at, message_count。
    """
    conn = _get_connection()
    try:
        rows = conn.execute("""
            SELECT
                c.id,
                c.title,
                c.created_at,
                c.updated_at,
                (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count
            FROM conversations c
            ORDER BY c.updated_at DESC
        """).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_conversation(conv_id: str) -> Optional[dict]:
    """获取单个会话的详细信息，不存在时返回 None。"""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
            (conv_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_conversation(conv_id: str):
    """
    删除会话及其关联的所有消息。

    注意：外键级联删除可能未启用，因此手动删除两条表。
    """
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        conn.commit()
    finally:
        conn.close()


def update_conversation_title(conv_id: str, title: str):
    """更新会话标题（通常在首条用户消息后调用）。"""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, datetime.now().isoformat(), conv_id),
        )
        conn.commit()
    finally:
        conn.close()


def save_message(conv_id: str, role: str, content: str):
    """
    保存一条消息到数据库，同时更新会话的更新时间。

    Args:
        conv_id: 所属会话 ID。
        role: 'user' 或 'assistant'。
        content: 消息文本内容。
    """
    now = datetime.now().isoformat()
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conv_id, role, content, now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conv_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_messages(conv_id: str) -> list[dict]:
    """
    获取指定会话的全部消息，按时间正序排列。

    Args:
        conv_id: 会话 ID。

    Returns:
        消息字典列表，每个包含 id, role, content, created_at。
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT id, role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conv_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_recent_messages(conv_id: str, limit: int = 10) -> list[dict]:
    """
    获取某个会话最近 N 条消息，按时间正序排列。

    用于 Agent 初始化时注入对话上下文，
    让 Agent 了解之前聊了什么。

    Args:
        conv_id: 会话 ID。
        limit: 返回的最大消息条数。

    Returns:
        消息字典列表（按时间正序）。
    """
    conn = _get_connection()
    try:
        # 子查询取最近 N 条（按时间倒序取），外层再正序排列
        rows = conn.execute("""
            SELECT id, role, content, created_at FROM (
                SELECT id, role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ) ORDER BY created_at ASC
        """, (conv_id, limit)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
