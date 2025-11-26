# Script Ops console

A lightweight single-page prototype for managing scripted operations with explicit checkpoints, sidecar context, and live cost tracking.

## Features
- Phase-gated navigation that requires filter selection, toolkit choice, variant approval, and rollback confirmation before moving forward.
- Transcript workspace with split-screen or PiP clips plus tags, summary, and sentiment presented in a sidebar.
- Token usage tracking per API call with real cost estimates surfaced in the footer.
- Simulated queue for long-running tasks with loading indicators that keep the UI responsive.

## Running locally
Open `index.html` in a modern browser. Network access is used only to load the sample clip.
