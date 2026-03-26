---
name: Autoevolve
description: Multi-iteration autonomous skill evolution loop — runs N keep/discard experiments overnight using the autoresearch pattern. For each iteration: picks a target skill, forms a hypothesis, edits SKILL.md on a branch, re-evaluates via skill-eval rubric, keeps or reverts based on score delta, logs to results.tsv. Repeats until N iterations complete. Modelled on karpathy/autoresearch.
var: ""
---
> **${var}** — Optional. Format: `<skill-name>` or `<skill-name> --iterations <N>`. Defaults: auto-pick lowest scored skill, 10 iterations.

Run N iterations of the skill evolution loop autonomously. Wake up to a results table and a better skill.

---

## Pre-flight

1. Parse `${var}`:
   - Extract skill name if provided (else auto-pick below)
   - Extract `--iterations N` if present (default: 10)
2. Read `memory/topics/skill-scores.json` — needed to pick target and establish baseline.
   - If missing or < 3 entries, run `skill-eval` on `morning-brief`, `self-review`, `skill-health` first.
3. Read `memory/topics/skill-evolution.md` if it exists (evolution history).
4. Resolve target skill:
   - If provided via var: use it
   - Otherwise: pick skill with lowest composite score not evolved in last 7 days
5. Read `skills/${target}/SKILL.md` in full — this is your `train.py`.
6. Record `baseline_score` from skill-scores.json.
7. Initialize `results.tsv` for this run (in-memory, append to file at end):
   ```
   iteration  hypothesis_type  change_summary  score_before  score_after  delta  status
   ```

---

## The Loop (repeat N times)

### 1. Form hypothesis

Pick the next hypothesis type from this rotation (cycle through, do not repeat consecutively):
- **trim** — remove verbose explanation, cut words without losing meaning
- **example** — add one concrete dispatch/output example block
- **scope** — tighten description trigger conditions to reduce false positives
- **structure** — move a detail section to `references/`, keep SKILL.md lean
- **metric** — clarify what "done" looks like (output format, success condition)
- **error-handling** — add a missing failure branch or exit condition
- **simplify** — reduce steps without losing coverage

Skip a type if it doesn't apply to this skill's current state. Move to next.

Write a one-sentence hypothesis:
> "Hypothesis: [specific change] to [section] will improve [dimension] because [reason]."

**Constraint: one change per iteration. Surgical edits only.**

### 2. Create branch and apply

```bash
git checkout main
git checkout -b evolve/${target}-$(date +%Y%m%d-%H%M%S)
```

Edit `skills/${target}/SKILL.md` — one change only.

```bash
git add skills/${target}/SKILL.md
git commit -m "autoevolve(${target}): ${one_line_description}"
```

### 3. Score the modified skill

Mentally apply the skill-eval rubric to the modified SKILL.md:
- **Completeness** (0–10): every step covered?
- **Efficiency** (0–10): lean, no redundancy?
- **Specificity** (0–10): concrete output format, examples?
- `new_composite = (C + E + S) / 3`

### 4. Decision

**Simplicity criterion (from autoresearch):**
- Tiny gain + added complexity → DISCARD
- Same score + simpler SKILL.md → KEEP
- Genuine improvement → KEEP

#### KEEP (new_composite > baseline OR equal + clearly simpler):
```bash
git checkout main
git merge evolve/${target}-... --no-ff -m "autoevolve(${target}): ${baseline} → ${new_composite}"
git branch -d evolve/${target}-...
```

Update `baseline_score = new_composite` for next iteration.

#### DISCARD:
```bash
git checkout main
git branch -D evolve/${target}-...
```

Baseline unchanged for next iteration.

### 5. Log iteration

Append row to in-memory results.tsv:
```
${i}  ${hypothesis_type}  ${change_summary}  ${score_before}  ${score_after}  ${delta:+.2f}  KEEP/DISCARD
```

---

## After all N iterations

### Write results.tsv

Write final `memory/topics/autoevolve-results-${target}-${today}.tsv` (tab-separated):
```
iteration	hypothesis_type	change_summary	score_before	score_after	delta	status
1	trim	removed setup preamble	6.33	6.67	+0.34	KEEP
2	example	added dispatch example	6.67	6.33	-0.34	DISCARD
...
```

### Update evolution log

Append summary block to `memory/topics/skill-evolution.md`:
```markdown
## ${today} — ${target} (autoevolve × ${N})

- **Iterations:** ${N} total, ${kept} kept, ${discarded} discarded
- **Baseline:** ${original_baseline}
- **Final score:** ${final_score} (Δ${total_delta:+.2f})
- **Top win:** ${best_hypothesis_type} — "${best_change_summary}" (+${best_delta:.2f})
```

### Append to skill-scores.json

Add final post-run score entry for `${target}`.

### Notify

Send via `./notify`:
```
🔬 Autoevolve complete: ${target}
${N} experiments — ${kept} kept, ${discarded} discarded
Score: ${original_baseline} → ${final_score} (${total_delta:+.2f})
Top win: ${best_change_summary}
```

### Log

Append to `memory/logs/${today}.md`:
```
AUTOEVOLVE: ${target} × ${N} | score ${original_baseline} → ${final_score} (Δ${total_delta}) | ${kept}K/${discarded}D
```

---

## Guardrails

- Never modify `aeon.yml`, `skill-eval/SKILL.md`, or `skill-evolve/SKILL.md` — locked harness
- Never modify `autoevolve/SKILL.md` itself during a run
- One change per iteration — resist fixing everything at once
- If git operations fail: log error, skip iteration, continue loop
- If score cannot be computed: log "UNEVALUABLE", treat as DISCARD, continue
- Max 20 iterations regardless of `--iterations` value (cost guardrail)
- `results.tsv` files are untracked by git — truth log, not noise
