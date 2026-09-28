# Pending Changes

[2026-05-11 20:45] - Entire Project - Complete migration from Pillow to FFmpeg.
- Added support for video watermarking (MP4, MOV, AVI).
- Implemented RAM-pipe processing for images to maintain zero-latency previews.
- Implemented Fast-Seek frame extraction for video previews.
- Switched base image to `python:3.11-slim` for stable FFmpeg support.
- Added `ThreadPoolExecutor` for parallel batch processing.

[17:15] - packages.txt - Create file - Added FFmpeg to fix FileNotFoundError in Streamlit Community Cloud.
[17:15] - test.py - Update UI - Injected Taste Skill CSS (Inter font, minimal UI, brutalist buttons) based on taste-skill conventions.
[2026-09-28] - test.py, docs - Feature: Free Logo Placement - Added 2D positioning presets and free X/Y movement sliders with top-center default.
[2026-09-28] - Deployment & Runtime Fixes:
- Added `.python-version` pinned to `3.11` to prevent Streamlit Cloud from defaulting to Python 3.14 (causing pyarrow segfault and ASGI issues).
- Kept `streamlit` aligned with Streamlit Cloud native environment to avoid 404 upload route mismatches.
- Added `.streamlit/config.toml` (maxUploadSize=1000MB, CORS/XSRF disabled) for reliable file uploads through Cloudflare proxy.
- Hardened `test.py` logo path resolution, safe video MIME detection, and even-dimension logo scaling.

