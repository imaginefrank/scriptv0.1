# scriptv0.1

A lightweight console tool for assembling scripted segments with archetypes, beats, and runtime checks.

## Features
- Predefined archetypes with beat slots, durations, and guidance.
- State tracking for selected archetype, beat text, clip selections, and operator approvals.
- Preview of beats with split-screen or PiP style context to pair narration and clips.
- Runtime estimation using spoken word-count/2.5 plus clip durations, flagging segments over a 15-minute cap.
- Continuity checks to ensure Setup leads logically into Clip, with an operator gate to approve transitions.

## Getting started
Run the console UI and follow the prompts to choose an archetype, add beat text, set clip in/out points, and review pacing:

```bash
python -m app.main
```

Use the numbered actions to edit beats, preview layouts, check runtime against the budget, and approve transitions once continuity looks correct.
