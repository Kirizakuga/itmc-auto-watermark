# Technical Specifications

## Environment
- **Runtime**: Python 3.11+
- **Base Image**: `python:3.11-slim`
- **System Binary**: `ffmpeg` (installed via apt-get)

## Dependencies
- `streamlit`: Web framework.
- `concurrent.futures`: Standard library for parallel processing.
- `tempfile`: Standard library for media artifact management.

## Processing Logic
- **Filter Graph**: `[1:v]scale=iw*{scale_ratio}:-1[logo];[0:v][logo]overlay=(W-w)/2:H*{margin_ratio}+{y_offset}`
- **Image Pipeline**: `image2pipe` format used for RAM-to-RAM processing.
- **Video Pipeline**: `libx264` codec with `crf=23` and `preset=medium`.
- **Fast Seek**: `-ss` parameter used before `-i` for instantaneous frame extraction.

## Supported Formats
- **Images**: `png`, `jpg`, `jpeg`, `webp`, `heic` (via FFmpeg).
- **Videos**: `mp4`, `mov`, `avi`.
