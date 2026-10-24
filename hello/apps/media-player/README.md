# Media Player Suite for HBLauncher

A full-featured media playback suite supporting **MP3, FLAC, WAV, OPUS, MP4, and WEBM** files hosted on your PC host and transferred/streamed via the built-in FTP service (`ftpd` background service).

Maintained for Nintendo Switch 2 Homebrew Launcher (SmileBASIC environment).

## Features

- **Multi-Format Support:** MP3, FLAC, WAV, OPUS, MP4, and WEBM media streams.
- **PC Hosting & FTP Management:** Host media files in the PC app folder and manage/transfer files via FTP (`ftp://<console-ip>:5000` via FileZilla).
- **GPU-Accelerated UI:** Rendered at 1920x1080 via Vulkan compute and fragment shaders with real-time controls.
- **Controls:**
  - D-Pad Up/Down: Navigate playlist / format selection.
  - A: Toggle Play / Pause.
  - X: Stop playback.
  - B or Minus: Return to HBLauncher.

## Installation

1. Copy the `media-player` folder to `HBLauncher/apps/media-player/`.
2. Place your media files (`.mp3`, `.flac`, `.wav`, `.opus`, `.mp4`, `.webm`) into the app folder or transfer them via FTP (`/save` or `/tmp`).
3. Refresh HBLauncher and launch **Media Player Suite**.
