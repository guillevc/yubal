from unittest.mock import MagicMock

import pytest
from yubal_api.api.exceptions import QueueFullError
from yubal_api.api.routes.download import download


@pytest.mark.enable_socket
class TestDownloadEndpoint:
    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        return MagicMock()

    @pytest.mark.asyncio
    async def test_happy_path(self, mock_executor: MagicMock) -> None:
        # 4a. Happy path — valid URL, job created
        mock_job = MagicMock()
        mock_job.id = "job-123"
        mock_executor.create_and_start_job.return_value = mock_job

        response = await download(
            job_executor=mock_executor,
            url="https://music.youtube.com/playlist?list=OLAK5uy_abcdef...",
        )
        assert response.id == "job-123"
        assert response.message == "Job created"

    @pytest.mark.asyncio
    async def test_queue_full(self, mock_executor: MagicMock) -> None:
        # 4b. Queue full
        mock_executor.create_and_start_job.return_value = None

        with pytest.raises(QueueFullError):
            await download(
                job_executor=mock_executor,
                url="https://music.youtube.com/playlist?list=OLAK5uy_abcdef...",
            )

    @pytest.mark.asyncio
    async def test_invalid_url(self, mock_executor: MagicMock) -> None:
        # 4c. Invalid URL
        with pytest.raises(ValueError):
            await download(
                job_executor=mock_executor, url="https://example.com/not-youtube"
            )

    @pytest.mark.asyncio
    async def test_max_items_forwarded(self, mock_executor: MagicMock) -> None:
        # 4d. max_items forwarded correctly
        mock_job = MagicMock()
        mock_job.id = "job-456"
        mock_executor.create_and_start_job.return_value = mock_job

        await download(
            job_executor=mock_executor,
            url="https://music.youtube.com/watch?v=12345678901",
            max_items=5,
        )
        mock_executor.create_and_start_job.assert_called_once_with(
            "https://music.youtube.com/watch?v=12345678901", 5
        )
