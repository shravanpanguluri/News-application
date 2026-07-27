import React, { useState } from 'react';
import EarningsCalendarWidget from './EarningsCalendarWidget/EarningsCalendarWidget';
import GeopoliticalRisk from './GeopoliticalRisk/GeopoliticalRisk';
import EventExplainer from './EventExplainer/EventExplainer';
import { BACKEND_URL } from '../API/governmentApi';
import './TradingIntelligenceDashboard.css';

const TICKERS = ['AAPL', 'MSFT', 'TSLA', 'NVDA', 'JPM', 'LMT', 'BA', 'XOM'];

function SignalTimeline() {
  const [ticker, setTicker] = useState('AAPL');
  const [days, setDays] = useState('90');
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/predict/explain/${ticker}?limit=10`);
      const data = await response.json();
      setEvents(data.events || []);
    } catch (error) {
      setEvents([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="ti-panel ti-timeline">
      <header className="ti-panel-header">
        <em>Government Signal Timeline</em>
        <span>EVENT SIGNAL VS. STOCK RETURN CORRELATION</span>
      </header>
      <div className="ti-presets">
        {TICKERS.map((item) => <button key={item} className={ticker === item ? 'active' : ''} onClick={() => setTicker(item)}>{item}</button>)}
      </div>
      <div className="ti-inline-form">
        <input value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} />
        <button onClick={load}>Go</button>
        <div className="ti-range">{['30d', '60d', '90d', '180d'].map((item) => <button key={item} className={days === item.slice(0, -1) ? 'active' : ''} onClick={() => setDays(item.slice(0, -1))}>{item}</button>)}</div>
      </div>
      <div className="ti-empty-area">
        {loading ? 'Loading signal history…' : events.length ? `${events.length} government signals found for ${ticker}.` : 'Select a ticker above to see which government events most strongly moved the stock historically.'}
      </div>
    </section>
  );
}

function InsiderTradingFeed() {
  const [ticker, setTicker] = useState('');
  const [filings, setFilings] = useState([]);
  const [loading, setLoading] = useState(false);
  const load = async () => {
    if (!ticker.trim()) return;
    setLoading(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/sec/insider/${ticker.trim().toUpperCase()}`);
      const data = await response.json();
      setFilings(data.filings || []);
    } catch (error) {
      setFilings([]);
    } finally {
      setLoading(false);
    }
  };
  return (
    <section className="ti-panel ti-insider">
      <header className="ti-panel-header"><em>Insider Trading Feed</em><span>SEC EDGAR FORM 4 · LAST 180 DAYS</span></header>
      <div className="ti-inline-form ti-insider-form">
        <input placeholder="ENTER TICKER SYMBOL (E.G. AAPL)" value={ticker} onChange={(event) => setTicker(event.target.value.toUpperCase())} onKeyDown={(event) => event.key === 'Enter' && load()} />
        <button onClick={load}>{loading ? 'LOADING…' : 'SEARCH SEC'}</button>
      </div>
      <div className="ti-empty-area">{filings.length ? `${filings.length} insider filings found for ${ticker}.` : 'Search any ticker to see Form 4 insider transaction filings from the SEC'}</div>
    </section>
  );
}

export default function TradingIntelligenceDashboard() {
  return (
    <div className="trading-intel-dashboard">
      <EarningsCalendarWidget />
      <div className="ti-two-col"><SignalTimeline /><GeopoliticalRisk /></div>
      <EventExplainer />
      <InsiderTradingFeed />
    </div>
  );
}
