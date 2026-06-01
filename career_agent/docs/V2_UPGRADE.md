# AI 招聘分析 Agent V2 升级说明

## V2 新增能力

1. LangGraph 工作流：将招聘分析拆成多个节点编排执行。
2. Tool 调用机制：将技能匹配、知识检索、学习路线生成封装成工具。
3. 技能知识库 RAG：根据缺失技能检索外部知识片段。
4. FAISS 向量检索：本地构建和持久化技能知识库向量索引。
5. 自动生成学习路线：按缺失技能生成阶段化学习目标、练习任务和简历表达建议。
6. 项目结构优化：V1 保留，V2 作为增量入口与模块。

## 完整目录树

```text
career_agent/
├─ agents/
│  ├─ __init__.py
│  └─ recruitment_agent.py
├─ clients/
│  ├─ __init__.py
│  └─ openai_client.py
├─ core/
│  ├─ __init__.py
│  └─ settings.py
├─ data/
│  └─ skill_knowledge.md
├─ docs/
│  └─ V2_UPGRADE.md
├─ examples/
│  ├─ sample_jd.txt
│  └─ sample_resume.txt
├─ models/
│  ├─ __init__.py
│  ├─ analysis_models.py
│  └─ v2_models.py
├─ prompts/
│  ├─ jd_prompt.txt
│  ├─ learning_advice_prompt.txt
│  └─ resume_prompt.txt
├─ rag/
│  ├─ __init__.py
│  ├─ embedding_adapter.py
│  ├─ faiss_store.py
│  ├─ knowledge_loader.py
│  └─ skill_knowledge_base.py
├─ services/
│  ├─ __init__.py
│  ├─ learning_advisor.py
│  ├─ matcher.py
│  └─ skill_extractor.py
├─ skills/
│  └─ resume_skill.py
├─ tools/
│  ├─ __init__.py
│  ├─ base_tool.py
│  ├─ knowledge_tool.py
│  ├─ match_tool.py
│  ├─ roadmap_tool.py
│  └─ tool_registry.py
├─ utils/
│  ├─ __init__.py
│  ├─ console.py
│  ├─ console_v2.py
│  ├─ prompt_loader.py
│  └─ text.py
├─ workflows/
│  ├─ __init__.py
│  ├─ recruitment_workflow.py
│  └─ state.py
├─ .env
├─ .env.example
├─ config.py
├─ main.py
├─ main_v2.py
├─ README.md
└─ requirements.txt
```

## 新增依赖

```text
langgraph>=0.2.60
langchain-core>=0.3.0
langchain-community>=0.3.0
faiss-cpu>=1.8.0
```

## 运行步骤

```bash
cd C:\Users\L1529\Desktop\ai学习\mask\career_agent
pip install -r requirements.txt
python main_v2.py --jd-file examples/sample_jd.txt --resume-file examples/sample_resume.txt
```

知识库更新后重建索引：

```bash
python main_v2.py --jd-file examples/sample_jd.txt --resume-file examples/sample_resume.txt --rebuild-index
```

## 模块作用说明

- `main.py`：V1 入口，保留不变。
- `main_v2.py`：V2 入口，负责装配配置、LLM、RAG、Tools 和 LangGraph 工作流。
- `workflows/recruitment_workflow.py`：LangGraph 主流程，串联技能提取、匹配、检索、路线生成和报告组装。
- `workflows/state.py`：定义 LangGraph State，描述节点之间共享的数据结构。
- `tools/base_tool.py`：定义统一 Tool 抽象和 ToolResult。
- `tools/tool_registry.py`：统一注册和调用 Tool。
- `tools/match_tool.py`：封装技能匹配能力。
- `tools/knowledge_tool.py`：封装技能知识库检索能力。
- `tools/roadmap_tool.py`：封装学习建议和路线生成能力。
- `rag/knowledge_loader.py`：读取并切分 Markdown 技能知识库。
- `rag/embedding_adapter.py`：把项目 OpenAI 客户端适配为 FAISS 可用的 Embedding 接口。
- `rag/faiss_store.py`：构建、加载、保存和查询 FAISS 向量索引。
- `rag/skill_knowledge_base.py`：对上层提供简洁的知识库检索服务。
- `models/v2_models.py`：定义 V2 报告、知识片段和学习路线数据结构。
- `utils/console_v2.py`：负责打印 V2 分析结果。
- `data/skill_knowledge.md`：本地技能知识库，可持续扩展。
