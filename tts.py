from gtts import gTTS
import os
import subprocess

def text_to_speech(
    text: str,
    output_path: str = "reply.mp3",
    lang: str = "en",
    speed: float = 1.35
) -> str:

    # Make base audio
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(output_path)

    # If speed is 1.0 → no change
    if speed == 1.0:
        return output_path

    # Create a new faster audio
    fast_output = "reply_fast.mp3"
    speed_cmd = f"ffmpeg -y -i {output_path} -filter:a atempo={speed} {fast_output}"
    subprocess.run(speed_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return fast_output
