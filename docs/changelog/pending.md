# Pending Changes

[2026-05-11 20:45] - Entire Project - Complete migration from Pillow to FFmpeg.
- Added support for video watermarking (MP4, MOV, AVI).
- Implemented RAM-pipe processing for images to maintain zero-latency previews.
- Implemented Fast-Seek frame extraction for video previews.
- Switched base image to `python:3.11-slim` for stable FFmpeg support.
- Added `ThreadPoolExecutor` for parallel batch processing.

[17:15] - packages.txt - Create file - Added FFmpeg to fix FileNotFoundError in Streamlit Community Cloud.
[17:15] - test.py - Update UI - Injected Taste Skill CSS (Inter font, minimal UI, brutalist buttons) based on taste-skill conventions.
