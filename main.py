
import asyncio
from pathlib import Path
from uuid import uuid4
from fastapi.responses import FileResponse

from interview_service import extract_interview_qa
from pdf_service import create_interview_pdf

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel


from config import (
    ALLOWED_VIDEO_EXTENSIONS,
    MAX_VIDEO_SIZE,
    STORAGE_DIR,
    BASE_DIR,
)

from video_service import transcribe_video


app = FastAPI(
    title="AI Interview Video Assistant",
    description="Upload an interview video and generate its transcript.",
    version="0.1.0",
)


class TranscriptResponse(BaseModel):
    filename: str
    transcript: str
    character_count: int


FRONTEND_FILE = BASE_DIR / "frontend" / "index.html"


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND_FILE)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/v1/videos/transcribe", response_model=TranscriptResponse)
async def upload_and_transcribe(
    file: UploadFile = File(...),
):
    video_path = None

    try:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="A filename is required.",
            )

        extension = Path(file.filename).suffix.lower()

        if extension not in ALLOWED_VIDEO_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail="Unsupported video extension.",
            )

        # Generate our own filename; never trust a client-supplied path.
        video_path = STORAGE_DIR / f"{uuid4().hex}{extension}"

        total_size = 0

        # Read incrementally instead of loading the entire upload into RAM.
        with video_path.open("wb") as destination:
            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > MAX_VIDEO_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Video exceeds the {MAX_VIDEO_SIZE // (1024 * 1024)} MB upload limit.",
                    )

                destination.write(chunk)

        if total_size == 0:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        # FFmpeg and the API client are blocking operations.
        # Run them in a worker thread instead of blocking the event loop.
        try:
            transcript = await asyncio.to_thread(
                transcribe_video,
                video_path,
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc
        except RuntimeError as exc:
            raise HTTPException(
                status_code=502,
                detail=str(exc),
            ) from exc

        return TranscriptResponse(
            filename=Path(file.filename).name,
            transcript=transcript,
            character_count=len(transcript),
        )

    finally:
        if video_path is not None:
            video_path.unlink(missing_ok=True)

        await file.close()

@app.post("/api/v1/videos/interview-pdf")
async def create_interview_pdf_from_video(
    file: UploadFile = File(...),
):
    video_path = None

    try:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="A filename is required.",
            )

        extension = Path(file.filename).suffix.lower()

        if extension not in ALLOWED_VIDEO_EXTENSIONS:
            raise HTTPException(
                status_code=415,
                detail="Unsupported video extension.",
            )

        video_path = STORAGE_DIR / f"{uuid4().hex}{extension}"
        total_size = 0

        with video_path.open("wb") as destination:
            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > MAX_VIDEO_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Video exceeds the {MAX_VIDEO_SIZE // (1024 * 1024)} MB upload limit.",
                    )

                destination.write(chunk)

        if total_size == 0:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        try:
            transcript = await asyncio.to_thread(
                transcribe_video,
                video_path,
            )

            interview_data = await asyncio.to_thread(
                extract_interview_qa,
                transcript,
            )

            pdf_path = await asyncio.to_thread(
                create_interview_pdf,
                interview_data,
                Path(file.filename).name,
            )

        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc
        except RuntimeError as exc:
            raise HTTPException(
                status_code=502,
                detail=str(exc),
            ) from exc

        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=pdf_path.name,
            headers={
                "X-PDF-Saved-To": str(pdf_path.relative_to(BASE_DIR))
            },
        )

    finally:
        if video_path is not None:
            video_path.unlink(missing_ok=True)

        await file.close()

