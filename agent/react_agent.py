from langchain.agents import create_agent
from model.factory import chat_model
from utils.prompt_loader import load_system_prompts
from utils.chat_memory import get_recent_messages
from agent.tools.agent_tools import (
    rag_summarize, get_weather, get_user_location, get_user_ID,
    get_current_month, fetch_external_data, fill_context_for_report,
)
from agent.tools.memory_tools import query_conversation_history
from agent.tools.middleware import monitor_tool, log_before_model, report_prompt_switch, log_before_agent


# 注入 Agent 上下文的历史消息数量
_HISTORY_LIMIT = 10


class ReactAgent:
    def __init__(self):
        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompts(),
            tools=[
                rag_summarize, get_weather, get_user_location, get_user_ID,
                get_current_month, fetch_external_data, fill_context_for_report,
                query_conversation_history,
            ],
            middleware=[monitor_tool, log_before_model, report_prompt_switch, log_before_agent]
        )

    def execute_stream(self, query: str, conv_id: str = ""):
        """
        执行 Agent 的流式推理。

        Args:
            query: 用户当前输入的文本。
            conv_id: 当前会话 ID。传入后会自动加载该会话的最近历史消息
                     并注入到 Agent 的输入上下文中，实现跨轮次记忆。

        Yields:
            Agent 输出文本的分块内容。
        """
        # 构建消息列表，先注入历史消息（如果有）
        messages = []

        if conv_id:
            # 从数据库加载最近 N 条历史消息作为对话上下文
            history = get_recent_messages(conv_id, limit=_HISTORY_LIMIT)
            for msg in history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        # 追加当前用户输入
        messages.append({"role": "user", "content": query})

        input_dict = {"messages": messages}

        for chunk in self.agent.stream(input_dict, stream_mode="values", context={"report": False}):
            latest_message = chunk["messages"][-1]
            if latest_message.content:
                yield latest_message.content.strip() + "\n"

# if __name__=='__main__':
#     agent = ReactAgent()
    
#     for chunk in agent.execute_stream("扫地机器人在我所在的地区的气温下如何保养"):
#         print(chunk)