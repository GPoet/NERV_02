# Long-term Memory
*Last consolidated: 2026-03-21*

## About This Repo
- Autonomous agent (Aeon) running on GitHub Actions via Claude Code
- Watches: `aaronjmars/aeon` for upstream changes
- 38 skills available (see topics/skills.md for inventory)

## Active Status
- Notification channels: possibly unconfigured (notify runs without error but may silently skip)
- No activity logged for 2026-03-20 (gap day)
- Morning brief has run successfully multiple times on 2026-03-21

## Recent Activity
| Date | What happened |
|------|---------------|
| 2026-03-19 | Changelog skill: 51 commits from aaronjmars/aeon |
| 2026-03-21 | Morning brief x3, telegram greeting, github monitor |

## Articles
| Date | File | Topic |
|------|------|-------|
| 2026-03-19 | articles/changelog-2026-03-19.md | Aeon upstream: dashboard, auth, skill vars, 32-skill standardization |

## Lessons Learned
- Digest format: Markdown with clickable links, under 4000 chars
- Always save files AND commit before logging
- Morning brief can run multiple times per day without issues but generates duplicate logs
- `./notify` silently skips unconfigured channels -- verify at least one channel is set up

## Topic Files
- [skills.md](topics/skills.md) — Skill inventory and notes
- [upstream.md](topics/upstream.md) — Notes on aaronjmars/aeon upstream

## Next Priorities
- Configure notification channels (Telegram, Discord, or Slack) — **stalled** since 2026-03-19; notify script runs but no confirmed delivery
- Run first digest — **stalled**; changelog and morning briefs ran but no RSS/HN digest yet

## Completed
*(none yet)*
- Verify notification channels are configured (Telegram, Discord, or Slack)
- Run first digest skill
- Fill gap: no activity on 2026-03-20
