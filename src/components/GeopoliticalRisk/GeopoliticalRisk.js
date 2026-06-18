import React, { useState, useEffect } from 'react';
import { Loader } from 'semantic-ui-react';
import { BACKEND_URL } from '../../API/governmentApi';
import './GeopoliticalRisk.css';

export default function GeopoliticalRisk() {
  var [regions, setRegions] = useState([]);
  var [loading, setLoading] = useState(true);
  var [days, setDays] = useState(7);
  var [asOf, setAsOf] = useState('');
  var [expanded, setExpanded] = useState(null);

  var fetchRisk = async function(d) {
    setLoading(true);
    try {
      var res = await fetch(BACKEND_URL + '/api/geopolitical/risk?days=' + d);
      var data = await res.json();
      setRegions(data.regions || []);
      setAsOf(data.as_of || '');
    } catch (e) {
      setRegions([]);
    }
    setLoading(false);
  };

  useEffect(function() {
    fetchRisk(days);
  }, []);

  var riskColor = function(level) {
    if (level === 'HIGH') return 'gr-high';
    if (level === 'MEDIUM') return 'gr-medium';
    return 'gr-low';
  };

  var barWidth = function(score) {
    return Math.min(100, score) + '%';
  };

  var formatDate = function(iso) {
    if (!iso) return '';
    try { return new Date(iso).toLocaleString(); } catch (e) { return iso; }
  };

  return (
    <div className="gr-widget">
      <div className="gr-header">
        <span className="gr-title">Geopolitical Risk Monitor</span>
        <div className="gr-controls">
          {[3, 7, 14, 30].map(function(d) {
            return (
              <button
                key={d}
                className={'gr-day-btn' + (days === d ? ' gr-day-btn--active' : '')}
                onClick={function() {
                  setDays(d);
                  fetchRisk(d);
                }}
              >
                {d}d
              </button>
            );
          })}
        </div>
      </div>

      {loading ? (
        <div className="gr-loading">
          <Loader active inline size="small" />
          <span>Scanning GDELT global news…</span>
        </div>
      ) : regions.length === 0 ? (
        <div className="gr-empty">No data available.</div>
      ) : (
        <div className="gr-list">
          {regions.map(function(region, i) {
            var isExpanded = expanded === region.region;
            var riskLevel = region.risk_level || region.level || 'LOW';
            return (
              <div key={region.region} className="gr-region-row">
                <div
                  className="gr-region-main"
                  onClick={function() { setExpanded(isExpanded ? null : region.region); }}
                  style={{ cursor: 'pointer' }}
                >
                  <div className="gr-rank">#{i + 1}</div>
                  <div className="gr-region-info">
                    <div className="gr-region-name">{region.region}</div>
                    <div className="gr-bar-wrap">
                      <div
                        className={'gr-bar ' + riskColor(riskLevel)}
                        style={{ width: barWidth(region.risk_score) }}
                      />
                    </div>
                  </div>
                  <div className="gr-region-right">
                    <span className={'gr-risk-badge gr-risk-badge--' + riskLevel.toLowerCase()}>
                      {riskLevel}
                    </span>
                    <span className="gr-score">{region.risk_score}</span>
                    <span className="gr-articles">{region.article_count || 0} articles</span>
                    <span className={'gr-chevron' + (isExpanded ? ' gr-chevron--open' : '')}>›</span>
                  </div>
                </div>

                {isExpanded && region.sample_headlines && region.sample_headlines.length > 0 && (
                  <div className="gr-headlines">
                    {region.sample_headlines.map(function(h, j) {
                      return (
                        <div key={j} className="gr-headline">
                          <span className="gr-headline-dot">·</span>
                          {h}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {asOf && (
        <div className="gr-footer">
          GDELT global news index · Updated {formatDate(asOf)} · {days}-day window
        </div>
      )}
    </div>
  );
}
