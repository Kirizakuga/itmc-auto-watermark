# Product Requirements Document (PRD)

## Problem Statement
Users need a simple, fast way to apply a consistent watermark (logo) to batches of images without manual editing.

## Goals
- Provide a user-friendly web interface for non-technical users.
- Support batch processing.
- Allow real-time adjustments of logo placement.
- Ensure high-quality output.

## Functional Requirements
- **Logo Management**: Support both a default server-side logo and custom user-uploaded logos.
- **Batch Upload**: Allow multiple background images to be uploaded at once.
- **Live Preview**: Show a preview of the first processed image with current settings.
- **Adjustable Parameters**: Scale, Margin, and Offset.
- **Downloadable Output**: Provide all processed images in a single ZIP file.

## Non-Functional Requirements
- **Performance**: Processing should be fast and happen in-RAM.
- **Portability**: Easy to deploy via Docker.
