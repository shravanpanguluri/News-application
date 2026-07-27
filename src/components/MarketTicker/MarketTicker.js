import React, { useState, useEffect } from 'react';
import { rssAPI } from '../../API/governmentApi';
import './MarketTicker.css';

const MarketTicker = () => {
    const [prices, setPrices] = useState({ crypto: [], forex: [], stocks: [], metals: [] });
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchPrices = async () => {
            try {
                const data = await rssAPI.getMarketPrices();
                console.log('Market data received:', data);
                if (data) {
                    setPrices({
                        crypto: data.crypto || [],
                        forex: data.forex || [],
                        stocks: data.stocks || [],
                        metals: data.metals || [],
                        bonds: data.bonds || [],
                        etfs: data.etfs || []
                    });
                }
            } catch (err) {
                console.error('Error fetching market prices:', err);
                setError(err.message);
                
                // Retry after 5 seconds if backend is waking up
                if (err.code === 'ECONNABORTED' || err.message.includes('timeout')) {
                    console.log('Backend waking up, retrying in 5s...');
                    setTimeout(fetchPrices, 5000);
                }
            }
        };

        fetchPrices();
        const interval = setInterval(fetchPrices, 60000); // Update every minute
        return () => clearInterval(interval);
    }, []);

    // Combine all markets with priority: stocks > metals > crypto > forex
    const allMarkets = [
        ...(prices.stocks || []).slice(0, 15),  // Top 15 stocks
        ...(prices.metals || []).slice(0, 5),   // Top 5 metals
        ...(prices.crypto || []).slice(0, 10),  // Top 10 crypto
        ...(prices.forex || []).slice(0, 5)     // Top 5 forex
    ];

    if (allMarkets.length === 0) {
        return (
            <div className="gp-ticker">
                <div className="gp-ticker-tag">LIVE MARKETS</div>
                <div className="gp-ticker-track">
                    <div className="gp-ticker-rail">
                        <div className="gp-ticker-item">Loading market data...</div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="gp-ticker">
            <div className="gp-ticker-tag">LIVE MARKETS</div>
            <div className="gp-ticker-track">
                <div className="gp-ticker-rail">
                    {allMarkets.concat(allMarkets).map((item, index) => (
                        <div key={`${index}-${item.symbol}`} className="gp-ticker-item">
                            <span className="gp-ticker-sym">{item.symbol}</span>
                            <span className="gp-ticker-px">${Number(item.price || 0).toLocaleString()}</span>
                            {item.change !== undefined && item.change !== 0 && (
                                <span className={`gp-ticker-chg ${item.change >= 0 ? 'up' : 'dn'}`}>
                                    {item.change >= 0 ? '▲' : '▼'} {Math.abs(item.change)}%
                                </span>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default MarketTicker;
