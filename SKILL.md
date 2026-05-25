---
name: python-ai-dev
description: 基于 Python 的 AI 应用开发指南，涵盖 LangChain/LangGraph Agent、RAG 系统、Streamlit 前端、向量数据库等常见 AI 应用开发的技术栈选型、架构模式和最佳实践。
metadata:
  type: development-guide
---

# Python AI 应用开发

## 技术栈选型

### AI Agent 框架
- **LangChain + LangGraph**: 构建 ReAct Agent，支持 `create_agent` 快速装配、中间件（`@wrap_tool_call`、`@before_model`、`@dynamic_prompt`、`@before_agent`）、流式输出
- **工具定义**: 使用 `@tool` 装饰器，通过 `description` 让 LLM 自主决策工具调用，入参通过类型注解自动解析
- **状态管理**: LangGraph 的 `AgentState` + `Runtime context` 管理 Agent 执行状态和上下文

### 模型接入
- **通义千问 (DashScope)**: `ChatTongyi` + `DashScopeEmbeddings`，通过 `DASHSCOPE_API_KEY` 环境变量认证
- **工厂模式**: 建议使用抽象工厂封装模型初始化，便于切换不同模型提供商

### 向量数据库
- **ChromaDB**: 轻量级本地向量数据库，`persist_directory` 指定持久化路径
- **文档处理**: `RecursiveCharacterTextSplitter` 分片，支持 txt/pdf 加载，MD5 去重

### 前端
- **Streamlit**: 快速构建 AI 应用 UI，`st.chat_message()` + `st.write_stream()` 实现流式对话，`st.session_state` 管理会话状态

## 项目结构规范

```
project/
├── app.py                    # 应用入口
├── agent/                    # Agent 层
│   ├── react_agent.py        # Agent 装配
│   └── tools/
│       ├── agent_tools.py    # 工具定义
│       └── middleware.py     # 中间件
├── model/
│   └── factory.py            # 模型工厂
├── rag/                      # RAG 层
│   ├── rag_service.py        # 检索总结链
│   └── vector_store.py       # 向量库管理
├── config/                   # YAML 配置
├── prompts/                  # 提示词模板
├── utils/                    # 工具函数
├── data/                     # 数据文件
└── logs/                     # 日志输出
```

## 关键开发模式

### 1. 配置管理
使用 YAML 集中管理所有可调参数，通过模块级单例加载。避免硬编码模型名、路径、分片参数等。

```python
# utils/config_handler.py
import yaml
def load_config(path):
    with open(path, encoding="utf-8") as f:
        return yaml.load(f, Loader=yaml.FullLoader)

rag_conf = load_config("config/rag.yml")
```

### 2. ReAct Agent 装配
```python
from langchain.agents import create_agent

agent = create_agent(
    model=chat_model,
    system_prompt=system_prompt,
    tools=[tool1, tool2],
    middleware=[monitor, log_before_model, prompt_switch]
)
```

### 3. 中间件驱动
- **`@wrap_tool_call`**: 包装工具调用，用于日志/监控/上下文注入
- **`@before_model`**: 模型调用前 hook，可修改 state
- **`@dynamic_prompt`**: 根据 runtime context 动态切换提示词
- **`@before_agent`**: Agent 启动前 hook

### 4. 报告/提示词切换模式
通过工具调用设置 `runtime.context` 标志，`dynamic_prompt` 中间件根据标志切换提示词，实现同一 Agent 在不同场景下的行为切换。

```python
# 工具中注入 context
request.runtime.context["report"] = True

# 中间件根据 context 切换提示词
@dynamic_prompt
def prompt_switch(request):
    if request.runtime.context.get("report"):
        return load_report_prompt()
    return load_main_prompt()
```

### 5. RAG 链
```python
chain = prompt_template | model | StrOutputParser()
result = chain.invoke({"input": query, "context": context_docs})
```

### 6. 工具定义规范
```python
@tool(description="清晰的工具描述，LLM 据此判断何时调用")
def my_tool(param1: str, param2: int) -> str:
    """返回值应为字符串，便于 LLM 处理"""
    return result
```

### 7. Streamlit 流式对话
```python
# 生成器捕获流式输出
def capture(generator, cache):
    for chunk in generator:
        cache.append(chunk)
        yield chunk

st.chat_message("assistant").write_stream(capture(stream, messages))
```

### 8. 统一路径解析
```python
# 所有路径基于项目根目录解析，确保跨平台兼容
def get_abs_path(relative_path):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, relative_path)
```

## 最佳实践

### 安全性
- API 密钥通过 `.env` 文件 + `python-dotenv` 加载，绝不硬编码
- `.env` 加入 `.gitignore`
- YAML 配置中不存放任何密钥

### 日志
- 同时输出到控制台 (INFO) 和文件 (DEBUG)
- 按日期分割日志文件
- 工具调用、模型调用、Agent 启动退出等关键节点必须记录

### 依赖管理
- 使用 `requirements.txt` 锁定版本
- 核心依赖: `langchain`, `langchain-core`, `langchain-community`, `langchain-chroma`, `streamlit`, `PyYAML`, `python-dotenv`, `dashscope`, `chromadb`, `pypdf`

### 错误处理
- 工具调用失败必须记录详细堆栈（`exc_info=True`）
- 外部数据读取失败应有降级处理
- 向量库加载失败不应阻塞应用启动

### Prompt 工程
- 系统提示词与代码分离，存放在独立文件
- 工具说明在 prompt 中需与代码中的 `@tool description` 保持一致
- 输出规则需明确约束（格式、语言、边界条件）
- ReAct Agent 的 prompt 应包含：角色定义、核心准则、工具说明、输出规则
