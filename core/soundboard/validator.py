import re
import json
import logging
import asyncio
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Sound constraints
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_DURATION_SECONDS = 6.0
NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{2,32}$")
RESERVED_NAMES = {"add", "play", "list", "all", "help", "info", "delete", "remove"}


def validate_sound_name(name: str) -> tuple[bool, str]:
    """
    Validates sound name for allowed characters, length, and reserved keywords.
    Returns (is_valid, error_message).
    """
    clean_name = name.strip()
    if not clean_name:
        return False, "Sound name cannot be empty."

    if clean_name.lower() in RESERVED_NAMES:
        return False, f"`{clean_name}` is a reserved subcommand keyword. Please choose another name."

    if not NAME_PATTERN.match(clean_name):
        return (
            False,
            "Sound name must be between 2 and 32 characters and only contain letters, numbers, underscores, or hyphens.",
        )

    return True, ""


def validate_attachment_size(file_size: int) -> tuple[bool, str]:
    """
    Validates file size does not exceed MAX_FILE_SIZE.
    Returns (is_valid, error_message).
    """
    if file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        actual_mb = file_size / (1024 * 1024)
        return False, f"File size is too large ({actual_mb:.2f} MB). Maximum allowed is {max_mb:.0f} MB."
    return True, ""


def _run_ffprobe(file_path: Path) -> subprocess.CompletedProcess:
    """Synchronous worker to execute ffprobe, intended to be called in an executor thread."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=15)


async def probe_audio(file_path: Path) -> tuple[bool, float, str]:
    """
    Inspects an audio file using ffprobe to confirm:
    1. The file is a valid audio format recognized and playable by FFmpeg.
    2. The clip duration is within MAX_DURATION_SECONDS (6.0s).

    Returns:
        (is_valid, duration_in_seconds, error_message)
    """
    try:
        proc = await asyncio.to_thread(_run_ffprobe, file_path)
    except FileNotFoundError:
        logger.error("ffprobe executable was not found on the system PATH.")
        return False, 0.0, "Audio processing system (`ffprobe`) is not installed on the host."
    except subprocess.TimeoutExpired:
        logger.warning(f"ffprobe timed out while analyzing {file_path}")
        return False, 0.0, "Audio analysis timed out. The file may be corrupt or too complex."
    except Exception as e:
        logger.error(f"Unexpected error executing ffprobe: {e}", exc_info=True)
        return False, 0.0, "An error occurred while analyzing the audio file."

    if proc.returncode != 0 or not proc.stdout:
        logger.warning(f"ffprobe failed on {file_path} with code {proc.returncode}: {proc.stderr}")
        return False, 0.0, "The file could not be recognized as a valid playable audio file."

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode ffprobe output: {e}", exc_info=True)
        return False, 0.0, "Failed to inspect audio metadata."

    # Check for presence of an audio stream
    audio_streams = [
        s for s in data.get("streams", [])
        if s.get("codec_type") == "audio"
    ]
    if not audio_streams:
        return False, 0.0, "The uploaded file does not contain any valid audio stream."

    # Extract duration from audio stream or container format
    duration: float = 0.0
    for stream in audio_streams:
        if "duration" in stream:
            try:
                duration = float(stream["duration"])
                if duration > 0:
                    break
            except (ValueError, TypeError):
                pass

    if duration <= 0:
        format_info = data.get("format", {})
        if "duration" in format_info:
            try:
                duration = float(format_info["duration"])
            except (ValueError, TypeError):
                pass

    if duration <= 0:
        return False, 0.0, "Could not determine audio duration. The file may be corrupted."

    if duration > MAX_DURATION_SECONDS:
        return (
            False,
            duration,
            f"Audio clip is too long ({duration:.2f}s). Maximum allowed duration is {MAX_DURATION_SECONDS:.0f} seconds.",
        )

    return True, duration, ""

