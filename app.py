import streamlit as st
from agent.react_agent import ReactAgent
from dotenv import load_dotenv
from utils.chat_memory import (
    init_db, create_conversation, get_conversations, get_messages,
    save_message, delete_conversation, update_conversation_title, get_conversation,
)

load_dotenv()

# 启动时初始化数据库表结构（幂等）
init_db()

# 设置页面
st.set_page_config(page_title="扫地机器人客服", layout="wide")
st.title("扫地机器人客服")
st.divider()

# =====================================================================
# 侧边栏 —— 会话管理
# =====================================================================
with st.sidebar:
    st.subheader("历史会话")

    if st.button("＋ 新建会话", use_container_width=True, type="primary"):
        st.session_state.pop("current_conv_id", None)
        st.session_state.pop("messages", None)
        st.rerun()

    conversations = get_conversations()

    if conversations:
        conv_options = {
            conv["id"]: f"{conv['title'] or '新会话'} ({conv['message_count']}条)"
            for conv in conversations
        }
        selected_conv_id = st.radio(
            "选择会话",
            options=list(conv_options.keys()),
            format_func=lambda x: conv_options[x],
            label_visibility="collapsed",
            index=None,
        )

        if selected_conv_id and selected_conv_id != st.session_state.get("current_conv_id"):
            st.session_state["current_conv_id"] = selected_conv_id
            st.session_state["messages"] = get_messages(selected_conv_id)
            st.rerun()

        current_conv = st.session_state.get("current_conv_id")
        if current_conv and any(c["id"] == current_conv for c in conversations):
            if st.button("删除当前会话", use_container_width=True, type="secondary"):
                delete_conversation(current_conv)
                st.session_state.pop("current_conv_id", None)
                st.session_state["messages"] = []
                st.rerun()
    else:
        st.caption("暂无历史会话")

# =====================================================================
# 会话状态初始化
# =====================================================================
if "current_conv_id" not in st.session_state:
    new_id = create_conversation()
    st.session_state["current_conv_id"] = new_id

if "messages" not in st.session_state:
    st.session_state["messages"] = get_messages(st.session_state["current_conv_id"])

if "agent" not in st.session_state:
    st.session_state["agent"] = ReactAgent()

# =====================================================================
# 消息渲染
# =====================================================================
for message in st.session_state["messages"]:
    st.chat_message(message["role"]).write(message["content"])

# =====================================================================
# 用户输入处理
# =====================================================================
prompt = st.chat_input("请输入您的问题...")

if prompt:
    conv_id = st.session_state["current_conv_id"]

    # 保存用户消息
    save_message(conv_id, "user", prompt)
    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # 自动设置会话标题（首条用户消息的前 20 个字）
    conv = get_conversation(conv_id)
    if conv and not conv["title"]:
        title = prompt[:20] + ("..." if len(prompt) > 20 else "")
        update_conversation_title(conv_id, title)

    # 调用 Agent 获取流式回复
    response_messages = []
    with st.spinner("智能客服思考中..."):
        res_stream = st.session_state["agent"].execute_stream(prompt, conv_id=conv_id)

        def capture(generator, cache_list):
            for chunk in generator:
                cache_list.append(chunk)
                yield chunk

        st.chat_message("assistant").write_stream(capture(res_stream, response_messages))

    # 保存助手消息
    full_response = "".join(response_messages).strip()
    if full_response:
        save_message(conv_id, "assistant", full_response)
        st.session_state["messages"].append({"role": "assistant", "content": full_response})