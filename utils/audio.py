# Placeholder code
import wave
import pyaudio


def record_microphone(
    output_path: str = "input.wav",
    duration_seconds: int = 5,
    rate: int = 16000,
) -> str:
    """
    Records audio from the default microphone and saves it as a WAV file.

    :param output_path: Path to save the recorded audio.
    :param duration_seconds: Length of recording.
    :param rate: Sample rate compatible with most ASR models.
    :return: Path to the saved audio file.
    """
    chunk = 1024
    fmt = pyaudio.paInt16
    channels = 1

    audio_interface = pyaudio.PyAudio()

    print(f"[VoiceDesk] Recording for {duration_seconds} seconds...")
    stream = audio_interface.open(
        format=fmt,
        channels=channels,
        rate=rate,
        input=True,
        frames_per_buffer=chunk,
    )

    frames = []
    for _ in range(int(rate / chunk * duration_seconds)):
        data = stream.read(chunk)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    audio_interface.terminate()

    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(audio_interface.get_sample_size(fmt))
        wf.setframerate(rate)
        wf.writeframes(b"".join(frames))

    print(f"[VoiceDesk] Audio saved to {output_path}")
    return output_path
