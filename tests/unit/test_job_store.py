"""Tests for yubal.services.job_store."""

from datetime import UTC, datetime, timedelta

import pytest

from yubal.core.enums import JobStatus
from yubal.core.models import AlbumInfo
from yubal.services.job_store import JobStore


@pytest.fixture
def fixed_time():
    """A fixed point in time for deterministic tests."""
    return datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def id_generator():
    """Predictable ID generator for tests."""
    counter = iter(range(100))
    return lambda: f"job-{next(counter)}"


@pytest.fixture
def job_store(fixed_time, id_generator):
    """JobStore with injectable clock and ID generator."""
    return JobStore(clock=lambda: fixed_time, id_generator=id_generator)


class TestCreateJob:
    """Tests for JobStore.create_job."""

    @pytest.mark.asyncio
    async def test_creates_job_with_predictable_id(self, job_store):
        """Job is created with ID from id_generator."""
        result = await job_store.create_job("https://example.com/playlist")

        assert result is not None
        job, _ = result
        assert job.id == "job-0"
        assert job.url == "https://example.com/playlist"
        assert job.audio_format == "mp3"
        assert job.status == JobStatus.PENDING

    @pytest.mark.asyncio
    async def test_first_job_should_start_immediately(self, job_store):
        """First job should start immediately (no active job)."""
        result = await job_store.create_job("https://example.com/playlist")

        assert result is not None
        _, should_start = result
        assert should_start is True

    @pytest.mark.asyncio
    async def test_second_job_should_queue(self, job_store):
        """Second job should queue while first is active."""
        await job_store.create_job("https://example.com/first")
        result = await job_store.create_job("https://example.com/second")

        assert result is not None
        job, should_start = result
        assert job.id == "job-1"
        assert should_start is False

    @pytest.mark.asyncio
    async def test_custom_audio_format(self, job_store):
        """Job respects custom audio format."""
        result = await job_store.create_job(
            "https://example.com/playlist", audio_format="opus"
        )

        assert result is not None
        job, _ = result
        assert job.audio_format == "opus"

    @pytest.mark.asyncio
    async def test_returns_none_when_queue_full(self, fixed_time, id_generator):
        """Returns None when queue is full of active jobs."""
        store = JobStore(clock=lambda: fixed_time, id_generator=id_generator)
        store.MAX_JOBS = 2  # Small limit for testing

        # Create 2 jobs (fills queue)
        await store.create_job("https://example.com/1")
        await store.create_job("https://example.com/2")

        # Third job should fail (queue full, no finished jobs to prune)
        result = await store.create_job("https://example.com/3")
        assert result is None

    @pytest.mark.asyncio
    async def test_prunes_finished_jobs_when_at_capacity(
        self, fixed_time, id_generator
    ):
        """Finished jobs are pruned to make room for new ones."""
        store = JobStore(clock=lambda: fixed_time, id_generator=id_generator)
        store.MAX_JOBS = 2

        # Create and complete first job
        result1 = await store.create_job("https://example.com/1")
        assert result1 is not None
        job1, _ = result1
        await store.update_job(job1.id, status=JobStatus.COMPLETED)

        # Create second job
        await store.create_job("https://example.com/2")

        # Third job should succeed (first job was pruned)
        result3 = await store.create_job("https://example.com/3")
        assert result3 is not None


class TestGetJob:
    """Tests for JobStore.get_job."""

    @pytest.mark.asyncio
    async def test_returns_job_by_id(self, job_store):
        """Can retrieve a job by its ID."""
        result = await job_store.create_job("https://example.com/playlist")
        assert result is not None
        created_job, _ = result

        retrieved = await job_store.get_job(created_job.id)
        assert retrieved is not None
        assert retrieved.id == created_job.id
        assert retrieved.url == "https://example.com/playlist"

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_job(self, job_store):
        """Returns None for nonexistent job ID."""
        result = await job_store.get_job("nonexistent-id")
        assert result is None


class TestCancelJob:
    """Tests for JobStore.cancel_job."""

    @pytest.mark.asyncio
    async def test_cancels_pending_job(self, job_store, fixed_time):
        """Can cancel a pending job."""
        result = await job_store.create_job("https://example.com/playlist")
        assert result is not None
        job, _ = result

        success = await job_store.cancel_job(job.id)
        assert success is True

        cancelled = await job_store.get_job(job.id)
        assert cancelled is not None
        assert cancelled.status == JobStatus.CANCELLED
        assert cancelled.completed_at == fixed_time

    @pytest.mark.asyncio
    async def test_cannot_cancel_finished_job(self, job_store):
        """Cannot cancel an already finished job."""
        result = await job_store.create_job("https://example.com/playlist")
        assert result is not None
        job, _ = result

        await job_store.update_job(job.id, status=JobStatus.COMPLETED)
        success = await job_store.cancel_job(job.id)

        assert success is False

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_job_returns_false(self, job_store):
        """Cancelling nonexistent job returns False."""
        success = await job_store.cancel_job("nonexistent-id")
        assert success is False

    @pytest.mark.asyncio
    async def test_is_cancelled_returns_true_after_cancel(self, job_store):
        """is_cancelled returns True after job is cancelled."""
        result = await job_store.create_job("https://example.com/playlist")
        assert result is not None
        job, _ = result

        assert job_store.is_cancelled(job.id) is False
        await job_store.cancel_job(job.id)
        assert job_store.is_cancelled(job.id) is True


class TestUpdateJob:
    """Tests for JobStore.update_job."""

    @pytest.mark.asyncio
    async def test_updates_status(self, job_store):
        """Can update job status."""
        result = await job_store.create_job("https://example.com/playlist")
        assert result is not None
        job, _ = result

        updated = await job_store.update_job(job.id, status=JobStatus.DOWNLOADING)
        assert updated is not None
        assert updated.status == JobStatus.DOWNLOADING

    @pytest.mark.asyncio
    async def test_updates_progress(self, job_store):
        """Can update job progress."""
        result = await job_store.create_job("https://example.com/playlist")
        assert result is not None
        job, _ = result

        updated = await job_store.update_job(job.id, progress=50.0)
        assert updated is not None
        assert updated.progress == 50.0

    @pytest.mark.asyncio
    async def test_updates_album_info(self, job_store):
        """Can update job album_info."""
        result = await job_store.create_job("https://example.com/playlist")
        assert result is not None
        job, _ = result

        album = AlbumInfo(title="Test Album", artist="Test Artist", track_count=10)
        updated = await job_store.update_job(job.id, album_info=album)

        assert updated is not None
        assert updated.album_info is not None
        assert updated.album_info.title == "Test Album"

    @pytest.mark.asyncio
    async def test_cannot_update_cancelled_job(self, job_store):
        """Cancelled jobs cannot be updated."""
        result = await job_store.create_job("https://example.com/playlist")
        assert result is not None
        job, _ = result

        await job_store.cancel_job(job.id)
        updated = await job_store.update_job(job.id, progress=100.0)

        # Returns job but doesn't apply update
        assert updated is not None
        assert updated.progress == 0.0  # Not updated

    @pytest.mark.asyncio
    async def test_finishing_job_sets_completed_at(self, job_store, fixed_time):
        """Finishing a job sets completed_at if not already set."""
        result = await job_store.create_job("https://example.com/playlist")
        assert result is not None
        job, _ = result

        updated = await job_store.update_job(job.id, status=JobStatus.COMPLETED)
        assert updated is not None
        assert updated.completed_at == fixed_time


class TestAddLog:
    """Tests for JobStore.add_log."""

    @pytest.mark.asyncio
    async def test_adds_log_entry(self, job_store, fixed_time):
        """Can add log entries to a job."""
        result = await job_store.create_job("https://example.com/playlist")
        assert result is not None
        job, _ = result

        await job_store.add_log(job.id, "downloading", "Track 1: 50%")

        logs = await job_store.get_all_logs()
        assert len(logs) == 1
        assert logs[0].status == "downloading"
        assert logs[0].message == "Track 1: 50%"
        assert logs[0].timestamp == fixed_time

    @pytest.mark.asyncio
    async def test_does_not_add_log_to_cancelled_job(self, job_store):
        """Cannot add logs to cancelled jobs."""
        result = await job_store.create_job("https://example.com/playlist")
        assert result is not None
        job, _ = result

        await job_store.cancel_job(job.id)
        await job_store.add_log(job.id, "downloading", "Should not appear")

        logs = await job_store.get_all_logs()
        assert len(logs) == 0

    @pytest.mark.asyncio
    async def test_trims_logs_when_exceeding_limit(self, fixed_time, id_generator):
        """Logs are trimmed when exceeding per-job limit."""
        store = JobStore(clock=lambda: fixed_time, id_generator=id_generator)
        store.MAX_LOGS_PER_JOB = 3

        result = await store.create_job("https://example.com/playlist")
        assert result is not None
        job, _ = result

        # Add 5 logs (exceeds limit of 3)
        for i in range(5):
            await store.add_log(job.id, "status", f"Log {i}")

        logs = await store.get_all_logs()
        assert len(logs) == 3
        # Should keep the most recent logs
        assert logs[0].message == "Log 2"
        assert logs[2].message == "Log 4"


class TestPopNextPending:
    """Tests for JobStore.pop_next_pending."""

    @pytest.mark.asyncio
    async def test_returns_oldest_pending_job(self, job_store):
        """Returns the oldest pending job (FIFO)."""
        await job_store.create_job("https://example.com/1")  # Active
        await job_store.create_job("https://example.com/2")  # Pending
        await job_store.create_job("https://example.com/3")  # Pending

        next_job = await job_store.pop_next_pending()
        assert next_job is not None
        assert next_job.id == "job-1"  # Second job (first pending)

    @pytest.mark.asyncio
    async def test_returns_none_when_no_pending(self, job_store):
        """Returns None when no pending jobs."""
        await job_store.create_job("https://example.com/1")  # Active only

        next_job = await job_store.pop_next_pending()
        assert next_job is None


class TestDeleteJob:
    """Tests for JobStore.delete_job."""

    @pytest.mark.asyncio
    async def test_deletes_finished_job(self, job_store):
        """Can delete a finished job."""
        result = await job_store.create_job("https://example.com/playlist")
        assert result is not None
        job, _ = result

        await job_store.update_job(job.id, status=JobStatus.COMPLETED)
        success = await job_store.delete_job(job.id)

        assert success is True
        assert await job_store.get_job(job.id) is None

    @pytest.mark.asyncio
    async def test_cannot_delete_running_job(self, job_store):
        """Cannot delete a running job."""
        result = await job_store.create_job("https://example.com/playlist")
        assert result is not None
        job, _ = result

        success = await job_store.delete_job(job.id)
        assert success is False


class TestClearCompleted:
    """Tests for JobStore.clear_completed."""

    @pytest.mark.asyncio
    async def test_clears_finished_jobs(self, job_store):
        """Clears all finished jobs."""
        # Create and complete 2 jobs
        result1 = await job_store.create_job("https://example.com/1")
        assert result1 is not None
        job1, _ = result1
        await job_store.update_job(job1.id, status=JobStatus.COMPLETED)

        result2 = await job_store.create_job("https://example.com/2")
        assert result2 is not None
        job2, _ = result2
        await job_store.update_job(job2.id, status=JobStatus.FAILED)

        # Create pending job
        await job_store.create_job("https://example.com/3")

        count = await job_store.clear_completed()
        assert count == 2

        jobs = await job_store.get_all_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == "job-2"  # Only the pending job remains


class TestTimeout:
    """Tests for job timeout detection."""

    @pytest.mark.asyncio
    async def test_job_times_out_after_threshold(self, id_generator):
        """Jobs time out after TIMEOUT_SECONDS."""
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        current_time = [start_time]  # Mutable for advancing time

        store = JobStore(
            clock=lambda: current_time[0],
            id_generator=id_generator,
        )
        store.TIMEOUT_SECONDS = 60  # 1 minute for testing

        # Create and start job
        result = await store.create_job("https://example.com/playlist")
        assert result is not None
        job, _ = result
        await store.update_job(job.id, started_at=start_time)

        # Advance time past timeout
        current_time[0] = start_time + timedelta(seconds=61)

        # Get job triggers timeout check
        timed_out_job = await store.get_job(job.id)
        assert timed_out_job is not None
        assert timed_out_job.status == JobStatus.FAILED

    @pytest.mark.asyncio
    async def test_job_does_not_timeout_before_threshold(self, id_generator):
        """Jobs don't time out before TIMEOUT_SECONDS."""
        start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        current_time = [start_time]

        store = JobStore(
            clock=lambda: current_time[0],
            id_generator=id_generator,
        )
        store.TIMEOUT_SECONDS = 60

        result = await store.create_job("https://example.com/playlist")
        assert result is not None
        job, _ = result
        await store.update_job(job.id, started_at=start_time)

        # Advance time but not past timeout
        current_time[0] = start_time + timedelta(seconds=30)

        still_running = await store.get_job(job.id)
        assert still_running is not None
        assert still_running.status == JobStatus.PENDING  # Not timed out
