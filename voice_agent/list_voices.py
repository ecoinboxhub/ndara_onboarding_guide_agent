"""Utility script to inspect available Nigerian voices from Google TTS."""

import asyncio
import json
import os
from pathlib import Path
import sys


current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

try:
    from .config import VoiceConfig  # type: ignore
    from .realtime.tts_google import GoogleTTS  # type: ignore
except ImportError:  # pragma: no cover
    from voice_agent.config import VoiceConfig
    from voice_agent.realtime.tts_google import GoogleTTS


async def main() -> None:
    config = VoiceConfig()

    if getattr(config, "GOOGLE_APPLICATION_CREDENTIALS", None):
        os.environ.setdefault(
            "GOOGLE_APPLICATION_CREDENTIALS", config.GOOGLE_APPLICATION_CREDENTIALS
        )

    tts = GoogleTTS(config)
    voices = await tts.get_voice_characteristics()
    print("Filtered Nigerian voices:")
    print(json.dumps(voices, indent=2))

    raw_voices = tts.client.list_voices().voices
    print(f"\nTotal voices available: {len(raw_voices)}")

    locales = set()
    for voice in raw_voices:
        locales.update(voice.language_codes)
    english_locales = sorted(code for code in locales if code.startswith("en"))
    print(f"Unique language codes: {len(locales)}")
    print("English locales (first 40):")
    print(json.dumps(english_locales[:40], indent=2))

    from google.cloud import texttospeech

    sample = []
    for voice in raw_voices[:20]:
        gender_enum = texttospeech.SsmlVoiceGender(voice.ssml_gender)
        sample.append(
            {
                "name": voice.name,
                "gender": gender_enum.name,
                "languages": list(voice.language_codes),
            }
        )
    print("\nSample of first 20 voices:")
    print(json.dumps(sample, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

