# Background Sound Assets

Place your background sound WAV file here.

## Required Format

The WAV file **must** be: **8kHz, 16-bit, mono** (matching Exotel's audio format).

## Converting Audio Files

Use ffmpeg to convert any audio file to the required format:

```bash
ffmpeg -i input.mp3 -ar 8000 -ac 1 -sample_fmt s16 bg-sound.wav
```

## Usage

Set the file path via environment variable or CLI argument:

```bash
# Environment variable
export BG_SOUND_FILE=exotel/assets/bg-sound.wav
export BG_SOUND_VOLUME=0.3  # 0.0 to 1.0

# Or CLI argument
python -m exotel.bridge --bg-sound-file exotel/assets/bg-sound.wav --bg-sound-volume 0.3
```
