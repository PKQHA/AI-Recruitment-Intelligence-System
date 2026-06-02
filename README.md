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

一个面向招聘场景的 AI 分析工具。项目可以根据岗位 JD 和候选人简历提取技能关键词，计算岗位匹配度，输出缺失技能、学习建议和阶段化学习路线。

项目包含命令行版本、FastAPI 后端和 Streamlit 前端，适合本地演示、原型验证或继续扩展成招聘分析产品。

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
