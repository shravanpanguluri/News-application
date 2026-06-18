import React, { useState, useEffect } from 'react';
import { Segment, Header, Icon, Loader, Label, Input, Button, Table } from 'semantic-ui-react';
import { BACKEND_URL } from '../../API/governmentApi';
import './EarningsCalendarWidget.css';

const DEFAULT_TICKERS = 'AAPL,MSFT,GOOGL,AMZN,TSLA,META,NVDA,JPM,BAC,XOM,LMT,RTX,BA,NOC,GD';

export default function EarningsCalendarWidget() {
  const [earnings, setEarnings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tickerInput, setTickerInput] = useState('');
  const [tickers, setTickers] = useState(DEFAULT_TICKERS);
  const [days, setDays] = useState(45);

  const fetchEarnings = async function(tkrs, d) {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(BACKEND_URL + '/api/earnings/upcoming?tickers=' + encodeURIComponent(tkrs) + '&days=' + d);
      const data = await res.json();
      setEarnings(data.earnings || []);
    } catch (e) {
      setError('Failed to load earnings data');
    }
    setLoading(false);
  };

  useEffect(function() {
    fetchEarnings(tickers, days);
  }, []);

  const handleAddTicker = function() {
    const t = tickerInput.trim().toUpperCase();
    if (!t) return;
    const updated = tickers + ',' + t;
    setTickers(updated);
    setTickerInput('');
    fetchEarnings(updated, days);
  };

  const dirColor = function(dir) {
    if (dir === 'BULLISH') return 'green';
    if (dir === 'BEARISH') return 'red';
    return 'grey';
  };

  const daysLabel = function(n) {
    if (n === 0) return 'Today';
    if (n === 1) return 'Tomorrow';
    return 'In ' + n + ' days';
  };

  return (
    <div className="ec-widget">
      <div className="ec-header">
        <span className="ec-title">Earnings Calendar</span>
        <div className="ec-controls">
          <select
            className="ec-days-select"
            value={days}
            onChange={function(e) {
              var d = parseInt(e.target.value);
              setDays(d);
              fetchEarnings(tickers, d);
            }}
          >
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
            <option value={45}>45 days</option>
            <option value={90}>90 days</option>
          </select>
          <div className="ec-add-ticker">
            <input
              className="ec-ticker-input"
              placeholder="Add ticker…"
              value={tickerInput}
              onChange={function(e) { setTickerInput(e.target.value.toUpperCase()); }}
              onKeyDown={function(e) { if (e.key === 'Enter') handleAddTicker(); }}
            />
            <button className="ec-add-btn" onClick={handleAddTicker}>+</button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="ec-loading">
          <Loader active inline size="small" />
          <span>Fetching earnings dates…</span>
        </div>
      ) : error ? (
        <div className="ec-error">{error}</div>
      ) : earnings.length === 0 ? (
        <div className="ec-empty">No upcoming earnings in the next {days} days for tracked tickers.</div>
      ) : (
        <div className="ec-table-wrap">
          <table className="ec-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Company</th>
                <th>Date</th>
                <th>When</th>
                <th>Price</th>
                <th>EPS Est.</th>
                <th>ML Signal</th>
              </tr>
            </thead>
            <tbody>
              {earnings.map(function(e, i) {
                var mlDirection = e.ml_direction || (e.prediction === 'UP' ? 'BULLISH' : e.prediction === 'DOWN' ? 'BEARISH' : 'NEUTRAL');
                var mlConfidence = e.ml_confidence || Math.round((e.confidence || 0.62) * 100);
                return (
                  <tr key={i} className={'ec-row ec-row--' + mlDirection.toLowerCase()}>
                    <td className="ec-sym">{e.ticker}</td>
                    <td className="ec-name">{e.company_name || e.ticker}</td>
                    <td className="ec-date">{e.earnings_date}</td>
                    <td className="ec-when">{daysLabel(e.days_until || 0)}</td>
                    <td className="ec-price">{e.current_price ? '$' + e.current_price : '—'}</td>
                    <td className="ec-eps">{e.eps_estimate ? '$' + parseFloat(e.eps_estimate).toFixed(2) : '—'}</td>
                    <td className="ec-signal">
                      <span className={'ec-badge ec-badge--' + dirColor(mlDirection)}>
                        {mlDirection} {mlConfidence}%
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <div className="ec-footer">
        ML signals based on {earnings.length} upcoming events · {tickers.split(',').length} tickers tracked
      </div>
    </div>
  );
}
