# HackerSquad submission copy

## Project name
ScoopScout

## Tagline
Your daily ice cream scoop, planned around your city and calendar.

## Description
ScoopScout turns a free calendar window into a feasible ice cream outing in San Francisco. Choose your current location and onward destination; the agent finds gaps, filters nine sourced shops by published hours and an estimated travel budget, and uses an Akamai-hosted Qwen model to rank eligible options for your preferences. Each plan includes departure and arrival times, a ten-minute scoop allowance, a five-minute buffer, source links, walking directions, and a visible decision summary.

Private calendar busy intervals and coordinates stay in the local app. The model receives only preferences and eligible shop facts. A Google Calendar FreeBusy OAuth integration is implemented, but live authorization still requires local OAuth credentials and sign-in. The recorded demo uses manually entered sample busy intervals and live workshop-model results. The app can recheck every five minutes while open and track daily completion in the browser. It falls back transparently to shortest estimated outings if inference is unavailable.

The prototype runs on a laptop and uses Qwen/Qwen3-4B served by the workshop’s Akamai-hosted vLLM endpoint through kubectl port-forward. It does not provision or scale inference infrastructure. Walking times are approximate geographic estimates; shop hours are sourced snapshots, not live availability.

## Technologies
Python; HTML/CSS/JavaScript; Akamai Cloud workshop inference; Qwen/Qwen3-4B; vLLM; OpenAI-compatible chat completions; Kubernetes/kubectl; Google Calendar FreeBusy API; Google OAuth 2.0.

## Demo
74-second narrated MP4: demo/ScoopScout-demo.mp4
Subtitles: demo/ScoopScout-demo.srt

## Validation
15 automated tests pass. Live UI checks in the Mission and Inner Sunset produce different nearby recommendations within the same sample calendar gap.

## Submission checklist
- [x] Public repository: https://github.com/michaelrooney-star/scoopscout
- [x] Project name and description saved in HackerSquad.
- [x] Akamai and additional stack saved; ScoopScout solo team linked.
- [x] Existing demo URL included in the saved project description.
- [x] HackerSquad marks the in-browser recording step complete. The latest recording was processing when the final submission succeeded.
- [x] Problem, stack, product video, and code presentation available locally at http://127.0.0.1:8080/demo.
- [x] Submitted for judging October 12, 2026, at 4:58:08 PM America/Los_Angeles. HackerSquad confirms “Project submitted” and all three steps are complete.
- Event-specific deadline, rules, and demo requirements: verify the current builder guide/form; do not infer unpublished rules.
