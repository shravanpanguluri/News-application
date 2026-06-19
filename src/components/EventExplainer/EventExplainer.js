import React, { useState } from 'react';
import { BACKEND_URL } from '../../API/governmentApi';
import './EventExplainer.css';

export default function EventExplainer(props) {
  // props.ticker — pre-filled ticker (optional)
  var [ticker, setTicker] = useState(props.ticker || '');
  var [inputVal, setInputVal] = useState(props.ticker || '');
  var [events, setEvents] = useState([]);
  var [stats, setStats] = useState(null);
  var [loading, setLoading] = useState(false);
  var [error, setError] = useState(null);

  var fetchExplanation = async function(t) {
    var sym = t.trim().toUpperCase();
    if (!sym) return;
    setLoading(true);
    setError(null);
    try {
      var res = await fetch(BACKEND_URL + '/api/predict/explain/' + encodeURIComponent(sym) + '?limit=10');
      var data = await res.json();
      setEvents(data.events || []);
      setStats({
        total: data.total_events || 0,
        bullish: data.bullish_pct || 50,
        avg7d: data.avg_7d_return || 0,
      });
      setTicker(sym);
      if (data.events && data.events.length === 0) {
        setError('No historical events found for ' + sym + ' in the training dataset.');
      }
    } catch (e) {
      setError('Failed to fetch event data');
    }
    setLoading(false);
  };

  var dirClass = function(dir) {
    return dir === 'UP' ? 'ee-up' : 'ee-dn';
  };

  var fmtReturn = function(r) {
    if (r === null || r === undefined) return '—';
    var n = parseFloat(r);
    return (n >= 0 ? '+' : '') + n.toFixed(2) + '%';
  };

  var fmtAmt = function(a) {
    if (!a) return null;
    if (a >= 1e9) return '$' + (a / 1e9).toFixed(1) + 'B';
    if (a >= 1e6) return '$' + (a / 1e6).toFixed(1) + 'M';
    return '$' + a.toLocaleString();
  };

  var formatDate = function(d) {
    if (!d) return '';
    return d.substring(0, 10);
  };

  var PRESET_TICKERS = ['AAPL', 'MSFT', 'TSLA', 'NVDA', 'LMT', 'BA', 'JPM', 'XOM'];

  return (
    <div className="ee-wrap">
      <div className="ee-header">
        <span className="ee-title">"Why Did This Move?"</span>
        <span className="ee-sub">Top government events correlated with {ticker || 'price'} moves</span>
      </div>

      <div className="ee-search">
        <div className="ee-presets">
          {PRESET_TICKERS.map(function(t) {
            return (
              <button
                key={t}
                className={'ee-preset' + (ticker === t ? ' ee-preset--active' : '')}
                onClick={function() {
                  setInputVal(t);
                  fetchExplanation(t);
                }}
              >
                {t}
              </button>
            );
          })}
        </div>
        <div className="ee-search-row">
          <input
            className="ee-input"
            placeholder="Any ticker…"
            value={inputVal}
            onChange={function(e) { setInputVal(e.target.value.toUpperCase()); }}
            onKeyDown={function(e) { if (e.key === 'Enter') fetchExplanation(inputVal); }}
          />
          <button className="ee-go-btn" onClick={function() { fetchExplanation(inputVal); }}>
            Explain
          </button>
        </div>
      </div>

      {loading && <div className="ee-loading">Scanning {events.length > 0 ? ticker : '…'} event history…</div>}
      {!loading && error && <div className="ee-error">{error}</div>}

      {!loading && stats && events.length > 0 && (
        <>
          <div className="ee-stats">
            <div className="ee-stat">
              <div className="ee-stat-val">{stats.total}</div>
              <div className="ee-stat-lbl">Total Events</div>
            </div>
            <div className="ee-stat">
              <div className={'ee-stat-val' + (stats.bullish >= 50 ? ' ee-up' : ' ee-dn')}>{stats.bullish}%</div>
              <div className="ee-stat-lbl">Bullish Outcomes</div>
            </div>
            <div className="ee-stat">
              <div className="ee-stat-val">{stats.avg7d}%</div>
              <div className="ee-stat-lbl">Avg 7d Move</div>
            </div>
          </div>

          <div className="ee-events">
            {events.map(function(ev, i) {
              var direction = (ev.direction || '').toUpperCase();
              if (!direction) direction = ((ev.return_7d || 0) >= 0 ? 'UP' : 'DOWN');
              var isNeutral = direction === 'NO_SIGNAL' || direction === 'NEUTRAL' || direction === 'FLAT' || direction === 'UNKNOWN';
              var rowDir = isNeutral ? 'neutral' : direction.toLowerCase();
              return (
                <div key={i} className={'ee-event-row ee-event-row--' + rowDir}>
                  <div className="ee-event-rank">#{i + 1}</div>
                  <div className="ee-event-body">
                    <div className="ee-event-title">{ev.event_title || ev.title || ev.event_type}</div>
                    <div className="ee-event-meta">
                      <span className="ee-event-type">{ev.event_type}</span>
                      {ev.event_date && <span className="ee-event-date">{formatDate(ev.event_date)}</span>}
                      {ev.source && <span className="ee-event-source">{ev.source}</span>}
                      {ev.award_amount && <span className="ee-event-amt">{fmtAmt(ev.award_amount)}</span>}
                    </div>
                  </div>
                  <div className="ee-event-returns">
                    <div className={'ee-ret-item ' + (ev.return_1d >= 0 ? 'ee-up' : 'ee-dn')}>
                      <span className="ee-ret-label">1d</span>
                      <span className="ee-ret-val">{fmtReturn(ev.return_1d)}</span>
                    </div>
                    <div className={'ee-ret-item ' + (ev.return_7d >= 0 ? 'ee-up' : 'ee-dn')}>
                      <span className="ee-ret-label">7d</span>
                      <span className="ee-ret-val">{fmtReturn(ev.return_7d)}</span>
                    </div>
                    <div className={'ee-ret-item ' + ((ev.return_30d || 0) >= 0 ? 'ee-up' : 'ee-dn')}>
                      <span className="ee-ret-label">30d</span>
                      <span className="ee-ret-val">{fmtReturn(ev.return_30d)}</span>
                    </div>
                  </div>
                  <div className={'ee-dir-pill ee-dir-pill--' + rowDir}>
                    {isNeutral ? '•' : direction === 'UP' ? '▲' : '▼'} {isNeutral ? 'NO SIGNAL' : direction}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="ee-footer">
            Top {events.length} highest-impact events from {stats.total} total · Ranked by absolute 7d return
          </div>
        </>
      )}

      {!ticker && !loading && (
        <div className="ee-prompt">
          <div className="ee-prompt-icon">🔍</div>
          <div>Select a ticker above to see which government events most strongly moved the stock historically.</div>
        </div>
      )}
    </div>
  );
}
