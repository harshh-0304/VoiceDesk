# Placeholder code
import os
import sys
from dotenv import load_dotenv
from playsound import playsound

from utils.audio import record_microphone
from asr import transcribe_audio
from llm import generate_response
from tts import text_to_speech
from memory import ConversationMemory

load_dotenv()


def load_system_prompt(path: str = "prompts/system_prompt.txt") -> str:
    if not os.path.exists(path):
        print(f"[VoiceDesk] System prompt file not found at {path}. Using fallback.")
        return (
            "You are a helpful, concise support assistant. "
            "If you are unsure, say you are unsure."
        )
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main() -> None:
    print("=" * 50)
    print("      VoiceDesk – AI Voice Support Agent")
    print("      Say something, or type 'q' to quit.")
    print("=" * 50)

    system_prompt = load_system_prompt()
    memory = ConversationMemory(max_messages=12)

    try:
        while True:
            cmd = input("\n[VoiceDesk] Press ENTER to speak, or type 'q' to quit: ").strip()
            if cmd.lower() in {"q", "quit", "exit"}:
                print("[VoiceDesk] Goodbye 👋")
                break

            # 1. Record audio
            audio_path = record_microphone(output_path="input.wav", duration_seconds=5)

            # 2. ASR – speech to text
            user_text = transcribe_audio(audio_path)
            if not user_text:
                print("[VoiceDesk] Didn't catch that. Let's try again.")
                continue

            print(f"\n[User] {user_text}")
            memory.add_user(user_text)

            # 3. LLM – generate reply
            reply_text = generate_response(
                user_text=user_text,
                system_prompt=system_prompt,
                memory=memory,
            )
            print(f"[VoiceDesk] {reply_text}")
            memory.add_assistant(reply_text)

            # 4. TTS – reply in voice
            tts_path = text_to_speech(reply_text, output_path="reply.mp3")
            if tts_path:
                try:
                    playsound(tts_path)
                except Exception as e:
                    print(f"[VoiceDesk] Could not play audio: {e}")

    except KeyboardInterrupt:
        print("\n[VoiceDesk] Interrupted. Goodbye 👋")
        sys.exit(0)


if __name__ == "__main__":
    main()
