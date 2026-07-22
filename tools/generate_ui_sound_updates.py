"""Generate the maintained scan-success and collapse whoosh WAV cues."""

from __future__ import annotations

from array import array
import math
from pathlib import Path
import random
import wave


ROOT = Path(__file__).resolve().parents[1]
SOUNDS = ROOT / "sounds"
SAMPLE_RATE = 44_100


def envelope(time_value: float, start: float, duration: float, attack: float = 0.012) -> float:
    offset = time_value - start
    if offset < 0 or offset >= duration:
        return 0.0
    if offset < attack:
        return offset / max(attack, 0.001)
    release_start = duration * 0.42
    if offset <= release_start:
        return 1.0
    return max(1.0 - ((offset - release_start) / max(duration - release_start, 0.001)), 0.0) ** 1.8


def add_tone(samples: list[float], frequency: float, start: float, duration: float, gain: float, harmonic: float = 0.14) -> None:
    first = max(int(start * SAMPLE_RATE), 0)
    last = min(int((start + duration) * SAMPLE_RATE), len(samples))
    for index in range(first, last):
        time_value = index / SAMPLE_RATE
        phase = 2.0 * math.pi * frequency * (time_value - start)
        value = math.sin(phase) + harmonic * math.sin((phase * 2.0) + 0.35)
        samples[index] += value * envelope(time_value, start, duration) * gain


def add_whoosh(samples: list[float], start_frequency: float, end_frequency: float, seed: int) -> None:
    randomizer = random.Random(seed)
    filtered_noise = 0.0
    phase = 0.0
    length = len(samples)
    for index in range(length):
        progress = index / max(length - 1, 1)
        shaped = math.sin(math.pi * progress) ** 1.45
        noise = randomizer.uniform(-1.0, 1.0)
        filtered_noise = (filtered_noise * 0.82) + (noise * 0.18)
        frequency = start_frequency + ((end_frequency - start_frequency) * (progress ** 0.85))
        phase += (2.0 * math.pi * frequency) / SAMPLE_RATE
        airy = (filtered_noise * 0.36) + (math.sin(phase) * 0.18)
        samples[index] += airy * shaped


def write_wav(name: str, samples: list[float]) -> None:
    peak = max(max(abs(value) for value in samples), 0.001)
    scale = (0.82 * 32767.0) / peak
    pcm = array("h", (int(max(-32767, min(32767, value * scale))) for value in samples))
    path = SOUNDS / name
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(pcm.tobytes())


def build_scan_success() -> list[float]:
    samples = [0.0] * int(SAMPLE_RATE * 0.58)
    randomizer = random.Random(9701)
    for index in range(int(SAMPLE_RATE * 0.026)):
        progress = index / max(int(SAMPLE_RATE * 0.026) - 1, 1)
        samples[index] += randomizer.uniform(-1.0, 1.0) * ((1.0 - progress) ** 3.2) * 0.12
    add_tone(samples, 523.25, 0.018, 0.24, 0.16)
    add_tone(samples, 659.25, 0.105, 0.28, 0.19)
    add_tone(samples, 783.99, 0.205, 0.29, 0.21)
    add_tone(samples, 1046.50, 0.305, 0.22, 0.11, harmonic=0.07)
    return samples


def main() -> None:
    SOUNDS.mkdir(parents=True, exist_ok=True)
    write_wav("scan_success.wav", build_scan_success())

    opening = [0.0] * int(SAMPLE_RATE * 0.25)
    add_whoosh(opening, 260.0, 1_100.0, 9702)
    write_wav("collapse_open.wav", opening)

    closing = [0.0] * int(SAMPLE_RATE * 0.22)
    add_whoosh(closing, 1_050.0, 220.0, 9703)
    write_wav("collapse_close.wav", closing)


if __name__ == "__main__":
    main()
