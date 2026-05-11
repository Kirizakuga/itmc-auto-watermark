# Architecture Decisions

## Core Framework
- **FFmpeg**: The primary engine for all media processing (Images & Videos). 
- **Streamlit**: Used for the interactive web interface.

## Application Structure
- **Unified Logic**: Both images and videos are treated as visual streams. 
- **RAM-Pipe Processing (Images)**: For images, processing occurs entirely in RAM via FFmpeg pipes (`stdin/stdout`). This avoids disk I/O latency and enables near-instant UI updates.
- **Atomic File Processing (Videos)**: Videos are processed via temporary directories (`tempfile.TemporaryDirectory`) to ensure reliable cleanup and handle large files safely.

## Deployment
- **Docker**: Containerized using `python:3.11-slim` (Debian-based) for stable FFmpeg binary support and easier dependency management.

## Performance & Scaling
- **Fast Seeking**: Video previews use Input Seeking (`-ss` before `-i`) to jump directly to keyframes, ensuring sub-second response times for the timestamp slider.
- **Concurrency**: Batch processing is handled via `ThreadPoolExecutor` with worker limits tied to CPU cores to prevent resource exhaustion.
