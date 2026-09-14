# Trading Dashboard

A complete, interactive, responsive trading dashboard web application for displaying backtest results and live trading tools.

## Quick Start

1. Open `trading_dashboard.html` in any modern browser
2. No build step, no server required — just open the file

## Features

### 8 Interactive Sections

| Section | Description |
|---------|-------------|
| **Dashboard** | Account balance, equity curve, monthly heatmap, daily P&L, recent trades |
| **Strategy Comparison** | Performance tables, win/loss distribution, equity curves per strategy, risk/reward scatter |
| **ORB Optimizer** | Interactive parameter controls, optimization heatmap, top 5 parameter combos |
| **Portfolio Analyzer** | 4 portfolio types, allocation charts, Monte Carlo simulation, portfolio comparison |
| **Trade Journal** | Add/edit/delete trades, statistics panel, CSV export, localStorage persistence |
| **Strategy Rules** | Accordion cards for each strategy, entry/exit rules, risk management section |
| **Live Checklist** | Interactive checkboxes, session timer, progress bar, emergency stop button |
| **Backtest Data** | CSV upload with drag-and-drop, data preview, client-side backtest runner |

### Interactive Features

- **Dark/Light mode** — toggle via sidebar (persisted in localStorage)
- **Collapsible sidebar** — click collapse button or resize window
- **Sortable tables** — click any column header to sort
- **CSV export** — export any table to CSV
- **Chart export** — export any chart as PNG
- **Keyboard shortcuts** — N (new trade), D (dashboard), J (journal), Esc (close modals)
- **Toast notifications** — feedback for all actions
- **LocalStorage persistence** — journal, checklist, ORB levels, theme preference

### Charts (Chart.js)

- Equity Curve (line)
- Monthly Returns Heatmap (color-coded grid)
- Daily P&L Bar Chart (green/red)
- Win/Loss Distribution (histogram)
- Strategy Allocation (doughnut)
- Strategy Equity Curves (overlaid lines)
- Risk/Reward Scatter Plot
- Monte Carlo Simulation (histogram)
- Backtest Equity Curve

### Mobile Responsive

- Sidebar converts to bottom navigation on mobile
- Cards stack vertically on small screens
- Charts resize properly
- Touch-friendly buttons and inputs

## Sample Data

The dashboard includes 55 sample trades spanning January-August 2026 across 4 strategies:
- ORB Breakout
- VWAP Reversion
- PDH/PDL Breakout
- Gap Fill

## Tech Stack

- **HTML5** — single file, no build step
- **Tailwind CSS** (CDN) — utility-first styling
- **Chart.js** (CDN) — interactive charts
- **Inter** (Google Fonts) — clean typography
- **LocalStorage** — client-side persistence

## File Structure

```
trading_dashboard.html   — Main application (single file, ~86KB)
dashboard_readme.md      — This documentation
```

## Usage Tips

1. **Add your first trade**: Click "+ New Trade" or navigate to Journal section
2. **Run optimization**: Go to ORB Optimizer, adjust parameters, click "Run Optimization"
3. **Compare portfolios**: Click through the portfolio tabs, run Monte Carlo simulation
4. **Upload real data**: Go to Backtest, drag-and-drop a CSV file with OHLCV data
5. **Track your checklist**: Mark items complete during your trading session
6. **Export data**: Use CSV buttons on any table to export your data

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `N` | Open new trade modal |
| `D` | Navigate to Dashboard |
| `J` | Navigate to Journal |
| `Esc` | Close any open modal |

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## License

Free to use and modify.
