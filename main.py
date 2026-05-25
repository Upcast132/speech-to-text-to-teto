"""
speech-to-text-to-teto
Convierte voz a texto y lo reproduce con la voz de Teto via OpenUTAU CLI.
"""

import random
import string
import os
import time
import subprocess
import sys
import signal
import logging
from pathlib import Path

# ── Configuración ────────────────────────────────────────────────────────────

# Ruta al ejecutable de OpenUTAU (ajustar según tu sistema)
# Windows: r"C:\Program Files\OpenUtau\OpenUtau.exe"
# Linux:   "/usr/bin/openutau" o donde lo tengas
OPENUTAU_PATH = Path(r"C:\Program Files\OpenUtau\OpenUtau.exe")

# Dispositivo de audio de salida (None = default del sistema)
# Para Discord/juegos: nombre del cable virtual, ej: "CABLE Input (VB-Audio Virtual Cable)"
# En Linux con PipeWire: nombre del sink virtual que hayas creado
AUDIO_OUTPUT_DEVICE = None

# Idioma del reconocimiento de voz
STT_LANGUAGE = "en"

# Rango de tonos MIDI para las notas (61-64 = D4-E4, zona cómoda de Teto)
TONE_MIN = 61
TONE_MAX = 64

# Multiplicador de duración por sílaba (en ticks de OpenUTAU, 480 = 1 beat a 120bpm)
DURATION_PER_SYLLABLE = 240

# Timeout para el render de OpenUTAU (segundos)
RENDER_TIMEOUT = 30

# ── Setup ────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

BASE_DIR   = Path(__file__).parent
TEMP_DIR   = BASE_DIR / "temp"
TEMPLATES  = BASE_DIR / "templates"

TEMP_DIR.mkdir(exist_ok=True)

# ── Utilidades ───────────────────────────────────────────────────────────────

def random_name(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def count_syllables(word: str) -> int:
    """
    Estimación rápida de sílabas en inglés.
    No es perfecta pero es mejor que contar caracteres.
    """
    word = word.lower().strip(".,!?'\"")
    if not word:
        return 1
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    # "e" muda al final
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def load_template(name: str) -> str:
    path = TEMPLATES / name
    if not path.exists():
        raise FileNotFoundError(f"Template no encontrado: {path}")
    return path.read_text(encoding="utf-8")

# ── Generación de USTX ───────────────────────────────────────────────────────

def build_ustx(text: str, output_path: Path) -> None:
    """Construye el archivo .ustx a partir del texto reconocido."""
    words = [w for w in text.split() if w]  # ignorar espacios extra
    if not words:
        raise ValueError("Texto vacío, nada que convertir.")

    file_template  = load_template("template.txt")
    word_template  = load_template("word.txt")

    segments = []
    total_dur = 0

    for word in words:
        syllables = count_syllables(word)
        duration  = syllables * DURATION_PER_SYLLABLE
        tone      = random.randint(TONE_MIN, TONE_MAX)

        # Limpiar palabra para el lyric (OpenUTAU no acepta puntuación aquí)
        lyric = word.translate(str.maketrans("", "", ".,!?'\"-"))

        segment = (word_template
                   .replace("POS__",  str(total_dur))
                   .replace("DUR__",  str(duration))
                   .replace("WORD__", lyric)
                   .replace("TONE__", str(tone)))

        segments.append(segment)
        total_dur += duration

    content = file_template + "\n" + "\n".join(segments) + "\nwave_parts: []"
    output_path.write_text(content, encoding="utf-8")
    log.info(f"USTX generado: {output_path.name} ({len(words)} palabras)")

# ── Render y reproducción ────────────────────────────────────────────────────

def render_ustx(ustx_path: Path) -> Path:
    """
    Llama a OpenUTAU en modo CLI para renderizar el .ustx a WAV.
    OpenUTAU escribe el WAV en el mismo directorio con el mismo nombre.
    """
    wav_path = ustx_path.with_suffix(".wav")

    if not OPENUTAU_PATH.exists():
        raise FileNotFoundError(
            f"OpenUTAU no encontrado en: {OPENUTAU_PATH}\n"
            "Ajusta OPENUTAU_PATH en la configuración."
        )

    cmd = [str(OPENUTAU_PATH), "--render", str(ustx_path), str(wav_path)]
    log.info("Renderizando con OpenUTAU...")

    try:
        result = subprocess.run(
            cmd,
            timeout=RENDER_TIMEOUT,
            capture_output=True,
            text=True
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"OpenUTAU tardó más de {RENDER_TIMEOUT}s, abortando.")

    if result.returncode != 0:
        raise RuntimeError(f"OpenUTAU error:\n{result.stderr}")

    if not wav_path.exists():
        raise RuntimeError("OpenUTAU terminó pero no generó el WAV.")

    log.info(f"WAV generado: {wav_path.name}")
    return wav_path


def play_wav(wav_path: Path) -> None:
    """
    Reproduce el WAV en el dispositivo de salida configurado.
    Usa sounddevice + soundfile para control preciso del dispositivo.
    """
    try:
        import sounddevice as sd
        import soundfile as sf
    except ImportError:
        log.error("Instala: pip install sounddevice soundfile")
        raise

    data, samplerate = sf.read(str(wav_path))

    if AUDIO_OUTPUT_DEVICE:
        log.info(f"Reproduciendo en: {AUDIO_OUTPUT_DEVICE}")
    else:
        log.info("Reproduciendo en dispositivo default...")

    sd.play(data, samplerate, device=AUDIO_OUTPUT_DEVICE, blocking=True)


def cleanup(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
        path.with_suffix(".wav").unlink(missing_ok=True)
    except Exception:
        pass

# ── Main loop ────────────────────────────────────────────────────────────────

def process_text(text: str) -> None:
    """Pipeline completo: texto → ustx → wav → reproducción."""
    if not text.strip():
        return

    name     = random_name()
    ustx     = TEMP_DIR / f"{name}.ustx"
    wav      = TEMP_DIR / f"{name}.wav"

    try:
        build_ustx(text, ustx)
        wav = render_ustx(ustx)
        play_wav(wav)
    except Exception as e:
        log.error(f"Error procesando '{text[:40]}...': {e}")
    finally:
        cleanup(ustx)


def main() -> None:
    try:
        from RealtimeSTT import AudioToTextRecorder
    except ImportError:
        log.error("Instala RealtimeSTT: pip install RealtimeSTT")
        sys.exit(1)

    log.info("Iniciando... espera 'speak now'")

    recorder = AudioToTextRecorder(language=STT_LANGUAGE)

    # Salida limpia con Ctrl+C
    def shutdown(sig, frame):
        log.info("Deteniendo...")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)

    while True:
        text = recorder.text()
        if text:
            log.info(f"Escuchado: {text}")
            process_text(text)


if __name__ == "__main__":
    main()
