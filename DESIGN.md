# TradeDash Design System

## Overview
TradeDash is a dark-theme trading dashboard for ES=F futures paper trading. Built with vanilla HTML/Tailwind CSS + Chart.js. Single-page application with sidebar navigation and section-based content.

## Color Palette

### Base (Dark Theme)
| Token | Hex | Usage |
|-------|-----|-------|
| bg | `#0a0a0f` | Page background |
| card | `#12121a` | Card backgrounds |
| hover | `#1a1a25` | Card hover state |
| border | `#1e1e2e` | Borders, dividers |
| text | `#e0e0e0` | Primary body text |
| muted | `#94a3b8` | Secondary text (labels, captions) |
| dim | `#666666` | Tertiary text (placeholders, helper text) |

### Accent Colors
| Token | Hex | Usage |
|-------|-----|-------|
| green | `#00ff88` | Positive P&L, wins, target status, long direction |
| red | `#ff4444` | Negative P&L, losses, stopped status, short direction |
| blue | `#4a9eff` | Primary actions, neutral/info, ORB strategy |
| yellow | `#ffd700` | Warnings, IB Breakout strategy, win rate badges |
| purple | `#a855f7` | VWAP strategy, pending status |

### Strategy Colors
| Strategy | Color | Badge |
|----------|-------|-------|
| ORB Breakout | `#4a9eff` (blue) | `rgba(74,158,255,0.15)` bg |
| VWAP Reversion | `#a855f7` (purple) | `rgba(168,85,247,0.15)` bg |
| PDH/PDL Breakout | `#ffd700` (yellow) | `rgba(255,215,0,0.15)` bg |
| Gap Fill | `#00ff88` (green) | `rgba(0,255,136,0.15)` bg |

### Status Colors
| Status | Color | Meaning |
|--------|-------|---------|
| target | `#00ff88` | Profit target hit |
| stopped | `#ff4444` | Stop loss hit |
| eod | `#4a9eff` | End-of-day exit |
| pending_next_day | `#a855f7` | Awaiting next session |

## Typography

### Font Family
- Primary: `Inter` (300, 400, 500, 600, 700, 800)
- Fallback: `system-ui, sans-serif`

### Type Scale
| Element | Size | Weight | Usage |
|---------|------|--------|-------|
| Page heading (h2) | 18px | 700 | Section titles |
| Card heading (h3/h4) | 14px / 12px | 600 | Widget titles |
| Metric value | 22-28px | 700 | Big numbers in cards |
| Metric label | 10-12px | 600 | Uppercase, letter-spaced |
| Table header | 11px | 600 | Uppercase, letter-spaced |
| Table body | 13px | 400 | Data cells |
| Badge text | 10px | 600 | Status/strategy badges |
| Helper/caption | 12px | 400 | Muted color (#94a3b8) |

## Layout

### Sidebar
- Width: 240px (desktop), collapses to 64px
- Mobile: full-width bottom sheet (70px height), slide-in from left
- Fixed position, z-index: 40

### Main Content
- Margin-left: 240px (desktop), 0 (mobile)
- Padding: 24px (desktop), 16px (mobile)
- Padding-bottom: 90px (mobile, for bottom sidebar)

### Grid System
| Class | Columns | Usage |
|-------|---------|-------|
| grid-4 | 4 × 1fr | Dashboard metrics, monthly heatmap |
| grid-2 | 2 × 1fr | Charts side-by-side, portfolio |
| Mobile | 1 column | Stack everything |

### Section Header Pattern
```
[Icon badge] [H2 title]
[Description paragraph]       [Last updated + Refresh button]
```
- Flex: space-between, align-items: flex-start
- Gap: 16px between title block and action block
- Margin-bottom: 20px

## Components

### Cards
- Background: `#12121a`
- Border: 1px solid `#1e1e2e`
- Border-radius: 12px
- Padding: 20px (standard), 16px (compact)
- Hover: border `#2a2a3e`, translateY(-1px)
- Transition: all 0.2s ease

### Metric Cards
- Base card + optional glow circle (60px, absolute top-right corner)
- Glow colors match accent (green/blue/yellow/purple at 0.08 opacity)
- Metric value: 22-28px, font-weight 700
- Metric label: 10-12px, uppercase, letter-spacing 0.5px, `#94a3b8`

### Buttons
| Variant | Background | Text | Hover |
|---------|-----------|------|-------|
| Primary | `#4a9eff` | `#fff` | `#3a8eef` |
| Danger | `#ff4444` | `#fff` | `#ee3333` |
| Ghost | transparent | `#888` | `#1a1a25` + `#e0e0e0` text |
- Padding: 8px 16px
- Border-radius: 8px
- Font-size: 13px, weight 500
- Transition: all 0.15s ease

### Tables
- Font-size: 13px
- Border-collapse: separate, border-spacing: 0
- Sticky thead: `position: sticky; top: 0`
- Th: `#94a3b8`, uppercase, 11px, cursor pointer
- Td: `#e0e0e0`, border-bottom `#141e1e`
- Zebra: `tr:nth-child(even)` → `#0d0d14`
- Hover row: `#1a1a25`
- Mobile: overflow-x auto, font-size 11px

### Badges
- Padding: 2px 8px (strategy) / 2px 6px (direction/status)
- Border-radius: 4px
- Font-size: 10px, weight 600
- Background: `rgba(color, 0.15)` with 1px solid `rgba(color, 0.3)` border

### Charts (Chart.js)
- Max-height: 280px (desktop), 200px (mobile)
- Responsive, maintainAspectRatio: false
- Grid color: `#1e1e2e`, tick color: `#666`, font-size: 10px
- Legend labels: `#888`, font-size: 11px

## Scrollbar
- Width: 10px
- Track: `#0a0a0f`
- Thumb: `#2a2a3a`, border-radius: 5px
- Thumb hover: `#3a3a4a`

## Accessibility
- Skip to main content link
- Focus-visible: 2px solid `#4a9eff`, offset 2px
- ARIA labels on all interactive elements
- Keyboard shortcuts: N (New Trade), D (Dashboard), J (Journal), E (Optimizer), Escape (close modals), ? (help)
- Sidebar nav items: tabindex="0", role="button", Enter/Space activation
- Checkboxes: tabindex="0", role="checkbox", aria-checked

## Light Theme
- Toggled via theme switch in sidebar
- bg: `#f5f5f7`, card: `#fff`, text: `#1a1a2e`
- All colors adapt via `html.light` overrides

## File Structure
```
trading_dashboard.html    # Single-file dashboard (HTML + CSS + JS)
scripts/
  gen_paper_data.js       # Seed data generator from backtest CSVs
data/
  paper_trades.csv        # Paper trade history
  paper_portfolio.json    # Portfolio equity & metrics
  signals_next_day.csv    # Next-day trading signals
.github/workflows/
  paper-trade.yml         # Daily GitHub Actions (weekdays 4:15pm ET)
```

## Deviations from Design System
None documented yet. All new components should follow this spec.