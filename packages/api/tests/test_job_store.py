"""Comprehensive tests for JobStore."""

import threading
from typing import Any

import pytest
from yubal import AudioCodec, PhaseStats
from yubal_api.domain.enums import JobSource, JobStatus
from yubal_api.domain.job import ContentInfo
from yubal_api.services.job_store import JobStore

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def store(clock: Any, id_generator: Any) -> JobStore:
    """Provide a configured JobStore instance."""
    return JobStore(clock=clock, id_generator=id_generator)


@pytest.fixture
def sample_content_info() -> ContentInfo:
    """Provide sample content info for tests."""
    return ContentInfo(
        title="Test Album",
        artist="Test Artist",
        year=2024,
        track_count=10,
        playlist_id="PLtest123",
        url="https://music.youtube.com/playlist?list=PLtest123",
    )


@pytest.fixture
def sample_download_stats() -> PhaseStats:
    """Provide sample download stats for tests."""
    return PhaseStats(success=8, failed=1, skipped_by_reason={})


# =============================================================================
# Test Class: Job Lifecycle
# =============================================================================


class TestJobLifecycle:
    """Tests for basic job lifecycle operations: create, get, get_all, delete."""

    def test_create_returns_job_with_correct_fields(
        self, store: JobStore, id_generator: Any
    ) -> None:
        """Created job should have all expected default fields."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _should_start = result

        assert job.id == "job-0001"
        assert job.url == "https://music.youtube.com/playlist?list=PLtest"
        assert job.audio_format == AudioCodec.OPUS
        assert job.max_items is None
        assert job.status == JobStatus.PENDING
        assert job.progress == 0.0
        assert job.content_info is None
        assert job.download_stats is None
        assert job.started_at is None
        assert job.completed_at is None

    def test_create_with_custom_audio_format(self, store: JobStore) -> None:
        """Created job should respect custom audio format."""
        result = store.create(
            "https://music.youtube.com/playlist?list=PLtest",
            audio_format=AudioCodec.MP3,
        )
        assert result is not None
        job, _ = result
        assert job.audio_format == AudioCodec.MP3

    def test_create_with_max_items(self, store: JobStore) -> None:
        """Created job should respect max_items parameter."""
        result = store.create(
            "https://music.youtube.com/playlist?list=PLtest",
            max_items=5,
        )
        assert result is not None
        job, _ = result
        assert job.max_items == 5

    def test_create_defaults_to_manual_source(self, store: JobStore) -> None:
        """Created job should default to MANUAL source when not specified."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result
        assert job.source == JobSource.MANUAL

    def test_create_with_scheduler_source(self, store: JobStore) -> None:
        """Created job should respect source parameter when set to SCHEDULER."""
        result = store.create(
            "https://music.youtube.com/playlist?list=PLtest",
            source=JobSource.SCHEDULER,
        )
        assert result is not None
        job, _ = result
        assert job.source == JobSource.SCHEDULER

    def test_source_is_retrievable_after_get(self, store: JobStore) -> None:
        """Source should be correctly stored and retrievable via get()."""
        result = store.create(
            "https://music.youtube.com/playlist?list=PLtest",
            source=JobSource.SCHEDULER,
        )
        assert result is not None
        job, _ = result

        retrieved = store.get(job.id)
        assert retrieved is not None
        assert retrieved.source == JobSource.SCHEDULER

    def test_create_first_job_should_start_immediately(self, store: JobStore) -> None:
        """First job created should be marked for immediate start."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        _, should_start = result
        assert should_start is True

    def test_create_second_job_should_not_start_immediately(
        self, store: JobStore
    ) -> None:
        """Second job should be queued, not started immediately."""
        store.create("https://music.youtube.com/playlist?list=PL1")
        result = store.create("https://music.youtube.com/playlist?list=PL2")

        assert result is not None
        _, should_start = result
        assert should_start is False

    def test_get_existing_job(self, store: JobStore) -> None:
        """Should return job when it exists."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        created_job, _ = result

        retrieved_job = store.get(created_job.id)
        assert retrieved_job is not None
        assert retrieved_job.id == created_job.id
        assert retrieved_job.url == created_job.url

    def test_get_nonexistent_job_returns_none(self, store: JobStore) -> None:
        """Should return None for non-existent job ID."""
        result = store.get("nonexistent-job-id")
        assert result is None

    def test_get_all_returns_jobs_in_fifo_order(self, store: JobStore) -> None:
        """Jobs should be returned in order of creation (oldest first)."""
        store.create("https://music.youtube.com/playlist?list=PL1")
        store.create("https://music.youtube.com/playlist?list=PL2")
        store.create("https://music.youtube.com/playlist?list=PL3")

        jobs = store.get_all()

        assert len(jobs) == 3
        assert jobs[0].id == "job-0001"
        assert jobs[1].id == "job-0002"
        assert jobs[2].id == "job-0003"

    def test_get_all_empty_store(self, store: JobStore) -> None:
        """Should return empty list when no jobs exist."""
        jobs = store.get_all()
        assert jobs == []

    def test_delete_finished_job(self, store: JobStore) -> None:
        """Should successfully delete a completed job."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        store.transition(job.id, JobStatus.COMPLETED)

        deleted = store.delete(job.id)
        assert deleted is True
        assert store.get(job.id) is None

    def test_delete_nonexistent_job_returns_false(self, store: JobStore) -> None:
        """Should return False when deleting non-existent job."""
        deleted = store.delete("nonexistent-job-id")
        assert deleted is False

    def test_delete_running_job_returns_false(self, store: JobStore) -> None:
        """Should not delete jobs that are still running."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        store.transition(job.id, JobStatus.DOWNLOADING)

        deleted = store.delete(job.id)
        assert deleted is False
        assert store.get(job.id) is not None

    def test_delete_pending_job_returns_false(self, store: JobStore) -> None:
        """Should not delete pending jobs."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        deleted = store.delete(job.id)
        assert deleted is False

    @pytest.mark.parametrize(
        "status",
        [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED],
    )
    def test_delete_accepts_all_finished_statuses(
        self, store: JobStore, status: JobStatus
    ) -> None:
        """Should allow deletion of jobs with any finished status."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        store.transition(job.id, status)

        deleted = store.delete(job.id)
        assert deleted is True

    def test_clear_finished_removes_all_finished_jobs(self, store: JobStore) -> None:
        """Should remove all completed, failed, and cancelled jobs."""
        # Create multiple jobs with different statuses
        store.create("https://music.youtube.com/playlist?list=PL1")  # will stay pending
        r2 = store.create("https://music.youtube.com/playlist?list=PL2")
        r3 = store.create("https://music.youtube.com/playlist?list=PL3")
        r4 = store.create("https://music.youtube.com/playlist?list=PL4")

        assert r2 and r3 and r4
        store.transition(r2[0].id, JobStatus.COMPLETED)
        store.transition(r3[0].id, JobStatus.FAILED)
        store.transition(r4[0].id, JobStatus.CANCELLED)

        count = store.clear_finished()

        assert count == 3
        jobs = store.get_all()
        assert len(jobs) == 1
        assert jobs[0].id == "job-0001"

    def test_clear_finished_with_no_finished_jobs(self, store: JobStore) -> None:
        """Should return 0 when no finished jobs exist."""
        store.create("https://music.youtube.com/playlist?list=PL1")
        store.create("https://music.youtube.com/playlist?list=PL2")

        count = store.clear_finished()

        assert count == 0
        assert len(store.get_all()) == 2


# =============================================================================
# Test Class: Job State Transitions
# =============================================================================


class TestJobStateTransitions:
    """Tests for job state transitions via transition() and cancel()."""

    def test_transition_updates_status(self, store: JobStore) -> None:
        """Transition should update job status."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        updated = store.transition(job.id, JobStatus.FETCHING_INFO)

        assert updated is not None
        assert updated.status == JobStatus.FETCHING_INFO

    def test_transition_updates_progress(self, store: JobStore) -> None:
        """Transition should update progress when provided."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        updated = store.transition(job.id, JobStatus.DOWNLOADING, progress=0.5)

        assert updated is not None
        assert updated.progress == 0.5

    def test_transition_updates_content_info(
        self, store: JobStore, sample_content_info: ContentInfo
    ) -> None:
        """Transition should update content_info when provided."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        updated = store.transition(
            job.id,
            JobStatus.DOWNLOADING,
            content_info=sample_content_info,
        )

        assert updated is not None
        assert updated.content_info == sample_content_info

    def test_transition_updates_download_stats(
        self, store: JobStore, sample_download_stats: PhaseStats
    ) -> None:
        """Transition should update download_stats when provided."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        updated = store.transition(
            job.id,
            JobStatus.COMPLETED,
            download_stats=sample_download_stats,
        )

        assert updated is not None
        assert updated.download_stats == sample_download_stats

    def test_transition_updates_started_at(self, store: JobStore, clock: Any) -> None:
        """Transition should update started_at when provided."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        start_time = clock()
        updated = store.transition(
            job.id,
            JobStatus.FETCHING_INFO,
            started_at=start_time,
        )

        assert updated is not None
        assert updated.started_at == start_time

    def test_transition_to_finished_sets_completed_at(
        self, store: JobStore, clock: Any
    ) -> None:
        """Finishing a job should automatically set completed_at."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        updated = store.transition(job.id, JobStatus.COMPLETED)

        assert updated is not None
        assert updated.completed_at == clock()

    def test_transition_nonexistent_job_returns_none(self, store: JobStore) -> None:
        """Transition on non-existent job should return None."""
        result = store.transition("nonexistent-id", JobStatus.DOWNLOADING)
        assert result is None

    @pytest.mark.parametrize(
        "status",
        [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED],
    )
    def test_transition_to_finished_clears_active_job(
        self, store: JobStore, status: JobStatus
    ) -> None:
        """Transitioning to finished status should clear active job slot."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, should_start = result
        assert should_start is True

        # Create second job (queued)
        result2 = store.create("https://music.youtube.com/playlist?list=PL2")
        assert result2 is not None
        _, should_start2 = result2
        assert should_start2 is False

        # Finish first job
        store.transition(job.id, status)

        # Now pop_next_pending should return the second job
        next_job = store.pop_next_pending()
        assert next_job is not None
        assert next_job.id == "job-0002"

    def test_cancel_pending_job(self, store: JobStore) -> None:
        """Should successfully cancel a pending job."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        cancelled = store.cancel(job.id)

        assert cancelled is True
        updated = store.get(job.id)
        assert updated is not None
        assert updated.status == JobStatus.CANCELLED

    def test_cancel_running_job(self, store: JobStore) -> None:
        """Should successfully cancel a running job."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        store.transition(job.id, JobStatus.DOWNLOADING)
        cancelled = store.cancel(job.id)

        assert cancelled is True
        updated = store.get(job.id)
        assert updated is not None
        assert updated.status == JobStatus.CANCELLED

    def test_cancel_sets_completed_at(self, store: JobStore, clock: Any) -> None:
        """Cancelling a job should set completed_at."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        store.cancel(job.id)

        updated = store.get(job.id)
        assert updated is not None
        assert updated.completed_at == clock()

    def test_cancel_nonexistent_job_returns_false(self, store: JobStore) -> None:
        """Should return False when cancelling non-existent job."""
        cancelled = store.cancel("nonexistent-id")
        assert cancelled is False

    @pytest.mark.parametrize(
        "status",
        [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED],
    )
    def test_cancel_finished_job_returns_false(
        self, store: JobStore, status: JobStatus
    ) -> None:
        """Should return False when cancelling already finished job."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        store.transition(job.id, status)
        cancelled = store.cancel(job.id)

        assert cancelled is False


# =============================================================================
# Test Class: Queue Management
# =============================================================================


class TestQueueManagement:
    """Tests for queue operations: pop_next_pending, release_active."""

    def test_pop_next_pending_returns_first_pending(self, store: JobStore) -> None:
        """Should return the oldest pending job."""
        # Create first job (becomes active)
        r1 = store.create("https://music.youtube.com/playlist?list=PL1")
        assert r1 is not None
        job1, should_start = r1
        assert should_start is True

        # Create two more jobs while first is still active (they stay pending)
        r2 = store.create("https://music.youtube.com/playlist?list=PL2")
        r3 = store.create("https://music.youtube.com/playlist?list=PL3")
        assert r2 is not None and r3 is not None
        assert r2[1] is False  # Should not start immediately
        assert r3[1] is False  # Should not start immediately

        # Complete first job to free the active slot
        store.transition(job1.id, JobStatus.COMPLETED)

        # pop_next_pending should return the oldest pending job (job2)
        next_job = store.pop_next_pending()

        assert next_job is not None
        assert next_job.id == "job-0002"

    def test_pop_next_pending_empty_queue(self, store: JobStore) -> None:
        """Should return None when no pending jobs exist."""
        next_job = store.pop_next_pending()
        assert next_job is None

    def test_pop_next_pending_all_finished(self, store: JobStore) -> None:
        """Should return None when all jobs are finished."""
        r1 = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert r1 is not None
        store.transition(r1[0].id, JobStatus.COMPLETED)

        next_job = store.pop_next_pending()
        assert next_job is None

    def test_pop_next_pending_skips_active_job(self, store: JobStore) -> None:
        """Should not return the currently active job."""
        # First job becomes active
        r1 = store.create("https://music.youtube.com/playlist?list=PL1")
        assert r1 is not None
        _job1, should_start = r1
        assert should_start is True

        # Second job is pending
        r2 = store.create("https://music.youtube.com/playlist?list=PL2")
        assert r2 is not None

        # pop_next_pending should return the second job, not the first
        next_job = store.pop_next_pending()
        assert next_job is not None
        assert next_job.id == "job-0002"

    def test_release_active_clears_slot(self, store: JobStore) -> None:
        """release_active should clear the active job slot."""
        r1 = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert r1 is not None
        job, _ = r1

        released = store.release_active(job.id)

        assert released is True

    def test_release_active_wrong_job_returns_false(self, store: JobStore) -> None:
        """Should return False when releasing a job that isn't active."""
        r1 = store.create("https://music.youtube.com/playlist?list=PL1")
        r2 = store.create("https://music.youtube.com/playlist?list=PL2")
        assert r1 and r2

        # job1 is active, try to release job2
        released = store.release_active(r2[0].id)

        assert released is False

    def test_release_active_allows_next_job_to_start(self, store: JobStore) -> None:
        """After release_active, next job should be able to start."""
        r1 = store.create("https://music.youtube.com/playlist?list=PL1")
        r2 = store.create("https://music.youtube.com/playlist?list=PL2")
        assert r1 and r2
        job1, _ = r1

        # Cancel job1 (note: cancel does NOT release active slot)
        store.cancel(job1.id)

        # Release the active slot
        store.release_active(job1.id)

        # Now pop_next_pending should return job2
        next_job = store.pop_next_pending()
        assert next_job is not None
        assert next_job.id == "job-0002"

    def test_fifo_order_maintained(self, store: JobStore) -> None:
        """Jobs should be processed in FIFO order."""
        # Create first job (becomes active)
        r1 = store.create("https://music.youtube.com/playlist?list=PL1")
        assert r1 is not None
        job1, _ = r1

        # Queue more jobs
        store.create("https://music.youtube.com/playlist?list=PL2")
        store.create("https://music.youtube.com/playlist?list=PL3")

        # Complete and release first job
        store.transition(job1.id, JobStatus.COMPLETED)
        store.release_active(job1.id)

        # Pop should return PL2 (second oldest)
        next_job = store.pop_next_pending()
        assert next_job is not None
        assert next_job.id == "job-0002"

        # Pop again should return PL3
        next_job2 = store.pop_next_pending()
        assert next_job2 is not None
        assert next_job2.id == "job-0003"


# =============================================================================
# Test Class: Capacity Limits and Pruning
# =============================================================================


class TestCapacityLimits:
    """Tests for MAX_JOBS capacity limits and pruning behavior."""

    def test_capacity_limit_reached(self, clock: Any, id_generator: Any) -> None:
        """Should return None when at capacity with no finished jobs to prune."""
        store = JobStore(clock=clock, id_generator=id_generator)

        # Fill to capacity with pending jobs
        for i in range(JobStore.MAX_JOBS):
            result = store.create(f"https://music.youtube.com/playlist?list=PL{i}")
            assert result is not None

        # One more should fail
        result = store.create("https://music.youtube.com/playlist?list=PLextra")
        assert result is None

    def test_pruning_removes_oldest_finished(
        self, clock: Any, id_generator: Any
    ) -> None:
        """When at capacity, oldest finished job should be pruned."""
        store = JobStore(clock=clock, id_generator=id_generator)

        # Create jobs up to capacity
        for i in range(JobStore.MAX_JOBS):
            result = store.create(f"https://music.youtube.com/playlist?list=PL{i}")
            assert result is not None

        # Complete the first job
        store.transition("job-0001", JobStatus.COMPLETED)

        # Now creating a new job should prune the completed one
        result = store.create("https://music.youtube.com/playlist?list=PLnew")
        assert result is not None

        # The completed job should be gone
        assert store.get("job-0001") is None
        # New job should exist
        assert store.get(result[0].id) is not None

    def test_pruning_multiple_finished_jobs(
        self, clock: Any, id_generator: Any
    ) -> None:
        """Should prune enough finished jobs to make room."""
        store = JobStore(clock=clock, id_generator=id_generator)

        # Fill to capacity
        for i in range(JobStore.MAX_JOBS):
            store.create(f"https://music.youtube.com/playlist?list=PL{i}")

        # Complete multiple jobs
        store.transition("job-0001", JobStatus.COMPLETED)
        store.transition("job-0002", JobStatus.FAILED)
        store.transition("job-0003", JobStatus.CANCELLED)

        # Create new job - should prune job-0001 (oldest finished)
        result = store.create("https://music.youtube.com/playlist?list=PLnew")
        assert result is not None

        # Only job-0001 should be pruned (we only needed one slot)
        assert store.get("job-0001") is None
        assert store.get("job-0002") is not None  # Still exists
        assert store.get("job-0003") is not None  # Still exists

    def test_capacity_with_all_running_jobs(
        self, clock: Any, id_generator: Any
    ) -> None:
        """Should fail when all jobs are running or pending."""
        store = JobStore(clock=clock, id_generator=id_generator)

        # Fill with running jobs
        for i in range(JobStore.MAX_JOBS):
            result = store.create(f"https://music.youtube.com/playlist?list=PL{i}")
            assert result is not None
            store.transition(f"job-{i + 1:04d}", JobStatus.DOWNLOADING)

        # Cannot create new job
        result = store.create("https://music.youtube.com/playlist?list=PLextra")
        assert result is None


# =============================================================================
# Test Class: Timeout Detection
# =============================================================================


class TestTimeoutDetection:
    """Tests for timeout detection on stalled jobs."""

    def test_timeout_marks_job_as_failed(self, store: JobStore, clock: Any) -> None:
        """Job exceeding timeout should be marked as failed."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        # Start the job
        store.transition(job.id, JobStatus.DOWNLOADING, started_at=clock())

        # Advance time past timeout
        clock.advance(JobStore.TIMEOUT_SECONDS + 1)

        # Get the job (triggers timeout check)
        updated = store.get(job.id)

        assert updated is not None
        assert updated.status == JobStatus.FAILED
        assert updated.completed_at == clock()

    def test_timeout_not_triggered_before_threshold(
        self, store: JobStore, clock: Any
    ) -> None:
        """Job should not timeout if within threshold."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        store.transition(job.id, JobStatus.DOWNLOADING, started_at=clock())

        # Advance time to just under timeout
        clock.advance(JobStore.TIMEOUT_SECONDS - 1)

        updated = store.get(job.id)

        assert updated is not None
        assert updated.status == JobStatus.DOWNLOADING

    def test_timeout_not_triggered_for_pending_jobs(
        self, store: JobStore, clock: Any
    ) -> None:
        """Pending jobs without started_at should not timeout."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        clock.advance(JobStore.TIMEOUT_SECONDS + 100)

        updated = store.get(job.id)

        assert updated is not None
        assert updated.status == JobStatus.PENDING

    def test_timeout_not_triggered_for_finished_jobs(
        self, store: JobStore, clock: Any
    ) -> None:
        """Already finished jobs should not be re-marked on timeout check."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        start_time = clock()
        store.transition(job.id, JobStatus.DOWNLOADING, started_at=start_time)
        store.transition(job.id, JobStatus.COMPLETED)

        clock.advance(JobStore.TIMEOUT_SECONDS + 1)

        updated = store.get(job.id)

        assert updated is not None
        assert updated.status == JobStatus.COMPLETED

    def test_timeout_clears_active_job(self, store: JobStore, clock: Any) -> None:
        """Timed-out job should release the active slot."""
        r1 = store.create("https://music.youtube.com/playlist?list=PL1")
        r2 = store.create("https://music.youtube.com/playlist?list=PL2")
        assert r1 and r2
        job1, _ = r1

        store.transition(job1.id, JobStatus.DOWNLOADING, started_at=clock())

        clock.advance(JobStore.TIMEOUT_SECONDS + 1)

        # Trigger timeout check
        store.get(job1.id)

        # Active slot should be cleared, allowing next job
        next_job = store.pop_next_pending()
        assert next_job is not None
        assert next_job.id == "job-0002"

    def test_get_all_checks_timeouts_on_all_jobs(
        self, store: JobStore, clock: Any
    ) -> None:
        """get_all should check timeouts on all jobs."""
        r1 = store.create("https://music.youtube.com/playlist?list=PL1")
        assert r1 is not None
        job1, _ = r1

        # Complete first job to free active slot
        store.transition(job1.id, JobStatus.COMPLETED)

        r2 = store.create("https://music.youtube.com/playlist?list=PL2")
        r3 = store.create("https://music.youtube.com/playlist?list=PL3")
        assert r2 and r3

        # Start both with timestamps
        store.transition(r2[0].id, JobStatus.DOWNLOADING, started_at=clock())
        clock.advance(10)
        store.transition(r3[0].id, JobStatus.DOWNLOADING, started_at=clock())

        # Advance past timeout for job2 but not job3
        clock.advance(JobStore.TIMEOUT_SECONDS - 5)

        jobs = store.get_all()

        job2 = next(j for j in jobs if j.id == "job-0002")
        job3 = next(j for j in jobs if j.id == "job-0003")

        assert job2.status == JobStatus.FAILED
        assert job3.status == JobStatus.DOWNLOADING


# =============================================================================
# Test Class: Thread Safety
# =============================================================================


class TestThreadSafety:
    """Tests for concurrent access to JobStore."""

    def test_concurrent_creates(self, clock: Any, id_generator: Any) -> None:
        """Multiple threads creating jobs should not cause race conditions."""
        store = JobStore(clock=clock, id_generator=id_generator)
        results: list[tuple[str, bool] | None] = []
        lock = threading.Lock()

        def create_job(i: int) -> None:
            result = store.create(f"https://music.youtube.com/playlist?list=PL{i}")
            with lock:
                if result:
                    results.append((result[0].id, result[1]))
                else:
                    results.append(None)

        threads = [threading.Thread(target=create_job, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All jobs should have been created
        valid_results = [r for r in results if r is not None]
        assert len(valid_results) == 10

        # Exactly one should have should_start=True
        start_count = sum(1 for _, should_start in valid_results if should_start)
        assert start_count == 1

        # All IDs should be unique
        ids = [r[0] for r in valid_results]
        assert len(set(ids)) == 10

    def test_concurrent_transitions(self, store: JobStore) -> None:
        """Concurrent transitions should not corrupt job state."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        progress_values: list[float] = []
        lock = threading.Lock()

        def update_progress(progress: float) -> None:
            store.transition(job.id, JobStatus.DOWNLOADING, progress=progress)
            updated = store.get(job.id)
            with lock:
                if updated:
                    progress_values.append(updated.progress)

        threads = [
            threading.Thread(target=update_progress, args=(i / 10,)) for i in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All progress updates should have happened
        assert len(progress_values) == 10

        # Final progress should be one of the valid values
        final = store.get(job.id)
        assert final is not None
        assert 0.0 <= final.progress <= 0.9

    def test_concurrent_cancel_and_transition(self, store: JobStore) -> None:
        """Concurrent cancel and transition should not cause issues."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        results: dict[str, bool | None] = {}
        lock = threading.Lock()

        def cancel_job() -> None:
            cancelled = store.cancel(job.id)
            with lock:
                results["cancel"] = cancelled

        def transition_job() -> None:
            updated = store.transition(job.id, JobStatus.DOWNLOADING)
            with lock:
                results["transition"] = updated is not None

        t1 = threading.Thread(target=cancel_job)
        t2 = threading.Thread(target=transition_job)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Job should end up in a valid state
        final = store.get(job.id)
        assert final is not None
        assert final.status in (JobStatus.CANCELLED, JobStatus.DOWNLOADING)

    def test_concurrent_pop_next_pending(self, store: JobStore) -> None:
        """Only one thread should successfully pop a pending job."""
        # Create first job (becomes active)
        r1 = store.create("https://music.youtube.com/playlist?list=PL1")
        assert r1 is not None

        # Create second job while first is active (so it stays PENDING)
        r2 = store.create("https://music.youtube.com/playlist?list=PL2")
        assert r2 is not None
        assert r2[1] is False  # Should NOT start immediately

        # Now complete first job to release active slot
        store.transition(r1[0].id, JobStatus.COMPLETED)

        results: list[str | None] = []
        lock = threading.Lock()

        def pop_job() -> None:
            job = store.pop_next_pending()
            with lock:
                results.append(job.id if job else None)

        threads = [threading.Thread(target=pop_job) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Exactly one thread should have gotten the job
        non_none = [r for r in results if r is not None]
        assert len(non_none) == 1
        assert non_none[0] == "job-0002"


# =============================================================================
# Test Class: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_job_with_empty_url(self, store: JobStore) -> None:
        """Should allow jobs with empty URL (validation is caller's responsibility)."""
        result = store.create("")
        assert result is not None
        job, _ = result
        assert job.url == ""

    def test_multiple_transitions_same_job(self, store: JobStore) -> None:
        """Multiple status transitions should be applied correctly."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        store.transition(job.id, JobStatus.FETCHING_INFO)
        store.transition(job.id, JobStatus.DOWNLOADING, progress=0.2)
        store.transition(job.id, JobStatus.DOWNLOADING, progress=0.5)
        store.transition(job.id, JobStatus.IMPORTING, progress=0.9)
        store.transition(job.id, JobStatus.COMPLETED, progress=1.0)

        final = store.get(job.id)
        assert final is not None
        assert final.status == JobStatus.COMPLETED
        assert final.progress == 1.0

    def test_transition_preserves_unset_fields(
        self, store: JobStore, sample_content_info: ContentInfo
    ) -> None:
        """Transition should not clear fields that aren't explicitly updated."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        # First transition sets content_info
        store.transition(
            job.id, JobStatus.DOWNLOADING, content_info=sample_content_info
        )

        # Second transition only updates progress
        store.transition(job.id, JobStatus.DOWNLOADING, progress=0.5)

        updated = store.get(job.id)
        assert updated is not None
        assert updated.content_info == sample_content_info
        assert updated.progress == 0.5

    def test_release_active_when_no_active_job(self, store: JobStore) -> None:
        """release_active should handle case with no active job."""
        # No jobs created yet
        released = store.release_active("nonexistent-id")
        assert released is False

    def test_cancel_does_not_release_active_slot(self, store: JobStore) -> None:
        """Cancelling a job should NOT automatically release the active slot."""
        r1 = store.create("https://music.youtube.com/playlist?list=PL1")
        r2 = store.create("https://music.youtube.com/playlist?list=PL2")
        assert r1 and r2

        job1, should_start = r1
        assert should_start is True

        # Cancel job1
        store.cancel(job1.id)

        # pop_next_pending should NOT return job2 yet (active slot still held)
        # because cancel doesn't release the active slot
        # The executor must call release_active after cleanup

        # Verify the active slot is still held by checking release_active succeeds
        released = store.release_active(job1.id)
        assert released is True

        # Now pop should work
        next_job = store.pop_next_pending()
        assert next_job is not None
        assert next_job.id == "job-0002"

    def test_get_returns_same_object_reference(self, store: JobStore) -> None:
        """Consecutive gets should return the same job object."""
        result = store.create("https://music.youtube.com/playlist?list=PLtest")
        assert result is not None
        job, _ = result

        job1 = store.get(job.id)
        job2 = store.get(job.id)

        assert job1 is job2

    def test_create_at_capacity_prunes_oldest_finished_first(
        self, clock: Any, id_generator: Any
    ) -> None:
        """When pruning, oldest finished job should be removed first."""
        store = JobStore(clock=clock, id_generator=id_generator)

        # Fill to capacity
        for i in range(JobStore.MAX_JOBS):
            store.create(f"https://music.youtube.com/playlist?list=PL{i}")

        # Complete jobs in reverse order (newest first)
        store.transition("job-0003", JobStatus.COMPLETED)
        store.transition("job-0002", JobStatus.COMPLETED)
        store.transition("job-0001", JobStatus.COMPLETED)

        # Create new job - should prune job-0001 (first in insertion order)
        store.create("https://music.youtube.com/playlist?list=PLnew")

        # job-0001 should be removed (oldest in OrderedDict)
        assert store.get("job-0001") is None
        # job-0002 and job-0003 should still exist
        assert store.get("job-0002") is not None
        assert store.get("job-0003") is not None
