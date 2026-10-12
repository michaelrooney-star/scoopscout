# ScoopScout video demo

`ScoopScout-demo.mp4` is a 74-second, 1280×720 narrated walkthrough using real app screenshots. Burned-in summary captions are included; `ScoopScout-demo.srt` contains the full narration.

The schedule is manually entered sample data for October 13, 2026. Qwen results were captured live. Google Calendar is explicitly shown as not connected. Travel estimates and sourced hours are identified as approximate.

To reproduce on macOS, install `demo/requirements.txt` into the project virtual environment and run `.venv/bin/python demo/render_demo.py`. macOS speech-service access is required for the Samantha narration. The script uses the saved app screenshots and creates its audio and MP4 locally.
