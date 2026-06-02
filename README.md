<<<<<<< HEAD
---
title: Resume Analyzer API
emoji: 📄
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# AI Recruitment Analysis Agent

=======
AI Recruitment Analysis Agent
>>>>>>> 934a821fd076301fa3bec6156c3dcb9123a80202
一个面向招聘场景的 AI 分析工具。项目可以根据岗位 JD 和候选人简历提取技能关键词，计算岗位匹配度，输出缺失技能、学习建议和阶段化学习路线。

项目包含命令行版本、FastAPI 后端和 Streamlit 前端，适合本地演示、原型验证或继续扩展成招聘分析产品。

<<<<<<< HEAD
## 功能特性

- JD 与简历技能关键词提取
- 技能匹配率、已匹配技能、缺失技能分析
- 基于 LLM 的学习建议生成
- 基于 LangGraph 的 V2 工作流编排
- 基于 FAISS 的技能知识库检索增强
- FastAPI 接口，支持异步任务进度查询
- Streamlit Web 前端
- 邀请码访问控制与使用次数限制
- 支持文本型 PDF 简历解析
- 支持图片简历 OCR 解析，需本机安装 Tesseract OCR

## 项目结构

```text
=======
点击start.bat，可以启动前后端

功能特性
JD 与简历技能关键词提取
技能匹配率、已匹配技能、缺失技能分析
基于 LLM 的学习建议生成
基于 LangGraph 的 V2 工作流编排
基于 FAISS 的技能知识库检索增强
FastAPI 接口，支持异步任务进度查询
Streamlit Web 前端
邀请码访问控制与使用次数限制
支持文本型 PDF 简历解析
支持图片简历 OCR 解析，需本机安装 Tesseract OCR
项目结构
>>>>>>> 934a821fd076301fa3bec6156c3dcb9123a80202
.
├─ career_agent/
│  ├─ agents/              # V1 Agent 组合逻辑
│  ├─ backend/             # FastAPI 后端
│  ├─ clients/             # OpenAI SDK 客户端封装
│  ├─ core/                # 配置与 V2 Agent 入口
│  ├─ data/                # 技能知识库等本地数据
│  ├─ docs/                # 项目文档
│  ├─ examples/            # 示例 JD 和简历文本
│  ├─ frontend/            # Streamlit 前端
│  ├─ models/              # 数据模型
│  ├─ prompts/             # 提示词模板
│  ├─ rag/                 # RAG、Embedding、FAISS 检索
│  ├─ services/            # 技能提取、匹配、简历解析等服务
│  ├─ tools/               # V2 工具注册与工具实现
│  ├─ workflows/           # LangGraph 工作流
│  ├─ main.py              # V1 CLI 入口
│  ├─ main_v2.py           # V2 CLI 入口
│  └─ requirements.txt
├─ .gitignore
└─ start.bat
<<<<<<< HEAD
=======
环境要求
Python 3.10+
可用的 OpenAI API Key，或兼容 OpenAI SDK 的模型服务
如需解析图片简历：本机安装 Tesseract OCR，并安装中文语言包
安装
建议在项目根目录创建虚拟环境：

python -m venv .venv
.\.venv\Scripts\activate
pip install -r .\career_agent\requirements.txt
也可以在 macOS/Linux 使用：

python -m venv .venv
source .venv/bin/activate
pip install -r ./career_agent/requirements.txt
配置
复制示例环境变量文件：

Copy-Item .\career_agent\.env.example .\career_agent\.env
填写 .env。不要把真实 .env、API Key、邀请码或本地数据库提交到仓库。

OPENAI_API_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_BASE_URL=

INVITE_CODES=
INVITE_CODE_MAX_USES=2
INVITE_DEV_CODE=

CAREER_AGENT_API_URL=http://127.0.0.1:8000/analyze
CAREER_AGENT_ANALYZE_TIMEOUT=600
如使用兼容 OpenAI SDK 的其他模型网关，可使用以下字段：

QWEN_API_KEY=
QWEN_BASE_URL=
QWEN_MODEL=qwen-plus
QWEN_EMBEDDING_MODEL=text-embedding-v4
命令行运行
进入应用目录：

cd .\career_agent

如果技能知识库内容有更新，可以重建 FAISS 索引：

python .\main_v2.py --jd-file .\examples\sample_jd.txt --resume-file .\examples\sample_resume.txt --rebuild-index



API 概览
GET /health：健康检查
POST /verify-code：验证邀请码
GET /quota：查询邀请码额度
POST /consume-code：扣减邀请码额度
POST /analyze：同步分析接口
POST /analyze/jobs：创建异步分析任务
GET /analyze/jobs/{job_id}：查询异步任务进度与结果

许可证
当前项目尚未声明许可证。如需开源发布，请先补充合适的 LICENSE 文件。
>>>>>>> 934a821fd076301fa3bec6156c3dcb9123a80202
