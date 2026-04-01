"""Local Nigerian voice synthesis smoke test."""

import asyncio
import os
import sys
from pathlib import Path


current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

try:
    from .config import VoiceConfig  # type: ignore
    from .realtime.tts_google import GoogleTTS  # type: ignore
except ImportError:  # pragma: no cover - fallback for script execution
    from voice_agent.config import VoiceConfig
    from voice_agent.realtime.tts_google import GoogleTTS


async def synthesize_sample(text: str, output_format: str = "MP3") -> Path:
    """Synthesize a sample phrase using the configured Nigerian voice."""

    os.environ.setdefault("VOICE_NAME", "en-NG-Standard-A")

    config = VoiceConfig()

    if getattr(config, "GOOGLE_APPLICATION_CREDENTIALS", None):
        os.environ.setdefault(
            "GOOGLE_APPLICATION_CREDENTIALS", config.GOOGLE_APPLICATION_CREDENTIALS
        )

    tts = GoogleTTS(config)
    audio_bytes = await tts.synthesize_speech(text=text, output_format=output_format)

    if not audio_bytes:
        raise RuntimeError("Voice synthesis returned no data. Check Google Cloud logs.")

    out_dir = Path.cwd() / "voice_samples"
    out_dir.mkdir(parents=True, exist_ok=True)

    file_name = f"nigerian_voice_test.{output_format.lower()}"
    out_path = out_dir / file_name
    out_path.write_bytes(audio_bytes)

    return out_path


async def main() -> None:
    sample_text = (
        "Hi there, I am from NDARA AI. We automate AI for businesses to improve their "
        "sales and closed sales. Please if you need anything, you can feel free to "
        "reach out to me."
    )

    output_path = await synthesize_sample(sample_text)
    print(f"Saved Nigerian voice sample to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())

