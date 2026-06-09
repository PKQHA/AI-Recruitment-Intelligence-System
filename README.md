---
title: Resume Analyzer API
emoji: 📋
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# AI Recruitment Analysis Agent

一个面向招聘与求职场景的 AI 简历分析系统。用户上传简历并输入岗位 JD 后，系统会自动提取双方技能关键词，计算岗位匹配度，输出已匹配技能、待补齐技能、AI 学习建议和阶段化学习路线。

项目包含三种入口：

- **Streamlit 前端**：`streamlit_app.py` 转发到 `career_agent/frontend/app.py`，适合部署到 Streamlit Community Cloud。
- **FastAPI 后端**：`career_agent/backend/main.py`，适合部署到 Hugging Face Docker Space。
- **CLI 入口**：`career_agent/main.py`、`career_agent/main_v2.py`，适合本地调试 Agent 流程。

## 功能特性

- JD 与简历技能关键词提取
- 技能匹配率、已匹配技能、缺失技能分析
- 基于 LLM 的学习建议与个性化学习路线生成
- 基于 LangGraph 的 V2 工作流编排
- 基于 FAISS 的技能知识库 RAG 检索增强
- FastAPI 后端接口，支持同步分析与异步任务轮询
- Streamlit Web 前端
- 邀请码访问控制与使用次数限制
- 支持文本型 PDF 简历解析
- 支持图片简历 OCR 解析，Docker 镜像内已安装 Tesseract OCR 与中文语言包

## 架构说明

```text
Browser
  |
  | Streamlit UI
  v
streamlit_app.py
  |
  v
career_agent/frontend/app.py
  |
  | HTTP multipart/form-data
  v
FastAPI backend: career_agent/backend/main.py
  |
  | create job / poll progress
  v
V2Agent facade: career_agent/core/v2_agent.py
  |
  v
LangGraph workflow: career_agent/workflows/recruitment_workflow.py
  |
  +-- SkillExtractor -> OpenAI-compatible Chat API
  +-- SkillMatcher -> local deterministic matching
  +-- SkillKnowledgeSearchTool -> FAISS + Embedding RAG
  +-- LearningRoadmapTool -> OpenAI-compatible Chat API + JSON schema validation
  |
  v
Analysis result: match rate, skills, recommendation, roadmap
```

核心分层如下：

- `career_agent/frontend/`：Streamlit 页面、邀请码弹窗、文件上传、任务进度展示、分析结果渲染。
- `career_agent/backend/`：FastAPI 接口层，负责参数校验、简历解析、邀请码校验、异步任务管理和错误返回。
- `career_agent/core/`：V2 Agent 门面，组装 Settings、LLM Client、RAG、Tools 和 LangGraph 工作流。
- `career_agent/workflows/`：LangGraph 状态图，目前是线性五节点流程：提取技能 -> 匹配技能 -> 检索知识 -> 生成路线 -> 组装报告。
- `career_agent/services/`：技能提取、匹配、学习建议、简历解析、邀请码 SQLite 存储等业务服务。
- `career_agent/tools/`：工作流调用的工具层。当前是本地 ToolRegistry，不依赖模型原生 function calling。
- `career_agent/rag/`：Markdown 知识库加载、Embedding 适配、FAISS 索引构建与相似度检索。
- `career_agent/prompts/`：JD 技能提取、简历技能提取、学习建议等 Prompt 模板。
- `career_agent/data/skill_knowledge.md`：技能知识库原始内容。

## 关键 Prompt 与 Vibe 思路

本项目的 Prompt 设计目标不是让模型“自由发挥”，而是让模型在招聘分析场景中保持稳定、可解释、可校验。

### JD 技能提取 Prompt

文件：`career_agent/prompts/jd_prompt.txt`

思路：

- 让模型只关注岗位职责、任职要求和技能栈中的技能关键词。
- 输出结构化 JSON，核心字段为 `skills`。
- 尽量抽取标准化技能名，避免输出长句、评价性描述或无关软技能。

### 简历技能提取 Prompt

文件：`career_agent/prompts/resume_prompt.txt`

思路：

- 从项目经历、技能清单、工作经历中识别候选人已经具备的技能。
- 将自然语言经历压缩为可匹配的技能关键词。
- 和 JD 提取保持相同输出契约，便于后续做集合匹配。

### 学习建议与路线 Prompt

文件：`career_agent/prompts/learning_advice_prompt.txt`

另一个更强的路线生成 Prompt 在 `career_agent/tools/roadmap_tool.py` 中动态构造。

思路：

- 输入已匹配技能、缺失技能、JD 原文、简历原文和 RAG 检索片段。
- 要求模型围绕每个缺失技能生成具体学习阶段、学习目标、练习任务、项目建议和简历表达建议。
- 不允许扩展到缺失技能列表之外，避免模型把报告写散。
- 对支持 `json_schema` 的模型使用严格 schema；对兼容网关退化为 `json_object`，再用 Pydantic 校验。

### Vibe 思路

这个项目的 Vibe 是“招聘技术面试官 + 职业发展教练”：

- **面试官视角**：先判断 JD 需要什么、候选人有什么、差距在哪里。
- **教练视角**：差距不只列清单，还要转化成能执行的学习路线和项目补强建议。
- **产品视角**：前端用进度条和阶段状态降低等待焦虑；邀请码机制方便小范围 Demo；后端异步任务避免长时间请求阻塞。
- **工程视角**：LLM 负责语义抽取与建议生成，匹配率、邀请码扣减、任务状态等关键逻辑尽量放在确定性代码中。

## AI 调用逻辑

### 模型与供应商

项目通过 OpenAI SDK 兼容接口调用模型，默认适配 DashScope/Qwen：

- Chat model 默认：`qwen-plus`
- Embedding model 默认：`text-embedding-v4`
- Base URL 默认：`https://dashscope.aliyuncs.com/compatible-mode/v1`

也可以使用 OpenAI 或其他 OpenAI-compatible 网关。相关配置在 `career_agent/core/settings.py`。

### Chat Completion

主要调用位置：

- `SkillExtractor`：分别从 JD 和简历中提取技能。
- `LearningAdvisor`：生成学习建议。
- `LearningRoadmapTool`：生成完整学习路线。

调用特点：

- 技能抽取温度较低，偏稳定。
- 学习路线温度略高，保留个性化表达。
- 输出优先要求 JSON。
- 统一做 JSON 清洗、解析、去重和 Pydantic schema 校验。

### Embedding 与 RAG

RAG 链路：

1. `KnowledgeLoader` 读取 `career_agent/data/skill_knowledge.md`。
2. `OpenAIEmbeddingAdapter` 调用 Embedding API。
3. `FaissSkillStore` 构建或加载本地 FAISS 索引。
4. `SkillKnowledgeSearchTool` 根据缺失技能检索相关知识片段。
5. `LearningRoadmapTool` 将 RAG 上下文注入学习路线 Prompt。

Embedding 请求会按批次拆分，避免部分供应商对单次 input 数量有限制。

### 异步任务与“流式”体验

当前后端没有使用 SSE/WebSocket/token streaming，也没有把模型 token 实时推到前端。

项目采用的是 **异步 job + 轮询进度**：

1. 前端调用 `POST /analyze/jobs` 创建任务。
2. 后端启动后台线程执行简历解析与 Agent 工作流。
3. LangGraph 节点执行时通过 `progress_callback` 更新 `current_step` 和 `progress`。
4. 前端每 1.5 秒调用 `GET /analyze/jobs/{job_id}` 查询状态。
5. 任务完成后返回完整分析结果。

这种方式实现简单，适合 Streamlit 与 Hugging Face Space 的部署环境。后续如果需要真正的 token 级流式输出，可以把后端扩展为 SSE 接口，并在模型调用层开启 streaming。

### Function Calling 说明

当前项目没有使用模型原生 function calling。工作流中的 `SkillMatchTool`、`SkillKnowledgeSearchTool`、`LearningRoadmapTool` 是代码侧 ToolRegistry 调度的本地工具：

- 模型不决定调用哪个工具。
- LangGraph 节点按固定顺序调用工具。
- 工具输入输出由 Python 类型和 Pydantic 模型约束。

这样做的好处是流程更稳定，适合 Demo 和课程项目展示。后续也可以将 ToolRegistry 改造成模型可调用函数，让 Agent 根据上下文自主选择工具。

## API 概览

后端启动后可访问：

- `GET /health`：健康检查
- `GET /`：服务信息
- `POST /verify-code`：验证邀请码
- `GET /quota`：查询邀请码剩余额度
- `POST /consume-code`：扣减邀请码额度
- `POST /analyze`：同步分析接口
- `POST /analyze/jobs`：创建异步分析任务
- `GET /analyze/jobs/{job_id}`：查询异步任务进度与结果
- `GET /docs`：FastAPI Swagger 文档

## 本地运行

### 1. 创建虚拟环境

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r .\career_agent\requirements.txt
```

macOS/Linux：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r ./career_agent/requirements.txt
```

### 2. 配置环境变量

复制示例配置：

```powershell
Copy-Item .\career_agent\.env.example .\career_agent\.env
```

填写 `career_agent/.env`：

```env
DASHSCOPE_API_KEY=your-dashscope-api-key
DASHSCOPE_MODEL=qwen-plus
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4

INVITE_CODES=DEMO123,DEMO456
INVITE_CODE_MAX_USES=2
INVITE_DEV_CODE=your-dev-code

CAREER_AGENT_ANALYZE_TIMEOUT=600
```

如果使用 OpenAI：

```env
OPENAI_API_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

注意：不要把真实 `.env`、API Key、邀请码或 SQLite 数据库提交到 GitHub。

### 3. 启动后端

```powershell
cd .\career_agent
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

健康检查：

```text
http://127.0.0.1:8000/health
```

### 4. 启动前端

当前前端 API 地址在 `career_agent/config.py` 中：

```python
API_BASE_URL = "https://pkqha-tool.hf.space"
```

本地调试时改成：

```python
API_BASE_URL = "http://127.0.0.1:8000"
```

然后在仓库根目录运行：

```powershell
streamlit run streamlit_app.py
```

也可以直接运行：

```powershell
streamlit run .\career_agent\frontend\app.py
```

### 5. CLI 调试

```powershell
cd .\career_agent
python .\main_v2.py --jd-file .\examples\sample_jd.txt --resume-file .\examples\sample_resume.txt --rebuild-index
```

## 部署步骤

目标部署方式：

- 前端：Streamlit Community Cloud
- 后端：Hugging Face Docker Space

### A. 后端部署到 Hugging Face Docker Space

1. 在 Hugging Face 创建一个新的 Space。
2. SDK 选择 **Docker**。
3. 将本仓库代码推送到该 Space，或将 GitHub 仓库连接到 Space。
4. 确认仓库根目录包含：

```text
Dockerfile
README.md
career_agent/
```

5. 确认 `README.md` 顶部 YAML 包含：

```yaml
---
sdk: docker
app_port: 7860
---
```

6. `Dockerfile` 当前会：

- 使用 `python:3.11-slim`
- 安装 `tesseract-ocr` 和 `tesseract-ocr-chi-sim`
- 安装 `career_agent/requirements.txt`
- 暴露 `7860`
- 启动 `uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}`

7. 在 Hugging Face Space 的 **Settings -> Variables and secrets** 中配置：

```env
DASHSCOPE_API_KEY=your-dashscope-api-key
DASHSCOPE_MODEL=qwen-plus
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4
INVITE_CODES=DEMO123,DEMO456
INVITE_CODE_MAX_USES=2
INVITE_DEV_CODE=your-private-admin-code
```

8. 等待 Space Build 完成，访问：

```text
https://<your-space-name>.hf.space/health
https://<your-space-name>.hf.space/docs
```

Hugging Face Docker Space 会根据 `app_port: 7860` 将外部 HTTPS 流量转发到容器内的 7860 端口。应用内部只需要监听 `0.0.0.0:7860`。

### B. 前端部署到 Streamlit Community Cloud

1. 将项目上传到 GitHub。
2. 登录 Streamlit Community Cloud。
3. 点击 **Create app**，选择你的 GitHub 仓库、分支和入口文件：

```text
streamlit_app.py
```

4. 设置 Python 版本为 3.11 或与本地一致的版本。
5. 在 Streamlit 的 Secrets 中配置前端需要的变量，例如：

```toml
CAREER_AGENT_ANALYZE_TIMEOUT = "600"
```

6. 重要：将 `career_agent/config.py` 中的后端地址改成你的 Hugging Face Space 地址：

```python
API_BASE_URL = "https://<your-space-name>.hf.space"
```

7. 部署完成后访问：

```text
https://<your-streamlit-app>.streamlit.app
```

Streamlit Community Cloud 会自动提供 `*.streamlit.app` 的 HTTPS 地址。项目中的 API 请求必须使用 HTTPS 后端地址，否则浏览器可能因为 mixed content 阻止请求。

### C. DNS 与 HTTPS 说明

#### 后端 Hugging Face Space

默认后端地址：

```text
https://<space-owner>-<space-name>.hf.space
```

如果需要绑定自定义域名：

1. Hugging Face Space 自定义域名功能需要符合 Hugging Face 当前账号权限要求。
2. 在 Space Settings 的 **Custom Domain** 中填写你的域名，例如：

```text
api.example.com
```

3. 到 DNS 服务商添加 CNAME：

```text
api.example.com  CNAME  hf.space
```

4. 等待 DNS 生效，Hugging Face 状态变为 ready。
5. 前端 `API_BASE_URL` 改为：

```python
API_BASE_URL = "https://api.example.com"
```

HTTPS 证书由 Hugging Face 托管层处理，应用容器里不需要自己配置证书。

#### 前端 Streamlit

默认前端地址：

```text
https://<your-app>.streamlit.app
```

Streamlit Community Cloud 支持设置自定义 `streamlit.app` 子域名。进入应用设置后可以修改 App URL，例如：

```text
https://resume-agent.streamlit.app
```

Streamlit Community Cloud 默认提供 HTTPS。若需要完全自有域名，例如 `www.example.com`，通常需要额外的反向代理、跳转页或其他托管平台配合；是否原生支持完整自定义域名请以 Streamlit 官方控制台当前能力为准。

## GitHub 上传建议

建议上传前检查：

```powershell
git status
```



## 参考文档

- [Streamlit Community Cloud 部署文档](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Streamlit 应用设置与自定义子域名](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/app-settings)
- [Hugging Face Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker)
- [Hugging Face Spaces Custom Domain](https://huggingface.co/docs/hub/main/en/spaces-custom-domain)

## 许可证

当前项目尚未声明许可证。若准备作为开源项目发布，建议在 GitHub 上传前补充合适的 `LICENSE` 文件。
