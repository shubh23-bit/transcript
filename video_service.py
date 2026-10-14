
import subprocess
from pathlib import Path

from groq import Groq, APIError

from config import (
    GROQ_API_KEY,
    MAX_AUDIO_SIZE,
    TRANSCRIPTION_MODEL,
)


def transcribe_video(video_path: Path) -> str:
    """Extract audio from a video and transcribe it using Groq."""

    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Check your .env file."
        )

    audio_path = video_path.with_suffix(".mp3")
    client = None

    try:
        command = [
            "ffmpeg",
            "-nostdin",
            "-y",
            "-i", str(video_path),
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-b:a", "48k",
            str(audio_path),
        ]

        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "FFmpeg was not found. Install it and check PATH."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "Audio extraction timed out."
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise ValueError(
                "The file could not be processed as a video. "
                "Check that the file is valid and contains audio."
            ) from exc

        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise ValueError("No usable audio was found in the video.")

        if audio_path.stat().st_size > MAX_AUDIO_SIZE:
            raise ValueError(
                "Extracted audio exceeds the 24 MB limit. "
                "Audio chunking will be added in a later phase."
            )

        client = Groq(api_key=GROQ_API_KEY, max_retries=2, timeout=180.0)

        try:
            with audio_path.open("rb") as audio_file:
                result = client.audio.transcriptions.create(
                    file=(audio_path.name, audio_file.read()),
                    model=TRANSCRIPTION_MODEL,
                    response_format="text",
                    temperature=0.0,
                )

            return str(result).strip()

        except APIError as exc:
            # Keep the detailed error in the server logs only.
            print(
                f"Groq API error: {type(exc).__name__}: {exc}"
            )
            raise RuntimeError(
                "Groq transcription failed. Check the API key, "
                "model access, rate limits, and account usage."
            ) from exc

    finally:
        if client is not None:
            client.close()

        audio_path.unlink(missing_ok=True)
