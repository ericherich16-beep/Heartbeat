# Live CEO agent

A steering-committee CEO who listens to your presentation through the microphone and cuts in out loud, the way a direct, demanding executive at a billion-dollar company would.

The persona is in [`persona.md`](persona.md). Edit it to change who she is. The server reloads it on restart.

## Run it

```bash
cd ceo-agent
npm install
export ANTHROPIC_API_KEY=sk-ant-...
npm start
```

Open http://localhost:8787 in **Chrome or Edge**, fill in the meeting details, put on headphones, click **Start listening**, and present.

You can also type into the box under the transcript to rehearse without a microphone.

## How it works

```
mic ──► browser speech-to-text ──► transcript ──► /api/decide ──► Claude (persona + transcript)
                                                                     │
speakers ◄── browser text-to-speech ◄── "interrupt" + line ◄─────────┘
```

1. The browser's built-in speech recognition turns your speech into text as you talk.
2. Each time you pause briefly (a finished phrase), the page sends the recent transcript to the server.
3. The server asks Claude, in character as the CEO, to choose `interrupt` or `hold`, and to give the exact line she'd say.
4. If she interrupts, the browser speaks the line aloud and adds it to the transcript, so she follows up on your answer.

Controls:
- **Intensity** (patient to relentless) changes both how readily she interrupts and the minimum gap between interruptions (45s down to 6s).
- **Quiet, Maggie** or the **Esc** key stops her mid-sentence.
- While she's speaking, the mic input is ignored so she doesn't react to her own voice.

## Settings

| Env var | Default | What it does |
|---|---|---|
| `ANTHROPIC_API_KEY` | (required) | Your Claude API key |
| `CEO_MODEL` | `claude-opus-5-5` | The model that makes decisions |
| `CEO_EFFORT` | `low` | `low` keeps reactions fast; `medium` gives sharper lines but more delay |
| `PORT` | `8787` | Server port |

Requests use server-side refusal fallbacks (`fallbacks: "default"`), so if a turn is declined, the API retries it on a fallback model instead of going silent.

## Limits

- **Latency.** She reacts about 1 to 3 seconds after you finish a phrase, like someone waiting for a breath to cut in. She doesn't talk over you mid-word.
- **Privacy.** Chrome and Edge send microphone audio to their own cloud speech services for transcription. Don't use this with confidential material unless that's acceptable.
- **One voice.** She can't tell speakers apart, so everything the mic hears is treated as the presenter.
- **Cost.** Each pause triggers one API call. The persona is cached, so you mostly pay for the transcript.
