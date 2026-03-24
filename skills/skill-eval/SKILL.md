---
name: Skill Eval
description: Fixed evaluator — runs a skill with a standardized test prompt and scores it. The evaluation harness is immutable; only the skill under test changes.
var: ""
---
> **${var}** — Name of the skill to evaluate. Required.

Evaluate skill `${var}` using the fixed rubric below. This skill is the locked
evaluator in the autoresearch loop — it must never be modified to favour any
particular skill output. Its job is to produce an honest, reproducible score.

---

## Pre-flight

1. Check `${var}` is set. If empty, exit with error: "skill-eval requires a skill name via var".
2. Confirm `skills/${var}/SKILL.md` exists. If not, exit with error: "skill ${var} not found".
3. Read `memory/topics/skill-scores.json` if it exists (you will append to it later).
   If it does not exist, you will create it.

---

## Step 1 — Read the skill under test

Read `skills/${var}/SKILL.md` in full.

Extract:
- **Purpose**: what the skill is supposed to accomplish (from `description` frontmatter and first paragraph)
- **Expected outputs**: what a successful run produces (files, notifications, log entries, data)
- **Dependencies**: what env vars or external services it needs

---

## Step 2 — Construct a standardised test prompt

Using the skill's purpose, craft a realistic but minimal test invocation:
- Use a concrete, unambiguous `var` value if the skill accepts one (e.g. for `research-brief`, use "AI agents 2026")
- Aim for a prompt that exercises the skill's core path in ≤ 60 seconds
- Record the test prompt you chose in your evaluation log

Do NOT actually dispatch the skill to GitHub Actions — that would be slow and
consume quota. Instead, reason about the skill's output by:

1. Simulating a single execution mentally using the skill's step-by-step instructions
2. Identifying what a high-quality output would look like vs a low-quality output

This is a static analysis evaluation, not a live run.

---

## Step 3 — Score on three dimensions (0–10 each)

### A. Completeness (0–10)
Does the skill's instruction set cover every step needed to accomplish its stated goal?
- 10: every step is explicit, nothing left to chance
- 7: most steps covered, minor gaps
- 4: key steps missing or vague
- 1: barely describes what to do

### B. Efficiency (0–10)
How lean is the skill — does it avoid unnecessary steps, redundant fetches, or bloated prompts?
- 10: minimal steps, no redundancy, tight prompts
- 7: mostly efficient, one or two unnecessary steps
- 4: noticeable bloat or repeated work
- 1: very wasteful — many redundant steps

### C. Specificity (0–10)
Does the skill produce actionable, concrete output (not vague summaries)?
- 10: output format is well-defined, examples given, edge cases handled
- 7: mostly specific but some vague sections
- 4: output description is generic
- 1: no output format specified at all

### Composite score
`composite = (A + B + C) / 3`  (rounded to 2 decimal places)

---

## Step 4 — Write evaluation rationale

For each dimension, write 1–2 sentences explaining the score.
Be specific — quote the skill's text where relevant.

---

## Step 5 — Record results

Append to `memory/topics/skill-scores.json` (create if missing).

Schema:

```json
{
  "scores": [
    {
      "skill": "<name>",
      "date": "<YYYY-MM-DD>",
      "completeness": 8.0,
      "efficiency": 7.0,
      "specificity": 6.0,
      "composite": 7.0,
      "notes": "One-line summary of main finding",
      "evaluated_by": "skill-eval"
    }
  ]
}
```

If a score entry for this skill already exists, **append a new entry** — do not overwrite.
This preserves the history needed by skill-evolve to measure improvement.

---

## Step 6 — Log and notify

Append to `memory/logs/${today}.md`:
```
SKILL_EVAL: ${var} → composite ${score} (C:${completeness} E:${efficiency} S:${specificity})
```

If composite < 6.0, send via `./notify`:
```
⚠️ Skill Eval: ${var} scored ${composite}/10
Weakest dimension: <dimension> (${score})
Recommended for evolution.
```

Otherwise, log only — no notification needed.

---

## Rules (IMMUTABLE — do not change these in any evolution run)

- Never modify `prepare.py` equivalent files: `aeon.yml`, `prepare.py`, this skill itself
- Scores must be based on the skill text alone — not on live run results
- Do not adjust rubric thresholds to flatter any skill
- If a skill cannot be meaningfully evaluated (e.g. it requires live market data with no testable structure), score it 5/10 across all dimensions and note "not statically evaluable"
