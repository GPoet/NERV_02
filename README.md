# Aeon

Autonomous agent running on GitHub Actions, powered by Claude Code. Writes daily articles, builds features from GitHub issues, generates digests, and notifies you on Telegram.

## Quick start

1. **Fork this repo** (or click "Use this template" if available)
2. **Enable GitHub Actions** — go to the **Actions** tab in your fork and click "I understand my workflows, go ahead and enable them"
3. **Add secrets** — go to **Settings > Secrets and variables > Actions** and add:

| Secret | Required | Description |
|--------|----------|-------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Yes | OAuth token for Claude (see below) |
| `TELEGRAM_BOT_TOKEN` | Optional | From @BotFather on Telegram |
| `TELEGRAM_CHAT_ID` | Optional | Your Telegram chat ID from @userinfobot |
| `XAI_API_KEY` | Optional | X.AI API key for searching X/Twitter |

4. **Edit `aeon.yml`** — configure which skills run and when
5. **Test** — go to **Actions > Run Skill > Run workflow** and enter a skill name (e.g. `article`)

### Getting your auth token

**Option A: Claude Code OAuth token (recommended)** — uses your existing Claude Pro/Max subscription, no separate API billing.

1. Install [Claude Code](https://docs.anthropic.com/en/docs/claude-code) and run:
   ```bash
   claude setup-token
   ```
2. It opens a browser for OAuth login, then prints a long-lived token (`sk-ant-oat01-...`, valid for 1 year).
3. Add it as the `CLAUDE_CODE_OAUTH_TOKEN` secret in your repo.

**Option B: Standard API key** — usage-based billing through console.anthropic.com.

1. Go to [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) and create a key.
2. Add it as `CLAUDE_CODE_OAUTH_TOKEN` in your repo secrets (it works in the same field).

## How it works

A GitHub Actions workflow runs every hour, checks `aeon.yml` to see if any skill is due, and if so, tells Claude Code to read and execute that skill's markdown file. After Claude finishes, the workflow commits all changes back to your repo.

```
Hourly cron fires
  → Checks aeon.yml — is any skill scheduled for this hour?
    → No  → exits immediately (costs ~10 seconds)
    → Yes → installs Claude Code
      → claude -p "Read and execute skills/article.md"
        → Claude reads the skill, searches the web, writes output
          → Workflow commits all changes back to main
```

## Configuration

All scheduling is done in `aeon.yml`:

```yaml
skills:
  article:
    schedule: "0 8 * * *"     # Daily at 8am UTC
  digest:
    schedule: "0 14 * * *"    # Daily at 2pm UTC
  feature:
    schedule: "0 2 * * 1"     # Monday at 2am UTC
```

The schedule format is standard cron (`minute hour day-of-month month day-of-week`). All times are UTC.

To disable a skill, remove it from `aeon.yml` or delete its schedule line.

## Adding a new skill

1. Create `skills/your-skill.md` with instructions for Claude:

```markdown
---
name: My Skill
description: What this skill does
---

Your task is to...
```

2. Add it to `aeon.yml` with a schedule:

```yaml
skills:
  your-skill:
    schedule: "0 12 * * *"   # Daily at noon UTC
```

That's it — no workflow changes needed.

## Telegram integration

Send messages to your Telegram bot and Aeon will interpret them — run skills, answer questions, or update memory. Polls every 5 minutes.

**Setup:**
1. Create a bot with [@BotFather](https://t.me/BotFather) on Telegram
2. Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` to your repo secrets
3. Send your bot a message like "write an article about quantum computing"

Only messages from your `TELEGRAM_CHAT_ID` are accepted — anyone else is ignored.

By default, Aeon polls Telegram every 5 minutes. This means up to a 5-minute delay before your message is picked up. If that's fine, you're done — no extra setup needed.

### Instant mode (optional)

To get near-instant responses, you can deploy a tiny webhook that triggers Aeon immediately when you send a message. This replaces the 5-minute polling delay with a ~1 second trigger. You still need the polling workflow as a fallback.

The webhook receives messages from Telegram and calls GitHub's `repository_dispatch` API to trigger the workflow instantly. It's ~20 lines of code.

**Option A: Cloudflare Worker (free tier: 100k requests/day)**

1. Create a worker at [workers.cloudflare.com](https://workers.cloudflare.com) with this code:

```js
export default {
  async fetch(request, env) {
    const { message } = await request.json();
    if (!message?.text || String(message.chat.id) !== env.TELEGRAM_CHAT_ID) {
      return new Response("ignored");
    }

    // Confirm receipt so polling doesn't reprocess
    await fetch(
      `https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/getUpdates?offset=${message.update_id + 1}`
    );

    // Trigger GitHub Actions
    await fetch(
      `https://api.github.com/repos/${env.GITHUB_REPO}/dispatches`,
      {
        method: "POST",
        headers: {
          Authorization: `token ${env.GITHUB_TOKEN}`,
          Accept: "application/vnd.github.v3+json",
        },
        body: JSON.stringify({
          event_type: "telegram-message",
          client_payload: { message: message.text },
        }),
      }
    );

    return new Response("ok");
  },
};
```

2. Add these environment variables in the Cloudflare dashboard:

| Variable | Value |
|----------|-------|
| `TELEGRAM_BOT_TOKEN` | Your bot token |
| `TELEGRAM_CHAT_ID` | Your chat ID |
| `GITHUB_REPO` | `your-name/aeon` |
| `GITHUB_TOKEN` | A [personal access token](https://github.com/settings/tokens) with `repo` scope |

3. Set your Telegram bot webhook to point to the worker:

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=https://your-worker.workers.dev"
```

**Option B: Railway / Vercel / any serverless platform**

Same code, different host. Deploy the webhook handler above as a serverless function on whichever platform you prefer. The logic is identical — receive Telegram webhook, call GitHub `repository_dispatch`.

## Trigger feature builds from issues

Add the label `ai-build` to any GitHub issue. The workflow fires automatically and Claude will read the issue, implement it, and open a PR.

## Running locally

```bash
# Run any skill locally (requires Claude Code CLI)
claude -p "Today is $(date +%Y-%m-%d). Read and execute the skill defined in skills/article.md" --dangerously-skip-permissions
```

## Two-repo strategy

This repo is a **public template**. For your own instance, we recommend keeping a separate private repo so your memory, articles, and API keys stay private.

### Setup

1. **Fork this repo** to your own account (e.g. `your-name/aeon-private`). Make it **private**.
2. Add your secrets to the **private** fork (not the public template).
3. Customize `CLAUDE.md`, `aeon.yml`, `memory/MEMORY.md`, and skill prompts in your private fork.
4. All generated content (articles, digests, memory) stays in your private fork.

### Pulling updates from the template

When the public template gets new skills or workflow improvements:

```bash
# In your private fork
git remote add upstream https://github.com/aaronjmars/aeon.git
git fetch upstream
git merge upstream/main --no-edit
```

This merges template changes without overwriting your personal content, since your articles/memory are in files that don't exist in the template.

## Project structure

```
CLAUDE.md           ← agent identity (auto-loaded by Claude Code)
aeon.yml            ← skill schedules (edit this to configure)
skills/
  article.md        ← daily article skill
  digest.md         ← daily digest skill
  feature.md        ← feature builder skill
  reflect.md        ← weekly reflection skill
  build-tool.md     ← skill builder skill
  fetch-tweets.md   ← tweet fetcher skill
  search-papers.md  ← academic paper search tool
memory/
  MEMORY.md         ← long-term persistent memory
.github/
  workflows/
    run-skill.yml   ← scheduled skill runner
    telegram.yml    ← Telegram message polling
```
