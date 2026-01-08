"""Jobs API endpoints."""

from fastapi import APIRouter, HTTPException, status

from yubal.api.dependencies import (
    AudioFormatDep,
    JobExecutorDep,
    JobStoreDep,
)
from yubal.core.models import Job
from yubal.schemas.jobs import (
    CancelJobResponse,
    ClearJobsResponse,
    CreateJobRequest,
    JobConflictErrorResponse,
    JobCreatedResponse,
    JobListResponse,
)
from yubal.services.job_store import JobStore

router = APIRouter()


def _get_job_or_404(job_store: JobStore, job_id: str) -> Job:
    """Get job by ID or raise 404."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    return job


@router.post(
    "/jobs",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": JobConflictErrorResponse, "description": "Queue is full"}
    },
)
async def create_job(
    request: CreateJobRequest,
    audio_format: AudioFormatDep,
    job_store: JobStoreDep,
    job_executor: JobExecutorDep,
) -> JobCreatedResponse:
    """Create a new sync job.

    Jobs are queued and executed sequentially. Returns 409 only if queue is full.
    """
    result = job_store.create_job(request.url, audio_format)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "Queue is full", "active_job_id": None},
        )

    job, should_start = result

    if should_start:
        job_executor.start_job(job)

    return JobCreatedResponse(id=job.id)


@router.get("/jobs")
async def list_jobs(job_store: JobStoreDep) -> JobListResponse:
    """List all jobs (oldest first, FIFO order).

    Returns up to 50 jobs with their current status and all logs.
    """
    jobs = job_store.get_all_jobs()
    logs = job_store.get_all_logs()

    return JobListResponse(jobs=jobs, logs=logs)


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    job_store: JobStoreDep,
    job_executor: JobExecutorDep,
) -> CancelJobResponse:
    """Cancel a running or queued job.

    Returns 404 if job not found, 409 if job already finished.
    """
    job = _get_job_or_404(job_store, job_id)

    if job.status.is_finished:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job already finished",
        )

    # Signal cancellation via cancel token if job is running
    job_executor.cancel_job(job_id)

    success = job_store.cancel_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not cancel job",
        )

    return CancelJobResponse()


@router.delete("/jobs")
async def clear_jobs(job_store: JobStoreDep) -> ClearJobsResponse:
    """Clear all completed/failed jobs.

    Running jobs are not affected.
    """
    count = job_store.clear_completed()
    return ClearJobsResponse(cleared=count)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: str, job_store: JobStoreDep) -> None:
    """Delete a completed, failed, or cancelled job.

    Running jobs cannot be deleted (returns 409).
    """
    job = _get_job_or_404(job_store, job_id)

    if not job.status.is_finished:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a running job",
        )

    job_store.delete_job(job_id)
