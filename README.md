# AI 招聘分析 Agent V1

这是一个基于 Python 和 OpenAI SDK 的终端版招聘分析 Agent。

用户输入岗位 JD 和个人简历后，系统会自动完成：

1. 提取 JD 中的技能关键词
2. 提取简历中的技能关键词
3. 计算技能匹配度
4. 输出匹配率
5. 输出匹配技能
6. 输出缺失技能
7. 生成学习建议

## 项目结构

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
├─ examples/
│  ├─ sample_jd.txt
│  └─ sample_resume.txt
├─ models/
│  ├─ __init__.py
│  └─ analysis_models.py
├─ prompts/
│  ├─ jd_prompt.txt
│  ├─ learning_advice_prompt.txt
│  └─ resume_prompt.txt
├─ services/
│  ├─ __init__.py
│  ├─ learning_advisor.py
│  ├─ matcher.py
│  └─ skill_extractor.py
├─ utils/
│  ├─ __init__.py
│  ├─ console.py
│  ├─ prompt_loader.py
│  └─ text.py
├─ skills/
│  └─ resume_skill.py
├─ .env.example
├─ config.py
├─ main.py
└─ requirements.txt
```

## 安装步骤

```bash
pip install -r requirements.txt
```

## 环境变量配置

1. 将 `.env.example` 复制为 `.env`
2. 填写以下内容：

```env
OPENAI_API_KEY=你的_API_Key
OPENAI_MODEL=gpt-4.1-mini
OPENAI_BASE_URL=
```

如果你使用的是兼容 OpenAI SDK 的其他模型网关，也可以继续沿用：

```env
QWEN_API_KEY=你的_Key
QWEN_BASE_URL=你的_Base_URL
QWEN_MODEL=qwen-plus
```

## 运行方式

### 方式一：通过示例文件运行

```bash
python main.py --jd-file examples/sample_jd.txt --resume-file examples/sample_resume.txt
```

### 方式二：终端直接粘贴文本

```bash
python main.py
```

程序会提示你分别输入岗位 JD 和个人简历，输入 `END` 单独一行结束。

## 输出示例

- JD 技能关键词
- 简历技能关键词
- 技能匹配率
- 已匹配技能
- 缺失技能
- 学习建议

## 设计说明

- 使用面向对象设计，便于后续扩展为 Web API、前端应用或多 Agent 架构。
- 技能提取和学习建议依赖 LLM。
- 匹配率计算采用确定性逻辑，便于结果稳定可解释。
- 当前版本为 V1，仅支持终端运行，不包含前端和数据库。
