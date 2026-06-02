"""
Streamlit frontend for the V3 recruitment analysis product.
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager
from json import JSONDecodeError
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import API_BASE_URL, REQUEST_TIMEOUT_SECONDS

ANALYZE_TIMEOUT = int(os.getenv("CAREER_AGENT_ANALYZE_TIMEOUT", "600"))
POLL_INTERVAL_SECONDS = 1.5


def init_state() -> None:
    if "fingerprint" not in st.session_state:
        st.session_state.fingerprint = _get_or_create_fingerprint()
    if "invite_code" not in st.session_state:
        st.session_state.invite_code = ""
    if "invite_quota" not in st.session_state:
        st.session_state.invite_quota = None
    if "invite_verified" not in st.session_state:
        st.session_state.invite_verified = False
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "roadmap" not in st.session_state:
        st.session_state.roadmap = []
    if "analysis_error" not in st.session_state:
        st.session_state.analysis_error = ""


def call_analyze_api(jd_text: str, resume_file: Any) -> dict[str, Any]:
    files = {
        "resume_file": (
            resume_file.name,
            resume_file.getvalue(),
            resume_file.type or "application/octet-stream",
        )
    }
    response = requests.post(
        f"{API_BASE_URL}/analyze",
        data={"jd": jd_text},
        files=files,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    _raise_for_status(response, "提交分析请求失败")
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as error:
        raise ValueError(f"后端返回的不是合法 JSON：{response.text}") from error
    except JSONDecodeError as error:
        raise ValueError(f"后端返回的不是合法 JSON：{response.text}") from error


def start_analyze_job(jd_text: str, resume_file: Any) -> dict[str, Any]:
    files = {
        "resume_file": (
            resume_file.name,
            resume_file.getvalue(),
            resume_file.type or "application/octet-stream",
        )
    }
    response = requests.post(
        f"{API_BASE_URL}/analyze/jobs",
        data={
            "jd": jd_text,
            "invite_code": st.session_state.invite_code,
            "fingerprint": st.session_state.fingerprint,
        },
        files=files,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    _raise_for_status(response, "创建分析任务失败")
    return response.json()


def verify_invite_code(code: str) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}/verify-code",
        json={"code": code, "fingerprint": st.session_state.fingerprint},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    _raise_for_status(response, "邀请码验证失败")
    return response.json()


def get_quota() -> dict[str, Any]:
    response = requests.get(
        f"{API_BASE_URL}/quota",
        params={
            "code": st.session_state.invite_code,
            "fingerprint": st.session_state.fingerprint,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    _raise_for_status(response, "查询邀请码额度失败")
    return response.json()


def consume_invite_code(request_id: str) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}/consume-code",
        json={
            "code": st.session_state.invite_code,
            "fingerprint": st.session_state.fingerprint,
            "request_id": request_id,
            "result_status": "success",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    _raise_for_status(response, "扣减邀请码额度失败")
    return response.json()


def get_analyze_job(job_id: str) -> dict[str, Any]:
    response = requests.get(
        f"{API_BASE_URL}/analyze/jobs/{job_id}",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    _raise_for_status(response, "查询分析任务失败")
    return response.json()


def _raise_for_status(response: requests.Response, action: str) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        detail = response.text
        try:
            payload = response.json()
            detail = payload.get("detail", detail) if isinstance(payload, dict) else detail
        except ValueError:
            pass
        raise RuntimeError(f"{action}：{detail}") from error


def _friendly_request_error(error: requests.exceptions.RequestException) -> str:
    return (
        f"无法连接到 Hugging Face 后端服务：{API_BASE_URL}。"
        f"错误详情：{error}"
    )


def wait_for_analyze_result(job_id: str, progress_bar: Any, status_slot: Any) -> dict[str, Any]:
    deadline = time.time() + ANALYZE_TIMEOUT
    while time.time() < deadline:
        job = get_analyze_job(job_id)
        progress = int(job.get("progress", 0))
        current_step = job.get("current_step", "正在分析")
        progress_bar.progress(progress)
        status_slot.markdown(f"当前状态：{current_step}...")

        if job.get("status") == "done":
            progress_bar.progress(100)
            status_slot.markdown("当前状态：分析完成")
            result = job.get("result")
            if not isinstance(result, dict):
                raise ValueError(f"后端任务完成但未返回有效结果：{job}")
            return result

        if job.get("status") == "error":
            raise ValueError(f"后端分析失败：{job.get('error', '')}")

        time.sleep(POLL_INTERVAL_SECONDS)

    raise requests.Timeout(f"后端分析超过 {ANALYZE_TIMEOUT} 秒仍未返回。")


def _get_or_create_fingerprint() -> str:
    query_params = st.query_params
    fingerprint = query_params.get("fp", "")
    if not fingerprint:
        fingerprint = uuid4().hex
        st.query_params["fp"] = fingerprint
    return fingerprint


def _quota_label(quota: dict[str, Any] | None) -> str:
    if not quota:
        return "当前邀请码剩余次数：未验证"
    if quota.get("unlimited"):
        return "当前邀请码剩余次数：无限制"
    remaining = quota.get("remaining", 0)
    limit = quota.get("limit", 2)
    return f"当前邀请码剩余次数：{remaining}/{limit}"


def render_invite_gate() -> bool:
    if st.session_state.invite_verified and st.session_state.invite_code:
        try:
            st.session_state.invite_quota = get_quota()
        except (RuntimeError, requests.exceptions.RequestException):
            pass
        st.caption(_quota_label(st.session_state.invite_quota))
        return bool(st.session_state.invite_quota and st.session_state.invite_quota.get("valid"))

    _show_invite_dialog()
    st.info("请输入邀请码后使用 AI 招聘分析系统。")
    return False


@st.dialog("邀请码验证")
def _show_invite_dialog() -> None:
    code = st.text_input("邀请码", type="password", placeholder="请输入邀请码")
    if st.button("验证邀请码", type="primary", use_container_width=True):
        try:
            quota = verify_invite_code(code)
        except requests.exceptions.RequestException as error:
            st.error(_friendly_request_error(error))
            return
        except RuntimeError as error:
            st.error(str(error))
            return

        if quota.get("valid"):
            st.session_state.invite_code = code.strip()
            st.session_state.invite_quota = quota
            st.session_state.invite_verified = True
            st.success(_quota_label(quota))
            st.rerun()
        else:
            st.error("邀请码无效或次数已用尽。")


def render_result() -> None:
    result = st.session_state.analysis_result
    if not result:
        return

    st.divider()
    st.subheader("分析结果")
    st.metric("岗位匹配率", f"{result.get('match_rate', 0):.2f}%")

    skills_left, skills_right = st.columns(2)
    with skills_left:
        st.markdown("#### 已匹配技能")
        matched_skills = result.get("matched_skills", [])
        if matched_skills:
            st.markdown("、".join(matched_skills))
        else:
            st.info("暂未识别到已匹配技能。")

    with skills_right:
        st.markdown("#### 待补齐技能")
        missing_skills = result.get("missing_skills", [])
        if missing_skills:
            st.markdown("、".join(missing_skills))
        else:
            st.success("暂未发现明显技能缺口。")

    st.markdown("#### AI 建议")
    recommendations = result.get("recommendation", [])
    if recommendations:
        for index, item in enumerate(recommendations):
            st.markdown(f"- {item}")
    else:
        st.info("暂无建议。")

    render_roadmap()


def render_roadmap() -> None:
    st.markdown("#### 学习路线")
    roadmap = st.session_state.roadmap

    with stable_container("roadmap_container"):
        if not roadmap:
            st.info("暂无学习路线。")
            return

        for index, step in enumerate(roadmap):
            phase = step.get("phase") or f"阶段 {index + 1}"
            target_skill = step.get("target_skill", "")
            goal = step.get("goal", "")
            reason = step.get("reason", "")
            learning_path = step.get("learning_path", [])
            practice_task = step.get("practice_task", "")
            project_idea = step.get("project_idea", "")
            resume_tip = step.get("resume_tip", "")

            st.markdown(f"**阶段 {index + 1}: {phase}**")
            if target_skill:
                st.markdown(f"- 目标技能：{target_skill}")
            if reason:
                st.markdown(f"- 学习原因：{reason}")
            if goal:
                st.markdown(f"- 学习目标：{goal}")
            if learning_path:
                for path_index, item in enumerate(learning_path, start=1):
                    st.markdown(f"- 路径 {path_index}：{item}")
            if practice_task:
                st.markdown(f"- 练习任务：{practice_task}")
            if project_idea:
                st.markdown(f"- 项目建议：{project_idea}")
            if resume_tip:
                st.markdown(f"- 简历优化：{resume_tip}")


@contextmanager
def stable_container(key: str):
    try:
        with st.container(key=key):
            yield
    except TypeError:
        with st.container():
            yield


init_state()

st.set_page_config(page_title="AI 招聘分析 V3", layout="wide")
st.title("AI 招聘分析 V3")
st.caption("上传 PDF 或图片简历，输入岗位 JD，生成匹配分析与学习建议。")

has_access = render_invite_gate()

left, right = st.columns([1, 1])
with left:
    jd_text = st.text_area(
        "岗位描述 JD",
        height=320,
        placeholder="请输入岗位职责、任职要求、技能栈等信息",
        disabled=not has_access,
    )
with right:
    resume_file = st.file_uploader(
        "上传简历文件",
        type=["pdf", "png", "jpg", "jpeg", "webp"],
        help="支持文本型 PDF；图片简历需要本机安装 OCR 依赖和 Tesseract OCR。",
        disabled=not has_access,
    )

if st.button("开始分析", type="primary", use_container_width=True, disabled=not has_access):
    if not has_access:
        st.session_state.analysis_error = "请先输入有效邀请码。"
    elif not jd_text.strip() or resume_file is None:
        st.session_state.analysis_error = "请填写岗位 JD，并上传 PDF 或图片简历。"
    else:
        st.session_state.analysis_error = ""
        progress_bar = st.progress(0)
        status_slot = st.empty()
        status_slot.markdown("当前状态：正在提交分析任务...")
        with st.spinner("AI 正在分析，请稍候..."):
            try:
                job = start_analyze_job(jd_text, resume_file)
                progress_bar.progress(int(job.get("progress", 0)))
                status_slot.markdown(f"当前状态：{job.get('current_step', '正在分析')}...")
                result = wait_for_analyze_result(
                    job_id=job["job_id"],
                    progress_bar=progress_bar,
                    status_slot=status_slot,
                )
                st.session_state.invite_quota = consume_invite_code(job["job_id"])
            except requests.Timeout:
                st.session_state.analysis_error = (
                    f"后端分析超过 {ANALYZE_TIMEOUT} 秒仍未返回。"
                    "后端可能仍在运行，请稍后查看后端日志或调大 CAREER_AGENT_ANALYZE_TIMEOUT。"
                )
            except requests.exceptions.RequestException as error:
                st.session_state.analysis_error = _friendly_request_error(error)
            except RuntimeError as error:
                st.session_state.analysis_error = str(error)
            except ValueError as error:
                st.session_state.analysis_error = str(error)
            else:
                st.session_state.analysis_result = result
                st.session_state.roadmap = result.get("roadmap", [])

if st.session_state.analysis_error:
    st.error(st.session_state.analysis_error)

render_result()
