"""Tests for JobExecutor timeout enforcement."""

import time
from typing import Any
from uuid import UUID

import pytest
from yubal import AudioCodec
from yubal_api.domain.enums import JobSource, JobStatus
from yubal_api.domain.job import Job
from yubal_api.services.job_executor import JobExecutor
from yubal_api.services.sync_service import SyncResult


class FakeJobStore:
    """Minimal fake implementing the JobExecutionStore protocol."""

    def __init__(self) -> None:
        self.transitions: list[tuple[str, JobStatus]] = []
        self.released: list[str] = []
        self._pending: list[Job] = []

    def create(
        self,
        url: str,
        audio_format: AudioCodec = AudioCodec.OPUS,
        max_items: int | None = None,
        source: JobSource = JobSource.MANUAL,
        subscription_id: UUID | None = None,
    ) -> tuple[Job, bool] | None:
        job = Job(id="test-job", url=url, audio_format=audio_format)
        return job, True

    def transition(self, job_id: str, status: JobStatus, **kwargs: Any) -> Job:
        self.transitions.append((job_id, status))
        return Job(id=job_id, url="", audio_format=AudioCodec.OPUS, status=status)

    def pop_next_pending(self) -> Job | None:
        return self._pending.pop(0) if self._pending else None

    def release_active(self, job_id: str) -> bool:
        self.released.append(job_id)
        return True


@pytest.mark.enable_socket
class TestExecutorTimeout:
    """Tests for timeout enforcement in _run_job."""

    @pytest.fixture
    def store(self) -> FakeJobStore:
        return FakeJobStore()

    @pytest.fixture
    def executor(self, store: FakeJobStore, tmp_path: Any) -> JobExecutor:
        return JobExecutor(job_store=store, base_path=tmp_path, job_timeout=0.1)

    @pytest.mark.asyncio
    async def test_timeout_triggers_cancellation_and_fails_job(
        self,
        executor: JobExecutor,
        store: FakeJobStore,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Timeout should mark job FAILED and trigger cancel token."""

        def blocking_run(*_args: Any, **_kwargs: Any) -> SyncResult:
            time.sleep(10)
            return SyncResult(success=True)

        monkeypatch.setattr(
            "yubal_api.services.job_executor.SyncService.run",
            blocking_run,
        )

        await executor._run_job("test-job", "https://example.com")

        # Should have transitioned to FETCHING_INFO then FAILED
        statuses = [s for _, s in store.transitions]
        assert JobStatus.FETCHING_INFO in statuses
        assert statuses[-1] == JobStatus.FAILED

        # Cancel token cleaned up in finally
        assert "test-job" not in executor._cancel_tokens

        # Active slot should have been released
        assert "test-job" in store.released

    @pytest.mark.asyncio
    async def test_normal_completion_within_timeout(
        self,
        executor: JobExecutor,
        store: FakeJobStore,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Job finishing before timeout should complete normally."""

        def fast_run(*_args: Any, **_kwargs: Any) -> SyncResult:
            return SyncResult(success=True)

        monkeypatch.setattr(
            "yubal_api.services.job_executor.SyncService.run",
            fast_run,
        )

        await executor._run_job("test-job", "https://example.com")

        statuses = [s for _, s in store.transitions]
        assert JobStatus.COMPLETED in statuses
        assert JobStatus.FAILED not in statuses
        assert "test-job" in store.released
