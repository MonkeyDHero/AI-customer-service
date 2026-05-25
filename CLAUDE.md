# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

扫地机器人智能客服系统 — 基于 LangChain/LangGraph ReAct Agent 的 Streamlit 应用，通过 RAG（ChromaDB + 通义千问向量模型）检索知识库，配合外部工具调用，为用户提供扫地机器人使用咨询和个性化报告生成服务。

## 快速启动

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 Streamlit UI
streamlit run app.py

# 加载知识库（首次运行或更新 data/ 下的 txt/pdf 文件后）
python -c "from rag.vector_store import VectorStoreService; VectorStoreService().load_document()"
```

## 代码架构

```
app.py                        # Streamlit 入口，会话管理 + 消息流
agent/
  react_agent.py              # 核心 Agent：LangGraph create_agent + 工具/中间件装配
  tools/
    agent_tools.py            # 7个工具定义：rag_summarize, get_weather, get_user_location,
                              #   get_user_ID, get_current_month, fetch_external_data,
                              #   fill_context_for_report
    middleware.py              # 4个中间件：工具调用监控/日志/报告提示词切换
model/
  factory.py                  # ChatTongyi + DashScopeEmbeddings 工厂
rag/
  rag_service.py              # RAG 总结链（检索 → Prompt → LLM → 输出）
  vector_store.py             # ChromaDB 管理：建库、文档分片、加载、MD5去重
config/
  agent.yml                   # 外部数据文件路径
  chroma.yml                  # 向量库参数（collection名、chunk_size、k等）
  prompt.yml                  # 提示词文件路径
  rag.yml                     # 模型名称配置
prompts/
  main_prompt.txt             # 主系统提示词（ReAct规则 + 工具说明）
  rag_summarize.txt           # RAG总结提示词
  report_prompt.txt           # 报告生成提示词
utils/
  config_handler.py           # YAML配置加载（模块级单例）
  path.py                     # 项目根路径工具
  file_handler.py             # MD5计算、文件加载（txt/pdf）
  prompt_loader.py            # 提示词文件读取
  logger_handler.py           # 日志配置（控制台+文件）
data/external/records.csv     # 用户使用记录外部数据源
```

## 关键设计

- **ReAct Agent**: 使用 LangGraph 的 `create_agent` 构建，遵循"思考→行动→观察→再思考"循环
- **报告生成流程**: fill_context_for_report → fetch_external_data → 中间件切换至 report_prompt
- **中间件驱动提示词切换**: `report_prompt_switch` 拦截 ModelRequest，根据 context["report"] 标志切换 main/report 提示词
- **RAG 去重**: 基于文件 MD5 记录在 `md5.txt`，避免重复加载知识库文档
- **配置优于硬编码**: 所有可调参数通过 YAML 管理（模型名、向量库参数、提示词路径等）
- **跨平台路径**: `utils/path.py` 统一通过 `get_abs_path()` 解析相对于项目根目录的路径

## 配置项

| 文件 | 关键配置 |
|------|---------|
| config/rag.yml | chat_model_name, embedding_model_name |
| config/chroma.yml | collection_name, persist_directory, k, chunk_size, chunk_overlap |
| config/prompt.yml | main_prompt_path, rag_summarize_prompt_path, report_prompt_path |
| config/agent.yml | external_data_path |

## 工具集

所有工具定义在 `agent/tools/agent_tools.py`，分为两类：
1. **信息查询**: rag_summarize（RAG检索）、get_weather（天气）、get_user_location（城市）、get_user_ID（用户ID）、get_current_month（月份）、fetch_external_data（外部记录）
2. **流程触发**: fill_context_for_report（触发提示词切换中间件）

## 日志

日志默认输出到 `logs/` 目录，文件名格式 `agent_YYYYMMDD.log`。日志级别：控制台 INFO，文件 DEBUG。
