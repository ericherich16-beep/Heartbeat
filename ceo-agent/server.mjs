// Live CEO agent: serves the browser app and decides, from the running
// transcript, whether the CEO persona should interrupt and what to say.
import http from "node:http";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import Anthropic from "@anthropic-ai/sdk";

const here = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 8787);
const MODEL = process.env.CEO_MODEL || "claude-opus-5-5";
// Low effort keeps each decision fast enough to land while the speaker is
// still on the point. Raise to "medium" for sharper but slower interjections.
const EFFORT = process.env.CEO_EFFORT || "low";

const client = new Anthropic();
const persona = await fs.readFile(path.join(here, "persona.md"), "utf8");

const SYSTEM = `${persona}

## Your job right now

You are Maggie Kessler, live, in a steering committee meeting. You hear a running speech-to-text transcript of the presenter. Lines you already said are marked CEO. After each new chunk, decide whether to cut in right now.

Rules:
- Interrupt only when Maggie genuinely would: a specific trigger from her persona just happened in the most recent speech, or the presenter just answered (or dodged) her last question.
- Respond to what was said most recently. Don't revisit points you already raised unless the answer dodged them.
- Your line is spoken aloud, so write it the way she talks: 1 to 3 short sentences, usually under 30 words, no lists, no stage directions, no markdown.
- Use the presenter's name if you know it.
- Speech-to-text makes mistakes. If a word looks garbled, read it charitably and don't interrupt over a transcription error.
- If you choose to hold, leave "line" empty.`;

const DECISION_SCHEMA = {
  type: "object",
  properties: {
    action: { type: "string", enum: ["interrupt", "hold"] },
    line: { type: "string", description: "Exactly what the CEO says aloud. Empty when holding." },
    reason: { type: "string", description: "One short phrase naming the trigger, for the on-screen log." },
  },
  required: ["action", "line", "reason"],
  additionalProperties: false,
};

const INTENSITY = {
  1: "Patient. Interrupt only for a missing ask, a major contradiction, or a serious risk being glossed over.",
  2: "Measured. Interrupt for clear triggers; let minor vagueness slide.",
  3: "Direct. Interrupt whenever a persona trigger clearly fires.",
  4: "Demanding. Interrupt on most triggers, including vague language and numbers without context.",
  5: "Relentless. Hold the presenter to account on every soft claim. Still respectful.",
};

function buildPrompt({ context = {}, transcript = [], intensity = 3, secondsSinceLastInterruption }) {
  const ctx = [
    context.company && `Company: ${context.company}`,
    context.presenter && `Presenter: ${context.presenter}`,
    context.topic && `Agenda item: ${context.topic}`,
    context.notes && `What you already know (pre-read): ${context.notes}`,
  ].filter(Boolean).join("\n") || "No extra context given.";

  // Keep the most recent ~8k characters; older speech matters less to a live decision.
  let lines = transcript.map(t => `${t.speaker === "ceo" ? "CEO" : "PRESENTER"}: ${t.text}`);
  let total = 0, start = lines.length;
  while (start > 0 && total + lines[start - 1].length < 8000) total += lines[--start].length;
  const tail = lines.slice(start).join("\n");

  const since = Number.isFinite(secondsSinceLastInterruption)
    ? `You last spoke ${Math.round(secondsSinceLastInterruption)} seconds ago.`
    : "You haven't spoken yet.";

  return `<meeting>\n${ctx}\n</meeting>

<intensity>${INTENSITY[intensity] || INTENSITY[3]}</intensity>

<transcript>
${tail || "(nothing yet)"}
</transcript>

${since} The last PRESENTER line is what was just said. Decide now: interrupt or hold.`;
}

async function decide(body) {
  const response = await client.beta.messages.create({
    model: MODEL,
    max_tokens: 4000,
    betas: ["server-side-fallback-2026-07-01"],
    fallbacks: "default",
    system: [{ type: "text", text: SYSTEM, cache_control: { type: "ephemeral" } }],
    messages: [{ role: "user", content: buildPrompt(body) }],
    output_config: {
      effort: EFFORT,
      format: { type: "json_schema", schema: DECISION_SCHEMA },
    },
  });

  if (response.stop_reason === "refusal") {
    return { action: "hold", line: "", reason: "model declined this turn" };
  }
  const text = response.content.filter(b => b.type === "text").map(b => b.text).join("");
  try {
    const parsed = JSON.parse(text);
    if (parsed.action !== "interrupt") parsed.line = "";
    return parsed;
  } catch {
    return { action: "hold", line: "", reason: `unparseable reply (stop: ${response.stop_reason})` };
  }
}

const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css" };

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === "POST" && req.url === "/api/decide") {
      let raw = "";
      for await (const chunk of req) {
        raw += chunk;
        if (raw.length > 1_000_000) throw Object.assign(new Error("body too large"), { status: 413 });
      }
      const started = Date.now();
      const decision = await decide(JSON.parse(raw || "{}"));
      decision.ms = Date.now() - started;
      res.writeHead(200, { "content-type": "application/json" });
      return res.end(JSON.stringify(decision));
    }
    if (req.method === "GET") {
      const rel = req.url === "/" ? "index.html" : decodeURIComponent(req.url.split("?")[0]).replace(/^\/+/, "");
      const file = path.join(here, "public", rel);
      if (!file.startsWith(path.join(here, "public"))) { res.writeHead(403); return res.end(); }
      const data = await fs.readFile(file);
      res.writeHead(200, { "content-type": TYPES[path.extname(file)] || "application/octet-stream" });
      return res.end(data);
    }
    res.writeHead(404); res.end();
  } catch (err) {
    const status = err.status && err.status < 600 ? err.status : err.code === "ENOENT" ? 404 : 500;
    if (status >= 500) console.error(err);
    res.writeHead(status, { "content-type": "application/json" });
    res.end(JSON.stringify({ error: err.message }));
  }
});

server.listen(PORT, () => {
  console.log(`CEO agent on http://localhost:${PORT}  (model ${MODEL}, effort ${EFFORT})`);
});
