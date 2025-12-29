"""Tests for yubal.core.enums."""

import pytest

from yubal.core.enums import JobStatus, ProgressStep


class TestJobStatus:
    """Tests for JobStatus enum."""

    @pytest.mark.parametrize(
        "status",
        [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED],
    )
    def test_is_finished_returns_true_for_terminal_states(self, status: JobStatus):
        """Terminal states (completed, failed, cancelled) should be finished."""
        assert status.is_finished is True

    @pytest.mark.parametrize(
        "status",
        [
            JobStatus.PENDING,
            JobStatus.FETCHING_INFO,
            JobStatus.DOWNLOADING,
            JobStatus.IMPORTING,
        ],
    )
    def test_is_finished_returns_false_for_active_states(self, status: JobStatus):
        """Active states (pending, in-progress) should not be finished."""
        assert status.is_finished is False

    def test_all_statuses_have_string_values(self):
        """All statuses should have valid string values."""
        for status in JobStatus:
            assert isinstance(status.value, str)
            assert len(status.value) > 0

    def test_status_values_are_lowercase(self):
        """Status values should be lowercase for JSON serialization."""
        for status in JobStatus:
            assert status.value == status.value.lower()


class TestProgressStep:
    """Tests for ProgressStep enum."""

    def test_progress_steps_have_string_values(self):
        """All progress steps should have valid string values."""
        for step in ProgressStep:
            assert isinstance(step.value, str)
            assert len(step.value) > 0

    def test_progress_step_values_match_job_status(self):
        """ProgressStep values should match corresponding JobStatus values."""
        # These steps should have matching values in JobStatus
        matching_steps = [
            (ProgressStep.FETCHING_INFO, JobStatus.FETCHING_INFO),
            (ProgressStep.DOWNLOADING, JobStatus.DOWNLOADING),
            (ProgressStep.IMPORTING, JobStatus.IMPORTING),
            (ProgressStep.COMPLETED, JobStatus.COMPLETED),
            (ProgressStep.FAILED, JobStatus.FAILED),
        ]
        for progress_step, job_status in matching_steps:
            assert progress_step.value == job_status.value
