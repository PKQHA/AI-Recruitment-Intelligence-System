"""
LLM-driven learning roadmap Tool.

Each missing skill is sent to the language model as an independent planning
task with JD, resume, gap position, and RAG context. The code only validates and
maps the structured response; it does not fill fixed learning templates.
"""

from __future__ import annotations

import json
from typing import Any, List

from pydantic import ValidationError

from models.v2_models import (
    KnowledgeDocument,
    LearningPlanResponse,
    LearningRoadmapStep,
    RoadmapItem,
    RoadmapResponse,
)
from services.learning_advisor import LearningAdvisor
from tools.base_tool import BaseTool, ToolResult
from utils.text import normalize_skill_name, unique_preserve_order


class LearningRoadmapTool(BaseTool):
    """Generate personalized learning strategy steps with the LLM."""

    name = "learning_roadmap"
    description = "Generate a personalized LLM-driven roadmap from missing skills."

    def __init__(self, learning_advisor: LearningAdvisor) -> None:
        self._learning_advisor = learning_advisor
        self._client_wrapper = learning_advisor._client_wrapper

    def run(self, **kwargs: Any) -> ToolResult:
        matched_skills = _clean_skill_list(kwargs.get("matched_skills", []))
        missing_skills = _clean_skill_list(kwargs.get("missing_skills", []))
        knowledge_documents = kwargs.get("knowledge_documents", [])
        jd_text = str(kwargs.get("jd_text", ""))
        resume_text = str(kwargs.get("resume_text", ""))

        suggestions, roadmap = self._build_learning_plan(
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            knowledge_documents=knowledge_documents,
            jd_text=jd_text,
            resume_text=resume_text,
        )

        return ToolResult(
            data={"suggestions": suggestions, "roadmap": roadmap},
            message="学习建议与学习路线生成完成。",
        )

    def _build_learning_plan(
        self,
        matched_skills: List[str],
        missing_skills: List[str],
        knowledge_documents: List[KnowledgeDocument],
        jd_text: str,
        resume_text: str,
    ) -> tuple[List[str], List[LearningRoadmapStep]]:
        gap_skills = _clean_skill_list(missing_skills)
        if not gap_skills:
            suggestions = self._learning_advisor.generate_advice(
                matched_skills=matched_skills,
                missing_skills=gap_skills,
            )
            return suggestions, []

        context_by_skill = _build_context_by_skill(gap_skills, knowledge_documents)
        learning_plan = self._generate_plan_with_llm(
            matched_skills=matched_skills,
            missing_skills=gap_skills,
            jd_text=jd_text,
            resume_text=resume_text,
            rag_context=_format_context_by_skill(gap_skills, context_by_skill),
        )
        suggestions = _sanitize_suggestions(learning_plan.suggestions)
        roadmap = _build_steps_from_response(
            RoadmapResponse(roadmap=learning_plan.roadmap),
            allowed_skills=gap_skills,
        )
        return suggestions, _filter_roadmap_by_gap(roadmap, gap_skills)

    def _generate_plan_with_llm(
        self,
        matched_skills: List[str],
        missing_skills: List[str],
        jd_text: str,
        resume_text: str,
        rag_context: str,
    ) -> LearningPlanResponse:
        prompt = _build_plan_prompt(
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            jd_text=jd_text,
            resume_text=resume_text,
            rag_context=rag_context,
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "你是资深职业发展教练和招聘技术面试官。"
                    "你必须基于输入上下文为所有缺失技能生成学习建议和学习路线，"
                    "只能返回符合 schema 的合法 JSON，不要输出 Markdown。"
                    "顶层必须包含 suggestions 和 roadmap。"
                ),
            },
            {"role": "user", "content": prompt},
        ]

        response_format = _build_response_format(self._client_wrapper, LearningPlanResponse)
        response_text = self._client_wrapper.chat(
            messages=messages,
            temperature=0.45,
            response_format=response_format,
        )
        return _parse_learning_plan_response(response_text)


def _build_plan_prompt(
    matched_skills: List[str],
    missing_skills: List[str],
    jd_text: str,
    resume_text: str,
    rag_context: str,
) -> str:
    missing_skill_lines = "\n".join(
        f"{index}. {skill}" for index, skill in enumerate(missing_skills, start=1)
    )
    return f"""
请为当前候选人的所有缺失技能生成完整学习建议和学习路线。

岗位 JD 上下文：
{jd_text}

候选人简历上下文：
{resume_text}

已匹配技能：
{"、".join(matched_skills) or "暂无"}

缺失技能：
{missing_skill_lines}

可参考知识片段：
{rag_context or "无"}

要求：
1. suggestions 生成 3 到 5 条中文学习建议。
2. roadmap 必须覆盖每一个缺失技能，每个缺失技能至少一个阶段。
3. 每个阶段必须解释为什么该技能对这个 JD 重要。
4. 每个阶段必须结合候选人简历背景，指出最适合的学习切入点。
5. 每个阶段必须给出岗位相关实战项目建议和简历表达方式。
6. 不允许套用固定模板；不同技能的内容必须语义不同。
7. 不要扩展缺失技能列表之外的技能。

请严格返回 JSON：
{{
  "suggestions": ["建议1", "建议2", "建议3"],
  "roadmap": [
    {{
      "phase": "阶段标题",
      "target_skill": "缺失技能名称",
      "reason": "为什么要学这个技能",
      "goal": "个性化学习目标",
      "learning_path": ["学习步骤1", "学习步骤2", "学习步骤3"],
      "practice_task": "结合岗位场景的实战项目建议",
      "project_idea": "可写进作品集或简历的项目想法",
      "resume_tip": "结合JD的简历表达建议"
    }}
  ]
}}
""".strip()


def _build_response_format(client_wrapper: Any, schema_model: Any) -> dict[str, Any]:
    if client_wrapper.supports_json_schema_response_format():
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "learning_plan_response",
                "strict": True,
                "schema": _model_json_schema(schema_model),
            },
        }

    return {"type": "json_object"}


def _model_json_schema(schema_model: Any) -> dict[str, Any]:
    if hasattr(schema_model, "model_json_schema"):
        return schema_model.model_json_schema()
    return schema_model.schema()


def _parse_learning_plan_response(response_text: str) -> LearningPlanResponse:
    parsed_result = _parse_json_with_debug(response_text)
    normalized_result = _normalize_learning_plan_payload(parsed_result)
    try:
        return _validate_learning_plan_response(normalized_result)
    except ValidationError as error:
        print("validation_error:")
        print(error)
        raise ValueError(
            "学习规划 LLM 输出未通过 Schema 校验。"
            f"\n原始返回内容：{response_text}"
            f"\nparsed_result：{parsed_result}"
            f"\nvalidation_error：{error}"
        ) from error


def _parse_roadmap_response(response_text: str) -> RoadmapResponse:
    parsed_result = _parse_json_with_debug(response_text)
    normalized_result = _normalize_roadmap_payload(parsed_result)
    try:
        return _validate_roadmap_response(normalized_result)
    except ValidationError as error:
        print("validation_error:")
        print(error)
        raise ValueError(
            "学习路线 LLM 输出未通过 Schema 校验。"
            f"\n原始返回内容：{response_text}"
            f"\nparsed_result：{parsed_result}"
            f"\nvalidation_error：{error}"
        ) from error


def _parse_json_with_debug(response_text: str) -> Any:
    print("LLM Raw Output:")
    print(response_text)

    cleaned_text = _clean_json_text(response_text)
    try:
        parsed_result = json.loads(cleaned_text)
    except json.JSONDecodeError as error:
        print("JSON parse error:")
        print(error)
        raise ValueError(
            "学习路线 LLM 输出不是合法 JSON。"
            f"\n原始返回内容：{response_text}"
            f"\nJSON解析错误：{error}"
        ) from error

    print(f"type(parsed_result): {type(parsed_result)}")
    print("parsed_result:")
    print(parsed_result)
    return parsed_result


def _clean_json_text(response_text: str) -> str:
    return response_text.replace("```json", "").replace("```JSON", "").replace("```", "").strip()


def _normalize_roadmap_payload(parsed_result: Any) -> dict[str, Any]:
    if isinstance(parsed_result, dict) and isinstance(parsed_result.get("roadmap"), list):
        return parsed_result

    if isinstance(parsed_result, list):
        return {"roadmap": parsed_result}

    if isinstance(parsed_result, dict):
        return {"roadmap": [parsed_result]}

    raise ValueError(
        "学习路线 LLM 输出必须是 JSON object 或 JSON array。"
        f"\nparsed_result：{parsed_result}"
    )


def _normalize_learning_plan_payload(parsed_result: Any) -> dict[str, Any]:
    if isinstance(parsed_result, dict) and isinstance(parsed_result.get("roadmap"), list):
        suggestions = parsed_result.get("suggestions", [])
        if not isinstance(suggestions, list):
            suggestions = []
        return {"suggestions": suggestions, "roadmap": parsed_result["roadmap"]}

    normalized_roadmap = _normalize_roadmap_payload(parsed_result)
    return {"suggestions": [], "roadmap": normalized_roadmap["roadmap"]}


def _validate_learning_plan_response(payload: dict[str, Any]) -> LearningPlanResponse:
    if hasattr(LearningPlanResponse, "model_validate"):
        return LearningPlanResponse.model_validate(payload)
    return LearningPlanResponse.parse_obj(payload)


def _validate_roadmap_response(payload: dict[str, Any]) -> RoadmapResponse:
    if hasattr(RoadmapResponse, "model_validate"):
        return RoadmapResponse.model_validate(payload)
    return RoadmapResponse.parse_obj(payload)


def _build_steps_from_response(
    response: RoadmapResponse,
    allowed_skills: List[str],
) -> List[LearningRoadmapStep]:
    if not response.roadmap:
        raise ValueError("学习路线 LLM 输出的 roadmap 不能为空。")

    allowed_skill_names = {normalize_skill_name(skill) for skill in allowed_skills}
    invalid_skills = [
        item.target_skill
        for item in response.roadmap
        if normalize_skill_name(item.target_skill) not in allowed_skill_names
    ]
    if invalid_skills:
        raise ValueError(
            "学习路线 LLM 输出包含缺失技能列表之外的 target_skill："
            f"{', '.join(invalid_skills)}"
        )

    return [
        _build_step_from_item(item=item, index=index)
        for index, item in enumerate(response.roadmap, start=1)
    ]


def _sanitize_suggestions(suggestions: Any) -> List[str]:
    if not isinstance(suggestions, list):
        return []
    return unique_preserve_order(
        str(item).strip(" -•\t\r\n")
        for item in suggestions
        if str(item).strip(" -•\t\r\n")
    )


def _format_context_by_skill(
    gap_skills: List[str],
    context_by_skill: dict[str, str],
) -> str:
    sections = [
        f"## {skill}\n{context_by_skill.get(normalize_skill_name(skill), '无') or '无'}"
        for skill in gap_skills
    ]
    return "\n\n".join(sections)


def _build_step_from_item(
    item: RoadmapItem,
    index: int,
) -> LearningRoadmapStep:
    target_skill = item.target_skill.strip()

    required_fields = ["phase", "reason", "goal", "practice_task", "project_idea", "resume_tip"]
    missing_fields = [field for field in required_fields if not getattr(item, field).strip()]
    if missing_fields:
        raise ValueError(f"学习路线 LLM 输出缺少字段：{', '.join(missing_fields)}")

    return LearningRoadmapStep(
        phase=item.phase.strip() or f"阶段 {index}：{target_skill}",
        target_skill=target_skill,
        reason=item.reason.strip(),
        goal=item.goal.strip(),
        learning_path=[path.strip() for path in item.learning_path if path.strip()],
        practice_task=item.practice_task.strip(),
        project_idea=item.project_idea.strip(),
        resume_tip=item.resume_tip.strip(),
    )


def _clean_skill_list(skills: Any) -> List[str]:
    if not isinstance(skills, list):
        return []

    cleaned = [
        str(skill).strip(" -•\t\r\n")
        for skill in skills
        if str(skill).strip(" -•\t\r\n")
    ]
    return unique_preserve_order(cleaned)


def _build_context_by_skill(
    gap_skills: List[str],
    knowledge_documents: List[KnowledgeDocument],
) -> dict[str, str]:
    contexts = {normalize_skill_name(skill): "" for skill in gap_skills}

    for document in knowledge_documents:
        content = getattr(document, "content", "")
        title = getattr(document, "title", "")
        combined_text = f"{title}\n{content}".strip()
        normalized_text = normalize_skill_name(combined_text)

        for skill in gap_skills:
            normalized_skill = normalize_skill_name(skill)
            if normalized_skill and normalized_skill in normalized_text:
                contexts[normalized_skill] = combined_text

    return contexts


def _filter_roadmap_by_gap(
    roadmap: List[LearningRoadmapStep],
    gap_skills: List[str],
) -> List[LearningRoadmapStep]:
    allowed_skills = {normalize_skill_name(skill) for skill in gap_skills}
    return [
        step
        for step in roadmap
        if normalize_skill_name(step.target_skill) in allowed_skills
    ]
