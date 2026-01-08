"""Cookies management endpoints."""

import asyncio

from fastapi import APIRouter, HTTPException, status

from yubal.api.dependencies import CookiesFileDep, YtdlpDirDep
from yubal.schemas.cookies import (
    CookiesStatusResponse,
    CookiesUploadRequest,
    CookiesUploadResponse,
)

router = APIRouter(prefix="/cookies", tags=["cookies"])


@router.get("/status")
async def cookies_status(cookies_file: CookiesFileDep) -> CookiesStatusResponse:
    """Check if cookies file is configured."""
    exists = await asyncio.to_thread(cookies_file.exists)
    return CookiesStatusResponse(configured=exists)


@router.post("")
async def upload_cookies(
    body: CookiesUploadRequest,
    cookies_file: CookiesFileDep,
    ytdlp_dir: YtdlpDirDep,
) -> CookiesUploadResponse:
    """Upload cookies.txt content (Netscape format)."""
    if not body.content.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty cookie file")
    # Basic validation: Netscape cookie format starts with comment or domain
    first_line = body.content.split("\n")[0]
    if not first_line.startswith(("#", ".")):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Invalid cookie file format (expected Netscape format)",
        )

    await asyncio.to_thread(ytdlp_dir.mkdir, parents=True, exist_ok=True)
    await asyncio.to_thread(cookies_file.write_text, body.content)
    return CookiesUploadResponse(status="ok")


@router.delete("")
async def delete_cookies(cookies_file: CookiesFileDep) -> CookiesUploadResponse:
    """Delete cookies file."""
    if await asyncio.to_thread(cookies_file.exists):
        await asyncio.to_thread(cookies_file.unlink)
    return CookiesUploadResponse(status="ok")
