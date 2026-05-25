"""
Agent 侧历史会话记忆工具。

提供 @tool 装饰的函数，供 Agent 在回答问题时主动查询
该用户的历史对话记录，从而给出更连续、更精准的回答。

使用场景举例：
- 用户问"我之前问过那个清洁问题"，Agent 可查询历史记录
- Agent 在回答时参考用户历史反馈，给出针对性建议
"""

from langchain_core.tools import tool
from utils.chat_memory import get_recent_messages, get_conversations


@tool(description="查询指定用户最近的历史对话记录，入参为用户ID（如'1001'），返回最近的对话摘要列表，每条包含会话标题、时间、消息条数。Agent 可用此信息了解用户之前问过什么问题。")
def query_conversation_history(user_id: str = "default") -> str:
    """
    查询用户最近的历史会话和消息。

    这是一个只读工具，不会修改任何数据。
    Agent 在需要回顾用户之前的问题或反馈时调用此工具。

    Args:
        user_id: 用户 ID 字符串（目前系统预留，默认使用 "default"）。

    Returns:
        格式化的历史会话摘要字符串。
    """
    conversations = get_conversations()

    if not conversations:
        return "暂无历史对话记录。"

    result_parts = ["以下是该用户最近的历史对话记录：\n"]

    for conv in conversations[:5]:  # 最多返回最近 5 个会话
        title = conv["title"] if conv["title"] else "未命名会话"
        msg_count = conv["message_count"]
        updated = conv["updated_at"][:19]  # 截取到秒

        # 获取该会话的最后一条消息作为摘要
        recent = get_recent_messages(conv["id"], limit=1)
        last_msg = ""
        if recent:
            msg = recent[0]
            # 只取前 50 个字符作为摘要
            last_msg = msg["content"][:50].replace("\n", " ")
            last_msg = f"  最后消息：{last_msg}..." if len(msg["content"]) > 50 else f"  最后消息：{last_msg}"

        result_parts.append(
            f"会话：{title}\n"
            f"  消息数：{msg_count} | 最后更新：{updated}\n"
            f"{last_msg}\n"
        )

    return "\n".join(result_parts)
