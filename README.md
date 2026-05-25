# speech-to-text-to-teto

Converts your speech to text and plays it back through Teto's voice using OpenUTAU as a headless renderer. No GUI required.

---

## Requirements

- Python 3.10 or higher
- OpenUTAU with the Kasane Teto voicebank installed
- A working microphone
- (Optional) A virtual audio cable if you want to route output to Discord or a game

---

## Dependencies

Install Python dependencies:

```
pip install -r requirements.txt
```

The requirements file installs:

- RealtimeSTT — microphone speech recognition
- sounddevice — audio playback with device selection
- soundfile — WAV file reading

RealtimeSTT will download a Whisper model on first run. The default is `tiny.en`, which is fast and small. Expect a few seconds on first launch.

---

## OpenUTAU setup

1. Download and install OpenUTAU from https://github.com/stakira/OpenUtau
2. Install the Kasane Teto English voicebank inside OpenUTAU
3. Verify the voicebank works by creating a test project manually before running this program
4. Note the path to your OpenUTAU executable

---

## Configuration

Open `main.py` and edit the variables at the top of the file:

```python
OPENUTAU_PATH = Path(r"C:\Program Files\OpenUtau\OpenUtau.exe")
```

Set this to wherever OpenUTAU is installed on your system.

```python
AUDIO_OUTPUT_DEVICE = None
```

Leave as `None` to use your default audio output. Change to a device name string to route audio elsewhere. See the routing section below for details.

```python
STT_LANGUAGE = "en"
```

Language code for speech recognition.

---

## Running

```
python main.py
```

Wait for the program to print "speak now", then speak. It will transcribe your voice, render it through Teto, and play it back.

Press Ctrl+C to stop.

---

## Routing audio to Discord or a game

The program lets you select a specific audio output device. This means you can route Teto's voice to a virtual cable and use that cable as a microphone input in Discord or any game.

### Windows

1. Install VB-Cable from https://vb-audio.com/Cable
2. In `main.py`, set:

```python
AUDIO_OUTPUT_DEVICE = "CABLE Input (VB-Audio Virtual Cable)"
```

3. In Discord or your game, set the microphone input to "CABLE Output".

To list all available device names on your system, run this in a Python shell:

```python
import sounddevice as sd
print(sd.query_devices())
```

Copy the exact name from the output.

### Linux (PipeWire)

Create a null sink:

```
pactl load-module module-null-sink media.class=Audio/Sink sink_name=teto_out channel_map=stereo
```

Set `AUDIO_OUTPUT_DEVICE` to `"teto_out"` and point Discord or your game at that sink as its microphone source.

---

## Troubleshooting

**OpenUTAU not found**
Check that `OPENUTAU_PATH` in `main.py` points to the correct executable.

**No audio output**
Run `python -c "import sounddevice as sd; print(sd.query_devices())"` to list devices and verify your device name is correct.

**Render times out**
Increase `RENDER_TIMEOUT` in `main.py`. Long sentences may take more than 30 seconds depending on your hardware.

**RealtimeSTT not detecting voice**
Make sure your microphone is set as the default input device in your OS settings.

**OpenUTAU --render flag not working**
The CLI render flag may not be available in all versions of OpenUTAU. Run `OpenUtau.exe --help` to check supported flags. If it is not available, check the OpenUTAU GitHub issues for the current recommended CLI workflow.
