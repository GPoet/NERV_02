# Upstream: aaronjmars/aeon

*Updated: 2026-03-21*

## What It Is
The Aeon framework -- autonomous agent platform on GitHub Actions with Claude Code.

## Recent Changes (week of 2026-03-19)
- Local dashboard (Next.js) for managing skills, secrets, runs
- Auth flow: `claude setup-token` integration, OAuth token as GitHub secret
- `add-skill` command for importing skills from other repos
- Inline run log viewer in dashboard
- GH_GLOBAL secret for cross-repo access
- All 32 skills standardized to single `var` variable + model selector
- `.skill` file format support
- Multiple UI/UX fixes: timezone, toast notifications, button states

## Key Decisions
- Skills use a single `var` string variable (not multiple params)
- Dashboard runs locally via `./aeon` launcher script
- Prompts piped via stdin to avoid ByteString Unicode errors

## Monitoring
- GitHub monitor checks: 0 open PRs, 0 new issues, 0 releases (as of 2026-03-21)
