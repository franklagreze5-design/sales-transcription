"""Microphone diagnostics for setup and calibration."""

from __future__ import annotations

import argparse
import queue
import time

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv

from sales_transcriber.config import _optional_device


def list_input_devices() -> None:
    """Print available input devices and their indexes."""

    hostapis = sd.query_hostapis()
    devices = sd.query_devices()
    print("Dispositivos de entrada disponibles:\n")
    for index, device in enumerate(devices):
        if int(device.get("max_input_channels", 0)) > 0:
            default_marker = " (default)" if index == sd.default.device[0] else ""
            hostapi = hostapis[int(device["hostapi"])]["name"]
            print(
                f"{index}: {device['name']}{default_marker} | "
                f"hostapi={hostapi} | "
                f"canales={device['max_input_channels']} | "
                f"sample_rate={int(device['default_samplerate'])}"
            )


def measure_input_level(
    device: str | int | None,
    sample_rate: int | None,
    seconds: int,
    mode: str,
) -> None:
    """Print a simple live level meter for the selected microphone."""

    audio_queue: queue.Queue[bytes] = queue.Queue()

    def on_audio(indata: np.ndarray, frames: int, time_info: object, status: sd.CallbackFlags) -> None:
        if status:
            print(f"[Audio] Advertencia: {status}")
        audio_queue.put(indata.copy().tobytes())

    selected = sd.query_devices(device=device, kind="input")
    effective_sample_rate = sample_rate or int(selected["default_samplerate"])

    print(f"\nDispositivo: {selected['name']}")
    print(f"Sample rate: {effective_sample_rate} Hz")
    print(f"Modo: {mode}")
    print("Medicion de nivel. Habla cerca del microfono durante la prueba.\n")

    try:
        if mode == "blocking":
            peak = _measure_blocking(device, effective_sample_rate, seconds)
        else:
            peak = _measure_callback(device, effective_sample_rate, seconds, audio_queue, on_audio)
    except Exception as exc:
        print(f"No se pudo abrir ese microfono: {exc}")
        print("Prueba otro indice con: sales-audio-check --device <indice>")
        return

    print(f"\nRMS maximo detectado: {peak:.1f}")
    if peak == 0:
        print("Resultado: el stream abrio, pero no llegaron muestras de audio.")
    elif peak < 50:
        print("Resultado: no parece estar entrando audio. Revisa permisos, dispositivo o entrada seleccionada.")
    elif peak < 350:
        print("Resultado: entra audio bajo. Prueba AUDIO_MIN_RMS=100 o AUDIO_MIN_RMS=150.")
    else:
        print("Resultado: el microfono recibe audio. Puedes usar AUDIO_MIN_RMS entre 250 y 500.")


def _print_level(rms: float) -> None:
    """Print one RMS measurement as a small level meter."""

    bar = "#" * min(60, int(rms / 120))
    print(f"RMS={rms:7.1f} | {bar}", flush=True)


def _rms_from_array(data: np.ndarray) -> float:
    """Calculate RMS from a NumPy audio buffer."""

    if data.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(data.astype(np.float32) ** 2)))


def _measure_blocking(device: str | int | None, sample_rate: int, seconds: int) -> float:
    """Measure levels using blocking reads instead of callback delivery."""

    peak = 0.0
    block_frames = max(1, sample_rate // 2)
    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="int16", device=device) as stream:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            data, overflowed = stream.read(block_frames)
            if overflowed:
                print("[Audio] Overflow de entrada")
            rms = _rms_from_array(data)
            peak = max(peak, rms)
            _print_level(rms)
    return peak


def _measure_callback(
    device: str | int | None,
    sample_rate: int,
    seconds: int,
    audio_queue: queue.Queue[bytes],
    on_audio,
) -> float:
    """Measure levels using the callback-based stream used by the app."""

    peak = 0.0
    started_at = time.monotonic()
    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        device=device,
        callback=on_audio,
    ):
        while time.monotonic() - started_at < seconds:
            try:
                block = audio_queue.get(timeout=1)
            except queue.Empty:
                print("Sin muestras recibidas aun...", flush=True)
                continue
            rms = _rms_from_array(np.frombuffer(block, dtype=np.int16))
            peak = max(peak, rms)
            _print_level(rms)
    return peak


def main() -> None:
    """Run microphone diagnostics from the command line."""

    load_dotenv()
    parser = argparse.ArgumentParser(description="Diagnostica dispositivos y nivel de microfono.")
    parser.add_argument("--list", action="store_true", help="Lista dispositivos de entrada.")
    parser.add_argument("--device", help="Indice o nombre del dispositivo de entrada.")
    parser.add_argument("--seconds", type=int, default=8, help="Duracion de la medicion.")
    parser.add_argument("--sample-rate", type=int, help="Frecuencia de muestreo. Por defecto usa la nativa.")
    parser.add_argument(
        "--mode",
        choices=["callback", "blocking"],
        default="blocking",
        help="Forma de lectura del microfono.",
    )
    args = parser.parse_args()

    if args.list:
        list_input_devices()
        return

    measure_input_level(
        device=_optional_device(args.device),
        sample_rate=args.sample_rate,
        seconds=args.seconds,
        mode=args.mode,
    )


if __name__ == "__main__":
    main()
