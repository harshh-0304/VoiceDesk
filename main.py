"""
VoiceDesk - Command Line Interface (CLI)

Provides an interactive terminal interface for chatting with VoiceDesk
via microphone audio or text chat mode with speech synthesis.
"""

import asyncio
import logging
import os
import shutil
import subprocess
import sys
from typing import Optional

from dotenv import load_dotenv

from asr import transcribe_audio
from llm import generate_response_async
from memory import ConversationMemory
from tts import text_to_speech
from utils.audio import is_microphone_available, record_microphone

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "WARNING").upper())
logger = logging.getLogger("VoiceDesk.CLI")


def load_system_prompt(path: str = "prompts/system_prompt.txt") -> str:
    """Load persona prompt from file or fallback to safe default."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    return content
        except Exception as exc:
            logger.warning(f"Failed to read {path}: {exc}")

    return (
        "You are VoiceDesk, an articulate AI assistant. "
        "Keep your answers concise, helpful, and natural."
    )


def play_audio_file(audio_path: str) -> None:
    """Attempt cross-platform playback of the generated audio file."""
    if not audio_path or not os.path.exists(audio_path):
        return

    # Check common system audio players
    for player in ["ffplay", "paplay", "aplay", "mpv", "afplay"]:
        bin_path = shutil.which(player)
        if bin_path:
            args = [bin_path, audio_path]
            if player == "ffplay":
                args = [bin_path, "-nodisp", "-autoexit", "-loglevel", "quiet", audio_path]
            try:
                subprocess.run(
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                return
            except Exception:
                continue

    # Fallback to playsound if available
    try:
        from playsound import playsound
        playsound(audio_path)
    except Exception:
        print(f"[*] Audio saved to {audio_path} (no audio player found in PATH).")


async def run_voice_turn(
    system_prompt: str,
    memory: ConversationMemory,
) -> bool:
    """Execute a single speech-to-speech turn."""
    input("\n[VoiceDesk] Press [ENTER] to record 5s of audio (or Ctrl+C to quit)... ")

    audio_file = record_microphone(output_path="temp_cli_input.wav", duration_seconds=5)
    if not audio_file or not os.path.exists(audio_file):
        print("[VoiceDesk] Could not record audio. Please check your microphone.")
        return True

    try:
        print("[VoiceDesk] Transcribing audio with Whisper...")
        user_text = await transcribe_audio(audio_file)
        if not user_text:
            print("[VoiceDesk] No speech detected. Please speak louder or closer to the mic.")
            return True

        print(f"\n[You]: {user_text}")
        memory.add_user(user_text)

        print("[VoiceDesk] Generating response...")
        reply = await generate_response_async(
            user_text=user_text,
            system_prompt=system_prompt,
            memory=memory,
        )
        print(f"[VoiceDesk]: {reply}\n")
        memory.add_assistant(reply)

        tts_output = text_to_speech(reply, output_path="temp_cli_reply.mp3")
        if tts_output:
            play_audio_file(tts_output)

        return True

    finally:
        if os.path.exists("temp_cli_input.wav"):
            try:
                os.remove("temp_cli_input.wav")
            except OSError:
                pass


async def run_text_turn(
    system_prompt: str,
    memory: ConversationMemory,
) -> bool:
    """Execute a single text turn with spoken audio playback."""
    user_text = input("\n[You] > ").strip()
    if not user_text:
        return True

    if user_text.lower() in {"q", "quit", "exit"}:
        return False

    if user_text.lower() == "/clear":
        memory.clear()
        print("[VoiceDesk] Conversation memory cleared.")
        return True

    memory.add_user(user_text)

    reply = await generate_response_async(
        user_text=user_text,
        system_prompt=system_prompt,
        memory=memory,
    )
    print(f"\n[VoiceDesk] > {reply}\n")
    memory.add_assistant(reply)

    tts_output = text_to_speech(reply, output_path="temp_cli_reply.mp3")
    if tts_output:
        play_audio_file(tts_output)

    return True


async def main() -> None:
    """Main CLI entrypoint."""
    print("=" * 60)
    print("      VOICEDESK - INTELLIGENT VOICE ASSISTANT")
    print("=" * 60)

    system_prompt = load_system_prompt()
    memory = ConversationMemory(max_messages=12)
    mic_ready = is_microphone_available()

    print(f"Microphone status: {'[DETECTED]' if mic_ready else '[NOT FOUND / DISABLED]'}")
    print("Select mode:")
    print("  [1] Voice Mode (Microphone speech-to-speech)")
    print("  [2] Text Chat Mode (Console input + Audio voice output)")
    print("  Type 'q' anytime to exit.\n")

    mode = "2"
    if mic_ready:
        selection = input("Choose mode [1 or 2, default=1]: ").strip()
        if selection in {"1", "2"}:
            mode = selection
        elif selection.lower() in {"q", "exit"}:
            print("Exiting VoiceDesk.")
            return
    else:
        print("[Notice] Defaulting to Text Chat Mode because microphone is unavailable.")
        mode = "2"

    try:
        active = True
        while active:
            if mode == "1":
                active = await run_voice_turn(system_prompt, memory)
            else:
                active = await run_text_turn(system_prompt, memory)

    except KeyboardInterrupt:
        print("\n\n[VoiceDesk] Session terminated by user. Goodbye!")
    finally:
        if os.path.exists("temp_cli_reply.mp3"):
            try:
                os.remove("temp_cli_reply.mp3")
            except OSError:
                pass


if __name__ == "__main__":
    asyncio.run(main())
