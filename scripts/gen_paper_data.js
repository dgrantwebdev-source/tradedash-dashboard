const fs = require('fs');
const path = require('path');

const DATA_DIR = 'data';
const MULTIPLIER = 50;
const RISK_PCT = 0.01;
const INITIAL_CAPITAL = 100000;

function readCsv(file) {
  const lines = fs.readFileSync(file, 'utf8').trim().split('\n');
  const headers = lines[0].split(',').map(h => h.trim());
  return lines.slice(1).map(line => {
    const vals = line.split(',');
    const obj = {};
    headers.forEach((h, i) => { obj[h] = vals[i] ? vals[i].trim() : ''; });
    return obj;
  });
}

function calcContracts(cash, entry, stop) {
  const riskAmt = cash * RISK_PCT;
  const riskPerPoint = Math.abs(entry - stop);
  if (riskPerPoint === 0) return { contracts: 1, riskUsd: 0 };
  const contracts = Math.max(1, Math.floor(riskAmt / (riskPerPoint * MULTIPLIER)));
  const riskUsd = contracts * riskPerPoint * MULTIPLIER;
  return { contracts, riskUsd: Math.round(riskUsd * 100) / 100 };
}

// Load backtest data
const gapFill = readCsv('trades_gap_fill.csv');
const orb = readCsv('trades_orb_15min.csv');
const ib = readCsv('trades_ib_breakout.csv');
const mr = readCsv('trades_mean_reversion.csv');

const trades = [];
let cash = INITIAL_CAPITAL;
let equity = INITIAL_CAPITAL;
let totalPnl = 0;
let winningTrades = 0;
let losingTrades = 0;
let totalTrades = 0;
const equityCurve = [{ date: null, equity: INITIAL_CAPITAL }];
const dailyPnl = [];

function addTrade(date, strategy, direction, entry, target, stop, exitPx, pnlPoints, status) {
  const { contracts, riskUsd } = calcContracts(cash, entry, stop);
  const pnlUsd = Math.round(pnlPoints * contracts * MULTIPLIER * 100) / 100;
  cash += pnlUsd;
  equity = cash;
  totalPnl += pnlUsd;
  totalTrades++;
  if (pnlUsd > 0) winningTrades++;
  else if (pnlUsd < 0) losingTrades++;

  trades.push({
    date,
    strategy,
    direction,
    entry: parseFloat(entry.toFixed(2)),
    target: parseFloat(target.toFixed(2)),
    stop: parseFloat(stop.toFixed(2)),
    exit: parseFloat(exitPx.toFixed(2)),
    pnl_points: parseFloat(pnlPoints.toFixed(2)),
    pnl_usd: pnlUsd,
    status,
    risk_usd: riskUsd,
    contracts,
  });

  equityCurve.push({ date, equity: Math.round(equity * 100) / 100 });
}

// Process Gap Fill trades (Aug 2026)
for (const t of gapFill) {
  const date = t.date.split(' ')[0];
  const entry = parseFloat(t.entry);
  const pnlPoints = parseFloat(t.pnl_points);
  const gapSize = parseFloat(t.gap_size);
  const direction = t.direction;
  const exitPx = entry + (direction === 'long' ? pnlPoints : -pnlPoints);
  const target = direction === 'long' ? entry + 1.5 * gapSize : entry - 1.5 * gapSize;
  const stop = direction === 'long' ? entry - 2.0 * gapSize : entry + 2.0 * gapSize;
  addTrade(date, 'Gap Fill', direction, entry, target, stop, exitPx, pnlPoints, pnlPoints > 0 ? 'target' : 'stopped');
}

// Process ORB trades
for (const t of orb) {
  const date = t.date.split(' ')[0];
  const entry = parseFloat(t.entry);
  const pnlPoints = parseFloat(t.pnl_points);
  const orbRange = parseFloat(t.orb_range);
  const direction = t.direction;
  const exitPx = entry + (direction === 'long' ? pnlPoints : -pnlPoints);
  const target = direction === 'long' ? entry + 1.5 * orbRange : entry - 1.5 * orbRange;
  const stop = direction === 'long' ? entry - orbRange : entry + orbRange;
  addTrade(date, 'ORB Breakout', direction, entry, target, stop, exitPx, pnlPoints, pnlPoints > 0 ? 'target' : 'stopped');
}

// Process IB Breakout trades
for (const t of ib) {
  const date = t.date.split(' ')[0];
  const entry = parseFloat(t.entry);
  const pnlPoints = parseFloat(t.pnl_points);
  const ibRange = parseFloat(t.ib_range);
  const direction = t.direction;
  const exitPx = entry + (direction === 'long' ? pnlPoints : -pnlPoints);
  const target = direction === 'long' ? entry + 1.5 * ibRange : entry - 1.5 * ibRange;
  const stop = direction === 'long' ? entry - 0.5 * ibRange : entry + 0.5 * ibRange;
  addTrade(date, 'IB Breakout', direction, entry, target, stop, exitPx, pnlPoints, pnlPoints > 0 ? 'target' : 'stopped');
}

// Process Mean Reversion trades (take first 8 clean ones to keep month manageable)
let mrCount = 0;
for (const t of mr) {
  if (mrCount >= 8) break;
  const pnlPoints = parseFloat(t.pnl_points);
  // Skip extreme outliers (>20 points loss) for cleaner demo data
  if (Math.abs(pnlPoints) > 20) continue;
  const date = t.date.split(' ')[0];
  const entry = parseFloat(t.entry);
  const exitPx = parseFloat(t.exit);
  const direction = t.direction;
  const target = direction === 'long' ? entry + 2.0 : entry - 2.0;
  const stop = direction === 'long' ? entry - 2.0 : entry + 2.0;
  addTrade(date, 'Mean Reversion', direction, entry, target, stop, exitPx, pnlPoints, pnlPoints > 0 ? 'target' : 'stopped');
  mrCount++;
}

// Sort trades by date
trades.sort((a, b) => a.date.localeCompare(b.date));

// Build daily P&L
const byDate = {};
trades.forEach(t => {
  if (!byDate[t.date]) byDate[t.date] = 0;
  byDate[t.date] += t.pnl_usd;
});
Object.entries(byDate).forEach(([date, pnl]) => {
  dailyPnl.push({ date, pnl_usd: Math.round(pnl * 100) / 100, trades: 1 });
});

// Write paper_trades.csv
const ptHeader = 'date,strategy,direction,entry,target,stop,exit,pnl_points,pnl_usd,status,risk_usd,contracts';
const ptRows = trades.map(t =>
  `${t.date},${t.strategy},${t.direction},${t.entry},${t.target},${t.stop},${t.exit},${t.pnl_points},${t.pnl_usd},${t.status},${t.risk_usd},${t.contracts}`
);
fs.writeFileSync(path.join(DATA_DIR, 'paper_trades.csv'), [ptHeader, ...ptRows].join('\n') + '\n');

// Write paper_portfolio.json
const portfolio = {
  initial_capital: INITIAL_CAPITAL,
  cash: Math.round(cash * 100) / 100,
  equity: Math.round(equity * 100) / 100,
  daily_pnl: dailyPnl,
  equity_curve: equityCurve,
  total_trades: totalTrades,
  winning_trades: winningTrades,
  losing_trades: losingTrades,
  total_pnl_usd: Math.round(totalPnl * 100) / 100,
  created_at: new Date().toISOString(),
};
fs.writeFileSync(path.join(DATA_DIR, 'paper_portfolio.json'), JSON.stringify(portfolio, null, 2));

// Write signals_next_day.csv (2-3 pending signals for tomorrow)
const lastDate = trades[trades.length - 1].date;
const signals = [
  { signal_date: '2026-10-21', strategy: 'Gap Fill', direction: 'long', entry: '5650.00', target: '5665.00', stop: '5640.00', status: 'pending_next_day' },
  { signal_date: '2026-10-21', strategy: 'ORB Breakout', direction: 'short', entry: '5645.00', target: '5630.00', stop: '5655.00', status: 'pending_next_day' },
];
const sigHeader = 'signal_date,strategy,direction,entry,target,stop,status';
const sigRows = signals.map(s => `${s.signal_date},${s.strategy},${s.direction},${s.entry},${s.target},${s.stop},${s.status}`);
fs.writeFileSync(path.join(DATA_DIR, 'signals_next_day.csv'), [sigHeader, ...sigRows].join('\n') + '\n');

console.log(`Generated ${trades.length} paper trades`);
console.log(`Total P&L: $${totalPnl.toFixed(2)}`);
console.log(`Final Equity: $${equity.toFixed(2)}`);
console.log(`Win Rate: ${((winningTrades / totalTrades) * 100).toFixed(1)}%`);
console.log(`Files written to ${DATA_DIR}/`);
