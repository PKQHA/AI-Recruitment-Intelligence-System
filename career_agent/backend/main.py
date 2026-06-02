"""
FastAPI backend for the V2 recruitment analysis agent.
"""

from __future__ import annotations

import threading
import traceback
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile  # pyright: ignore[reportMissingImports]
from pydantic import BaseModel  # pyright: ignore[reportMissingImports]

from core.v2_agent import run as run_v2_agent, run_with_progress
from services.invite_code_store import InviteCodeStore
from services.resume_parser import ResumeParser


app = FastAPI(title="AI Recruitment Analysis V3 API")
resume_parser = ResumeParser()
invite_store = InviteCodeStore()


@dataclass
class AnalysisJob:
    invite_code: str = ""
    fingerprint: str = ""
    ip: str = ""
    user_agent: str = ""
    current_step: str = "等待开始"
    progress: int = 0
    status: str = "pending"
    result: dict[str, Any] | None = None
    error: str = ""
    traceback_text: str = ""
    lock: threading.Lock = field(default_factory=threading.Lock)


JOBS: dict[str, AnalysisJob] = {}


class AnalyzeResponse(BaseModel):
    match_rate: float
    matched_skills: list[str]
    missing_skills: list[str]
    recommendation: list[str]
    roadmap: list[dict[str, Any]]


class JobCreateResponse(BaseModel):
    job_id: str
    current_step: str
    progress: int
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    current_step: str
    progress: int
    status: str
    result: dict[str, Any] | None = None
    error: str = ""


class VerifyCodeRequest(BaseModel):
    code: str
    fingerprint: str


class ConsumeCodeRequest(BaseModel):
    code: str
    fingerprint: str
    request_id: str
    result_status: str = "success"


class QuotaResponse(BaseModel):
    valid: bool = False
    remaining: int | None = 0
    limit: int | None = 2
    used: int = 0
    unlimited: bool = False


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "AI Recruitment Analysis API",
        "health": "/health",
        "docs": "/docs",
    }


@app.post("/verify-code", response_model=QuotaResponse)
def verify_code(payload: VerifyCodeRequest, request: Request) -> dict[str, Any]:
    return invite_store.verify(
        code=payload.code,
        fingerprint=payload.fingerprint,
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )


@app.get("/quota", response_model=QuotaResponse)
def get_quota(code: str, fingerprint: str) -> dict[str, Any]:
    return invite_store.quota(code=code, fingerprint=fingerprint)


@app.post("/consume-code", response_model=QuotaResponse)
def consume_code(payload: ConsumeCodeRequest, request: Request) -> dict[str, Any]:
    if payload.result_status != "success":
        raise HTTPException(status_code=400, detail="只有成功结果可以扣减邀请码次数。")
    return invite_store.consume(
        code=payload.code,
        fingerprint=payload.fingerprint,
        ip=_client_ip(request),
        user_agent=_user_agent(request),
        request_id=payload.request_id,
        result_status=payload.result_status,
    )


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    request: Request,
    jd: str = Form(...),
    resume_file: UploadFile = File(...),
    invite_code: str = Form(...),
    fingerprint: str = Form(...),
) -> dict[str, Any]:
    try:
        quota = invite_store.quota(code=invite_code, fingerprint=fingerprint)
        if not quota["valid"]:
            raise ValueError("邀请码无效或次数已用尽。")

        jd_text = jd.strip()
        if not jd_text:
            raise ValueError("岗位 JD 不能为空。")

        resume_content = await resume_file.read()
        resume_text = resume_parser.parse(
            content=resume_content,
            filename=resume_file.filename or "",
            content_type=resume_file.content_type,
        )
        result = run_v2_agent(jd=jd_text, resume=resume_text)
        invite_store.consume(
            code=invite_code,
            fingerprint=fingerprint,
            ip=_client_ip(request),
            user_agent=_user_agent(request),
            request_id=uuid4().hex,
            result_status="success",
        )
        return result
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.post("/analyze/jobs", response_model=JobCreateResponse)
async def create_analyze_job(
    request: Request,
    jd: str = Form(...),
    resume_file: UploadFile = File(...),
    invite_code: str = Form(...),
    fingerprint: str = Form(...),
    user_agent_header: str | None = Header(default=None, alias="User-Agent"),
) -> dict[str, Any]:
    quota = invite_store.quota(code=invite_code, fingerprint=fingerprint)
    if not quota["valid"]:
        raise HTTPException(status_code=403, detail="邀请码无效或次数已用尽。")

    job_id = uuid4().hex
    job = AnalysisJob(
        invite_code=invite_code.strip(),
        fingerprint=fingerprint.strip(),
        ip=_client_ip(request),
        user_agent=user_agent_header or _user_agent(request),
        current_step="正在解析简历",
        progress=5,
        status="running",
    )
    JOBS[job_id] = job

    jd_text = jd.strip()
    resume_content = await resume_file.read()
    filename = resume_file.filename or ""
    content_type = resume_file.content_type

    thread = threading.Thread(
        target=_run_analysis_job,
        args=(job_id, jd_text, resume_content, filename, content_type),
        daemon=True,
    )
    thread.start()

    return _job_payload(job_id, job)


@app.get("/analyze/jobs/{job_id}", response_model=JobStatusResponse)
def get_analyze_job(job_id: str) -> dict[str, Any]:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="分析任务不存在。")
    return _job_payload(job_id, job)


def _run_analysis_job(
    job_id: str,
    jd_text: str,
    resume_content: bytes,
    filename: str,
    content_type: str | None,
) -> None:
    job = JOBS[job_id]
    try:
        if not jd_text:
            raise ValueError("岗位 JD 不能为空。")

        _update_job(job, "正在解析简历", 10)
        resume_text = resume_parser.parse(
            content=resume_content,
            filename=filename,
            content_type=content_type,
        )

        _update_job(job, "简历解析完成", 18)

        def report_progress(current_step: str, progress: int) -> None:
            _update_job(job, current_step, progress)

        result = run_with_progress(
            jd=jd_text,
            resume=resume_text,
            progress_callback=report_progress,
        )
        invite_store.consume(
            code=job.invite_code,
            fingerprint=job.fingerprint,
            ip=job.ip,
            user_agent=job.user_agent,
            request_id=job_id,
            result_status="success",
        )
        with job.lock:
            job.current_step = "分析完成"
            job.progress = 100
            job.status = "done"
            job.result = result
    except Exception as error:  # noqa: BLE001
        traceback_text = traceback.format_exc()
        print(traceback_text)
        with job.lock:
            job.current_step = "分析失败"
            job.progress = max(job.progress, 1)
            job.status = "error"
            job.error = str(error)
            job.traceback_text = traceback_text


def _update_job(job: AnalysisJob, current_step: str, progress: int) -> None:
    with job.lock:
        job.current_step = current_step
        job.progress = max(0, min(100, progress))


def _job_payload(job_id: str, job: AnalysisJob) -> dict[str, Any]:
    with job.lock:
        return {
            "job_id": job_id,
            "current_step": job.current_step,
            "progress": job.progress,
            "status": job.status,
            "result": job.result,
            "error": job.error,
        }


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", maxsplit=1)[0].strip()
    return request.client.host if request.client else ""


def _user_agent(request: Request) -> str:
    return request.headers.get("user-agent", "")
