// ─── Centralized Design Tokens — Apple Mono Theme ────────────────────────────

export const C = {
  bg:           '#1C1C1E',   // Apple systemBackground dark
  bgPanel:      '#2C2C2E',   // Apple secondarySystemBackground dark
  bgDeep:       '#141416',   // deeper layer
  border:       '#38383A',   // Apple separator dark
  borderHi:     '#48484A',   // Apple opaqueSeparator dark
  orange:       '#C8A97E',   // warm sand accent (replaces neon orange)
  orangeDim:    '#5C4020',   // dimmed sand
  red:          '#FF453A',   // Apple red dark
  redBright:    '#FF6961',
  green:        '#32D74B',   // Apple green dark
  blue:         '#0A84FF',   // Apple blue dark
  amber:        '#FFD60A',   // Apple yellow dark
  yellow:       '#FFD60A',
  cyan:         '#5AC8FA',   // Apple cyan
  cyanDim:      '#1A4455',
  purple:       '#BF5AF2',   // Apple purple dark
  text:         '#8E8E93',   // Apple secondaryLabel dark
  textDim:      '#636366',   // Apple tertiaryLabel dark
  textBright:   '#F5F5F7',   // Apple label dark
  textMuted:    '#1C1C1E',
  surfaceTwo:   '#3A3A3C',   // Apple tertiarySystemBackground dark
  surfaceThree: '#444446',
  slateIndigo:  '#2C2C2E',
  cautionYellow:'#FFD60A',
} as const

export const MODELS = [
  { id: 'claude-sonnet-4-6', label: 'Sonnet 4.6' },
  { id: 'claude-opus-4-6', label: 'Opus 4.6' },
  { id: 'claude-haiku-4-5-20251001', label: 'Haiku 4.5' },
] as const

export const SKILL_GROUPS: Record<string, string[]> = {
  HYPERLIQUID: ['hl-intel', 'hl-scan', 'hl-monitor', 'hl-alpha', 'hl-report', 'hl-trade'],
  INTEL:       ['morning-brief', 'rss-digest', 'hacker-news-digest', 'paper-digest', 'tweet-digest'],
  OPERATIONS:  ['issue-triage', 'pr-review', 'github-monitor'],
  FINANCIAL:   ['token-alert', 'wallet-digest', 'on-chain-monitor', 'defi-monitor'],
  CREATIVE:    ['article', 'digest', 'feature'],
  MAINTENANCE: ['code-health', 'changelog', 'build-skill'],
  META:        ['goal-tracker', 'skill-health', 'self-review', 'reflect', 'memory-flush', 'weekly-review', 'heartbeat'],
}

export const GROUP_COLORS: Record<string, string> = {
  HYPERLIQUID: '#FF453A',   // Apple red
  INTEL:       '#0A84FF',   // Apple blue
  OPERATIONS:  '#C8A97E',   // warm sand
  FINANCIAL:   '#FFD60A',   // Apple yellow
  CREATIVE:    '#BF5AF2',   // Apple purple
  MAINTENANCE: '#32D74B',   // Apple green
  META:        '#FF6961',   // Apple pink
}
