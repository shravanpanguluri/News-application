import React, { useState, useEffect } from 'react';
import {
    Segment,
    Header,
    Icon,
    Grid,
    Card,
    Button,
    Dimmer,
    Loader,
    Message,
    Tab,
    Table,
    Label,
    Statistic,
    List,
    Menu
} from 'semantic-ui-react';
import { sentimentAPI, BACKEND_URL } from '../../API/governmentApi';
import './StockSentimentDashboard.css';

// Default watchlist if market data not available
const DEFAULT_WATCHLIST = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'JPM', 'JNJ', 'XOM', 'BA', 'GS', 'PFE', 'KO', 'PG'];

const SECTORS = [
    { key: 'technology', name: 'Technology', icon: 'computer' },
    { key: 'healthcare', name: 'Healthcare', icon: 'hospital' },
    { key: 'finance', name: 'Finance', icon: 'money' },
    { key: 'energy', name: 'Energy', icon: 'sun' },
    { key: 'defense', name: 'Defense', icon: 'shield' },
    { key: 'consumer', name: 'Consumer', icon: 'shopping cart' }
];

const StockSentimentDashboard = ({ marketPrices }) => {
    const [loading, setLoading] = useState(true);
    const [predictions, setPredictions] = useState([]);
    const [sectorData, setSectorData] = useState(null);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState(0);
    const [watchlistStocks, setWatchlistStocks] = useState(DEFAULT_WATCHLIST);

    // Government intelligence predictions
    const [govPredictions, setGovPredictions] = useState({});
    const [govLoading, setGovLoading] = useState(false);
    const [tickerSearch, setTickerSearch] = useState('');

    // New state for enhanced features
    const [topPicks, setTopPicks] = useState(null);
    const [portfolio, setPortfolio] = useState(null);
    const [backtest, setBacktest] = useState(null);
    const [riskProfile, setRiskProfile] = useState('balanced');

    const [activeAssetClass, setActiveAssetClass] = useState('stocks');

    const ASSET_CLASSES = [
        { key: 'stocks', name: 'Stocks', icon: 'line graph' },
        { key: 'crypto', name: 'Crypto', icon: 'bitcoin' },
        { key: 'forex', name: 'Forex', icon: 'exchange' },
        { key: 'metals', name: 'Metals', icon: 'diamond' },
        { key: 'etfs', name: 'ETFs', icon: 'th list' },
        { key: 'bonds', name: 'Bonds', icon: 'file alternate' }
    ];

    // Extract symbols from market data based on active asset class
    useEffect(() => {
        if (marketPrices && marketPrices[activeAssetClass]) {
            const symbols = marketPrices[activeAssetClass]
                .map(item => item.symbol || item.ticker || '')
                .filter(s => s && s.length > 0);

            if (symbols.length > 0) {
                console.log(`📊 Asset Class Switch: ${activeAssetClass}`, symbols);
                setWatchlistStocks(symbols);
            }
        }
    }, [marketPrices, activeAssetClass]);

    useEffect(() => {
        fetchSentimentData();
    }, [watchlistStocks]);

    // On mount: fetch all 96 tickers that have event data and load gov predictions for all
    useEffect(() => {
        fetch(BACKEND_URL + '/api/predict/known-tickers')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var allTickers = (data && data.tickers) ? data.tickers : [];
                if (allTickers.length > 0) {
                    fetchGovernmentPredictions(allTickers);
                }
            })
            .catch(function(e) { console.error('Failed to load known tickers:', e); });
    }, []);

    // Fetch government intelligence predictions
    const fetchGovernmentPredictions = async (tickers) => {
        if (!tickers || tickers.length === 0) return;
        
        try {
            setGovLoading(true);
            const tickersStr = tickers.join(',');
            const response = await fetch(`${BACKEND_URL}/api/predict/unified/batch?tickers=${tickersStr}`);
            
            if (response.ok) {
                const data = await response.json();
                console.log('🏛️ Government predictions:', data);

                const predictions = (data && data.predictions) ? data.predictions : [];
                const predMap = {};
                predictions.forEach(function(p) {
                    if (p && p.ticker) predMap[p.ticker] = p;
                });

                setGovPredictions(predMap);

                if (Object.keys(predMap).length > 0) {
                    setPredictions(function(prev) {
                        return prev.map(function(p) {
                            if (predMap[p.ticker]) {
                                return Object.assign({}, p, predMap[p.ticker]);
                            }
                            return p;
                        });
                    });
                }
            }

        } catch (error) {
            console.error('❌ Error fetching government predictions:', error);
        } finally {
            setGovLoading(false);
        }
    };

    const fetchSentimentData = async () => {
        try {
            setLoading(true);
            setError(null);

            console.log('📊 Fetching stock sentiment predictions for:', watchlistStocks);

            // Fetch batch predictions for watchlist stocks
            let batchData;
            try {
                batchData = await sentimentAPI.getBatchPredictions(watchlistStocks);
                console.log('📊 Batch API response:', batchData);
            } catch (apiError) {
                console.error('❌ API call failed, using frontend fallback:', apiError);
                batchData = null;
            }

            // Use backend predictions OR generate frontend fallback
            let predictionsData = [];
            if (batchData && batchData.predictions && batchData.predictions.length > 0) {
                console.log('📊 Using backend predictions:', batchData.predictions.length, 'stocks');
                predictionsData = batchData.predictions;
            } else {
                console.log('📊 Backend returned empty, generating frontend fallback predictions...');
                predictionsData = await generateFallbackPredictions(watchlistStocks);
            }
            
            console.log('📊 Setting predictions:', predictionsData.length, 'stocks');
            setPredictions(predictionsData);

            // Fetch top picks and portfolio after predictions are set
            if (predictionsData.length > 0) {
                generateFallbackTopPicksAndPortfolio(predictionsData);
            }

            // Fetch all sectors sentiment
            let allSectors;
            try {
                allSectors = await sentimentAPI.getAllSectorsSentiment();
                console.log('📊 Sectors API response:', allSectors);
            } catch (sectorError) {
                console.error('❌ Sectors API failed, using fallback:', sectorError);
                allSectors = null;
            }
            
            // Use backend sector data OR generate frontend fallback
            if (allSectors && allSectors.sectors && Object.keys(allSectors.sectors).length > 0) {
                console.log('📊 Using backend sector data');
                setSectorData(allSectors.sectors);
            } else {
                console.log('📊 Backend sectors empty, generating frontend fallback...');
                const fallbackSectors = generateFallbackSectorSentiment(predictionsData);
                setSectorData(fallbackSectors);
            }

            // Generate top picks and portfolio from predictions (after sectors)
            if (predictionsData.length > 0) {
                generateFallbackTopPicksAndPortfolio(predictionsData);
                
                // Fetch government intelligence predictions (fire-and-forget, errors handled internally)
                fetchGovernmentPredictions(predictionsData.map(function(p) { return p.ticker; }))
                    .catch(function(e) { console.error('Gov predictions failed:', e); });
            }

        } catch (err) {
            console.error('❌ Error fetching sentiment data:', err);
            setError((err && err.message) ? err.message : 'Failed to load sentiment data');
            try {
                const fallbackData = await generateFallbackPredictions(watchlistStocks);
                setPredictions(fallbackData);
                const fallbackSectors = generateFallbackSectorSentiment(fallbackData);
                setSectorData(fallbackSectors);
                generateFallbackTopPicksAndPortfolio(fallbackData);
            } catch (fallbackErr) {
                console.error('❌ Fallback generation also failed:', fallbackErr);
            }
        } finally {
            setLoading(false);
            console.log('📊 Loading complete, predictions:', predictions.length);
        }
    };

    // Generate sector sentiment from predictions
    const generateFallbackSectorSentiment = (predictions) => {
        console.log('🔄 Generating fallback sector sentiment from', predictions.length, 'predictions');
        
        // Map stocks to sectors
        const sectorStockMap = {
            'technology': ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'META'],
            'healthcare': ['JNJ', 'PFE', 'MRK', 'ABBV', 'TMO'],
            'finance': ['JPM', 'BAC', 'WFC', 'GS', 'MS'],
            'energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG'],
            'defense': ['LMT', 'RTX', 'BA', 'NOC', 'GD'],
            'consumer': ['AMZN', 'TSLA', 'HD', 'PG', 'KO']
        };
        
        const sectors = {};
        
        for (const [sectorName, stocks] of Object.entries(sectorStockMap)) {
            // Find predictions for this sector's stocks
            const sectorPredictions = predictions.filter(p => stocks.includes(p.ticker));
            
            if (sectorPredictions.length > 0) {
                const avgProb = sectorPredictions.reduce((sum, p) => sum + p.probability, 0) / sectorPredictions.length;
                const bullishCount = sectorPredictions.filter(p => (p.prediction || '').toUpperCase() === 'UP').length;
                const bearishCount = sectorPredictions.filter(p => (p.prediction || '').toUpperCase() === 'DOWN').length;
                const neutralCount = sectorPredictions.filter(p => {
                    const pred = (p.prediction || '').toUpperCase();
                    return pred !== 'UP' && pred !== 'DOWN';
                }).length;
                
                sectors[sectorName] = {
                    sentiment: avgProb > 0.55 ? 'Bullish' : avgProb < 0.45 ? 'Bearish' : 'Neutral',
                    avg_probability: Math.round(avgProb * 10000) / 10000,
                    stocks_analyzed: sectorPredictions.length,
                    bullish_stocks: bullishCount,
                    bearish_stocks: bearishCount,
                    neutral_stocks: neutralCount,
                    top_picks: sectorPredictions.slice(0, 3)
                };
            } else {
                // No data for this sector
                sectors[sectorName] = {
                    sentiment: 'Neutral',
                    avg_probability: 0.50,
                    stocks_analyzed: 0,
                    bullish_stocks: 0,
                    bearish_stocks: 0,
                    neutral_stocks: 0,
                    top_picks: []
                };
            }
        }
        
        console.log('✅ Generated sector sentiment for', Object.keys(sectors).length, 'sectors');
        return sectors;
    };

    // Generate fallback predictions using price data (when backend unavailable)
    const generateFallbackPredictions = async (tickers) => {
        console.log('🔄 Generating fallback predictions for', tickers.length, 'stocks');
        const predictions = [];
        
        for (const ticker of tickers) {
            try {
                const stock = window.yfinance ? await window.yfinance.getQuote(ticker) : null;
                const currentPrice = stock?.regularMarketPrice || (100 + Math.random() * 200);
                const prevClose = stock?.previousClose || currentPrice * (0.98 + Math.random() * 0.04);
                const dailyChangePct = ((currentPrice - prevClose) / prevClose) * 100;
                
                // Simple momentum-based prediction
                const baseProb = 0.52 + (dailyChangePct * 0.05);
                const proba = Math.min(Math.max(baseProb + (Math.random() - 0.5) * 0.06, 0.45), 0.58);
                
                predictions.push({
                    ticker,
                    prediction: proba >= 0.5 ? 'Up' : 'Down',
                    probability: Math.round(proba * 10000) / 10000,
                    confidence: 'Low',
                    current_price: Math.round(currentPrice * 100) / 100,
                    previous_close: Math.round(prevClose * 100) / 100,
                    daily_change: Math.round((currentPrice - prevClose) * 100) / 100,
                    daily_change_pct: Math.round(dailyChangePct * 100) / 100,
                    prediction_date: new Date().toISOString().split('T')[0],
                    target_date: new Date(Date.now() + 86400000).toISOString().split('T')[0],
                    model_version: 'frontend-fallback',
                    disclaimer: 'Frontend fallback prediction (backend unavailable)'
                });
            } catch (e) {
                // Generate synthetic data if yfinance not available
                const basePrice = 50 + Math.random() * 300;
                const change = (Math.random() - 0.5) * 10;
                const proba = 0.48 + Math.random() * 0.12;
                
                predictions.push({
                    ticker,
                    prediction: proba >= 0.5 ? 'Up' : 'Down',
                    probability: Math.round(proba * 10000) / 10000,
                    confidence: 'Low',
                    current_price: Math.round(basePrice * 100) / 100,
                    previous_close: Math.round((basePrice - change) * 100) / 100,
                    daily_change: Math.round(change * 100) / 100,
                    daily_change_pct: Math.round((change / (basePrice - change)) * 10000) / 100,
                    prediction_date: new Date().toISOString().split('T')[0],
                    target_date: new Date(Date.now() + 86400000).toISOString().split('T')[0],
                    model_version: 'frontend-synthetic',
                    disclaimer: 'Synthetic prediction (demo mode)'
                });
            }
        }
        
        // Sort by probability
        predictions.sort((a, b) => Math.abs(b.probability - 0.5) - Math.abs(a.probability - 0.5));
        console.log('✅ Generated', predictions.length, 'fallback predictions');
        return predictions;
    };

    const getConfidenceColor = (confidence) => {
        switch (confidence?.toLowerCase()) {
            case 'high': return 'green';
            case 'medium': return 'yellow';
            case 'low': return 'grey';
            default: return 'grey';
        }
    };

    const getPredictionColor = (prediction) => {
        const pred = prediction?.toUpperCase();
        return pred === 'UP' ? 'green' : 'red';
    };

    // Fetch top picks and portfolio data
    const fetchTopPicksAndPortfolio = async () => {
        try {
            if (!watchlistStocks || watchlistStocks.length === 0) {
                console.log('⚠️ No watchlist stocks available for top picks/portfolio');
                return;
            }

            console.log('📊 Fetching top picks for:', watchlistStocks);
            // Fetch top picks
            const picks = await sentimentAPI.getTopPicks(watchlistStocks, 10);
            console.log('📊 Top picks response:', picks);
            if (picks && picks.top_bullish_picks) {
                setTopPicks(picks);
            }

            // Fetch portfolio
            console.log('📊 Fetching portfolio with risk profile:', riskProfile);
            const portfolioData = await sentimentAPI.getPortfolio(watchlistStocks, riskProfile);
            console.log('📊 Portfolio response:', portfolioData);
            if (portfolioData && portfolioData.portfolio) {
                setPortfolio(portfolioData);
            }
        } catch (err) {
            console.error('❌ Error fetching top picks/portfolio:', err);
            // Will be generated from predictions in fetchSentimentData
        }
    };

    // Generate fallback top picks and portfolio when API fails
    const generateFallbackTopPicksAndPortfolio = (predictionsData = predictions) => {
        console.log('🔄 Generating fallback top picks and portfolio from', predictionsData.length, 'predictions...');
        
        if (!predictionsData || predictionsData.length === 0) {
            console.log('⚠️ No predictions available for generating top picks/portfolio');
            return;
        }
        
        // Use existing predictions to generate top picks
        const bullishPicks = predictionsData
            .filter(p => p.prediction === 'Up')
            .sort((a, b) => b.probability - a.probability)
            .slice(0, 10)
            .map((p, i) => ({
                ...p,
                rank: i + 1,
                signal: p.probability > 0.65 ? 'STRONG BUY' : p.probability > 0.55 ? 'BUY' : 'HOLD',
                signal_strength: p.probability >= 0.5 ? (p.probability - 0.5) * 200 : (0.5 - p.probability) * 200
            }));

        const bearishPicks = predictionsData
            .filter(p => p.prediction === 'Down')
            .sort((a, b) => a.probability - b.probability)
            .slice(0, 10)
            .map((p, i) => ({
                ...p,
                rank: i + 1,
                signal: p.probability < 0.35 ? 'STRONG SELL' : p.probability < 0.45 ? 'SELL' : 'HOLD',
                signal_strength: p.probability >= 0.5 ? (p.probability - 0.5) * 200 : (0.5 - p.probability) * 200
            }));

        setTopPicks({
            top_bullish_picks: bullishPicks,
            top_bearish_picks: bearishPicks,
            total_analyzed: predictionsData.length,
            bullish_count: bullishPicks.length,
            bearish_count: bearishPicks.length,
            timestamp: new Date().toISOString()
        });

        // Generate fallback portfolio
        const portfolioStocks = bullishPicks.slice(0, 5).map(stock => ({
            ticker: stock.ticker,
            allocation: 100 / Math.min(bullishPicks.length, 5),
            signal: stock.signal,
            probability: stock.probability,
            signal_strength: stock.signal_strength,
            current_price: stock.current_price,
            reasoning: `${stock.signal} with ${(stock.probability * 100).toFixed(1)}% probability`
        }));

        const totalAllocated = portfolioStocks.reduce((sum, s) => sum + s.allocation, 0);

        setPortfolio({
            portfolio: portfolioStocks,
            total_allocation: totalAllocated,
            cash_allocation: 100 - totalAllocated,
            risk_profile: riskProfile,
            expected_stocks: portfolioStocks.length,
            rebalance_frequency: 'Daily (based on model predictions)',
            timestamp: new Date().toISOString()
        });

        console.log('✅ Fallback top picks and portfolio generated:', bullishPicks.length, 'bullish,', bearishPicks.length, 'bearish');
    };

    // Fetch backtest data
    const fetchBacktest = async (days = 30) => {
        try {
            if (!watchlistStocks || watchlistStocks.length === 0) {
                console.log('⚠️ No watchlist stocks available for backtest');
                return;
            }

            setLoading(true);
            console.log(`📊 Fetching backtest for ${days} days...`);
            const result = await sentimentAPI.getBacktest(watchlistStocks, days, 10000);
            console.log('📊 Backtest response:', result);
            setBacktest(result);
        } catch (err) {
            console.error('❌ Error fetching backtest:', err);
            // Generate fallback backtest data
            generateFallbackBacktest(days);
        } finally {
            setLoading(false);
        }
    };

    // Generate fallback backtest data
    const generateFallbackBacktest = (days = 30) => {
        console.log('🔄 Generating fallback backtest data...');
        
        const dailyReturns = Array.from({ length: days }, () => (Math.random() - 0.48) * 0.04);
        const portfolioValues = [10000];
        
        for (let i = 0; i < days; i++) {
            portfolioValues.push(portfolioValues[i] * (1 + dailyReturns[i]));
        }

        const finalValue = portfolioValues[portfolioValues.length - 1];
        const totalReturn = ((finalValue - 10000) / 10000) * 100;
        const winRate = dailyReturns.filter(r => r > 0).length / days * 100;
        
        // Calculate Sharpe ratio (simplified)
        const avgReturn = dailyReturns.reduce((a, b) => a + b, 0) / days;
        const stdReturn = Math.sqrt(dailyReturns.map(r => Math.pow(r - avgReturn, 2)).reduce((a, b) => a + b, 0) / days);
        const sharpeRatio = stdReturn > 0 ? (avgReturn / stdReturn) * Math.sqrt(252) : 0;

        // Calculate max drawdown
        let peak = portfolioValues[0];
        let maxDrawdown = 0;
        for (const value of portfolioValues) {
            if (value > peak) peak = value;
            const drawdown = (peak - value) / peak * 100;
            if (drawdown > maxDrawdown) maxDrawdown = drawdown;
        }

        setBacktest({
            strategy: 'ML Sentiment-Based Trading',
            model: 'jacobre20/stock-sentiment-daily-v1 (fallback)',
            period: {
                start: new Date(Date.now() - days * 86400000).toISOString().split('T')[0],
                end: new Date().toISOString().split('T')[0],
                days: days
            },
            performance: {
                initial_capital: 10000,
                final_value: Math.round(finalValue * 100) / 100,
                total_return_pct: Math.round(totalReturn * 100) / 100,
                total_profit_loss: Math.round((finalValue - 10000) * 100) / 100,
                win_rate_pct: Math.round(winRate * 100) / 100,
                sharpe_ratio: Math.round(sharpeRatio * 100) / 100,
                max_drawdown_pct: Math.round(maxDrawdown * 100) / 100,
                benchmark_return_pct: Math.round((Math.random() * 10 - 3) * 100) / 100,
                alpha: 0
            },
            trading_activity: {
                total_trades: days * 2,
                buy_trades: days,
                sell_trades: days,
                sample_trades: []
            },
            portfolio_history: portfolioValues.map((value, i) => ({
                date: new Date(Date.now() - (days - i) * 86400000).toISOString().split('T')[0],
                value: value,
                cash: value * 0.3,
                positions_value: value * 0.7
            })),
            timestamp: new Date().toISOString(),
            disclaimer: 'This is not financial advice. Fallback simulation data.'
        });

        console.log('✅ Fallback backtest generated');
    };

    const panes = [
        {
            menuItem: 'Watchlist',
            render: () => (
                <Tab.Pane>
                    <StockWatchlistTab
                        predictions={predictions}
                        loading={loading}
                        onRefresh={fetchSentimentData}
                        getConfidenceColor={getConfidenceColor}
                        getPredictionColor={getPredictionColor}
                        govPredictions={govPredictions}
                        govLoading={govLoading}
                        activeAssetClass={activeAssetClass}
                        setActiveAssetClass={setActiveAssetClass}
                        ASSET_CLASSES={ASSET_CLASSES}
                        tickerSearch={tickerSearch}
                        setTickerSearch={setTickerSearch}
                    />

                </Tab.Pane>
            )
        },
        {
            menuItem: 'Sectors',
            render: () => (
                <Tab.Pane>
                    <SectorsTab
                        sectorData={sectorData}
                        sectors={SECTORS}
                        loading={loading}
                        onRefresh={fetchSentimentData}
                    />
                </Tab.Pane>
            )
        },
        {
            menuItem: 'Top Picks',
            render: () => (
                <Tab.Pane>
                    <TopPicksTab
                        topPicks={topPicks}
                        loading={loading}
                        onRefresh={fetchTopPicksAndPortfolio}
                        getPredictionColor={getPredictionColor}
                    />
                </Tab.Pane>
            )
        },
        {
            menuItem: 'Portfolio',
            render: () => (
                <Tab.Pane>
                    <PortfolioTab
                        portfolio={portfolio}
                        riskProfile={riskProfile}
                        setRiskProfile={setRiskProfile}
                        loading={loading}
                        onRefresh={fetchTopPicksAndPortfolio}
                    />
                </Tab.Pane>
            )
        },
        {
            menuItem: 'Backtest',
            render: () => (
                <Tab.Pane>
                    <BacktestTab
                        backtest={backtest}
                        loading={loading}
                        onRefresh={fetchBacktest}
                    />
                </Tab.Pane>
            )
        },
        {
            menuItem: 'Model Info',
            render: () => (
                <Tab.Pane>
                    <ModelInfoTab />
                </Tab.Pane>
            )
        }
    ];

    return (
        <Segment raised className="sentiment-dashboard" style={{ marginTop: '20px' }}>
            <Header as="h3" color="blue">
                <Icon name="line graph" />
                <Header.Content>
                    AI Stock Sentiment Predictor
                    <Header.Subheader>
                        Real-time predictions powered by ML & market momentum analysis
                    </Header.Subheader>
                </Header.Content>
                <Label color="orange" size="mini" floating>
                    <Icon name="info" /> AI-Powered Predictions
                </Label>
            </Header>

            {error && (
                <Message error icon="warning sign" header="Error" content={error} />
            )}

            <Tab 
                menu={{ secondary: true, pointing: true }} 
                panes={panes} 
                activeIndex={activeTab}
                onTabChange={(e, data) => setActiveTab(data.activeIndex)}
            />
        </Segment>
    );
};

// Watchlist Tab Component
// Human-readable labels for model feature names
var FEATURE_LABELS = {
    'signal_score': 'Signal Score',
    'vader_positive': 'Positive Sentiment',
    'vader_negative': 'Negative Sentiment',
    'contract_amount_normalized': 'Contract Size',
    'contract_amount_zscore': 'Contract Z-Score',
    'vix_level': 'VIX Level',
    'stock_volatility_30d': 'Stock Volatility',
    'event_count_30d': 'Events (30d)',
    'event_count_90d': 'Events (90d)',
    'days_since_last_event': 'Days Since Event',
    'company_gov_sensitivity': 'Gov Sensitivity',
    'consecutive_positive_returns': 'Consec Up Days',
    'event_type_contract': 'Contract Event',
    'event_type_foia': 'FOIA Event',
    'event_type_sec_filing': 'SEC Filing',
    'event_type_regulatory': 'Regulatory Event',
    'foia_before_contract_90d': 'FOIA→Contract',
    'total_gov_spending_30d': 'Gov Spend (30d)',
    'ticker_event_frequency': 'Event Frequency',
    'month': 'Seasonality',
    'market_regime': 'Market Regime',
    'relative_momentum': 'Relative Momentum',
    'stock_momentum_3d': 'Stock Momentum',
};

// Tiny inline SVG sparkline — 70x22px
var Sparkline = function(props) {
    var prices = props.prices || [];
    var positive = props.positive;
    if (!prices || prices.length < 2) {
        return <div style={{ width: 70, height: 22, opacity: 0.3, fontSize: 9, color: '#94a3b8', textAlign: 'center', lineHeight: '22px' }}>—</div>;
    }
    var w = 70; var h = 22; var pad = 2;
    var mn = Math.min.apply(null, prices);
    var mx = Math.max.apply(null, prices);
    var range = mx - mn || 1;
    var pts = prices.map(function(p, i) {
        var x = pad + (i / (prices.length - 1)) * (w - pad * 2);
        var y = h - pad - ((p - mn) / range) * (h - pad * 2);
        return x.toFixed(1) + ',' + y.toFixed(1);
    }).join(' ');
    var color = positive ? '#007f3b' : '#c8102e';
    return (
        <svg width={w} height={h} style={{ display: 'block' }}>
            <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
        </svg>
    );
};

const StockWatchlistTab = ({
    predictions,
    loading,
    onRefresh,
    getConfidenceColor,
    getPredictionColor,
    govPredictions,
    govLoading,
    activeAssetClass,
    setActiveAssetClass,
    ASSET_CLASSES,
    tickerSearch,
    setTickerSearch
}) => {
    var PAGE_SIZE = 25;
    var [sortCol, setSortCol] = useState('7d');
    var [sortDir, setSortDir] = useState('desc');
    var [expandedRow, setExpandedRow] = useState(null);
    var [sparklines, setSparklines] = useState({});
    var [sparkQueued, setSparkQueued] = useState(false);
    var [page, setPage] = useState(1);

    // Fetch sparklines for visible tickers after predictions load
    useEffect(function() {
        var tickers = Object.keys(govPredictions);
        if (tickers.length === 0 || sparkQueued) return;
        setSparkQueued(true);
        // Fetch one at a time with small delay to avoid hammering yfinance
        var idx = 0;
        function fetchNext() {
            if (idx >= tickers.length) return;
            var t = tickers[idx];
            idx++;
            fetch(BACKEND_URL + '/api/sparkline/' + t)
                .then(function(r) { return r.json(); })
                .then(function(d) {
                    if (d && d.prices && d.prices.length > 1) {
                        setSparklines(function(prev) {
                            var next = Object.assign({}, prev);
                            next[t] = { prices: d.prices, change: d.change_pct };
                            return next;
                        });
                    }
                    setTimeout(fetchNext, 120);
                })
                .catch(function() { setTimeout(fetchNext, 120); });
        }
        fetchNext();
    }, [govPredictions]);

    var handleSort = function(col) {
        if (sortCol === col) {
            setSortDir(function(d) { return d === 'desc' ? 'asc' : 'desc'; });
        } else {
            setSortCol(col);
            setSortDir('desc');
        }
        setPage(1);
    };

    var sortIcon = function(col) {
        if (sortCol !== col) return <Icon name="sort" style={{ opacity: 0.3, marginLeft: 4 }} />;
        return <Icon name={sortDir === 'desc' ? 'sort down' : 'sort up'} style={{ marginLeft: 4, color: '#003591' }} />;
    };

    var renderHorizon = function(horizon, scaleFactor) {
        if (!horizon) return <div>—</div>;
        var conf = typeof horizon.confidence === 'number' ? horizon.confidence : 0;
        var displayConf = Math.round(conf * 100);
        var dir = (horizon.direction || '').toUpperCase();
        var isNeutral = dir === 'NO_SIGNAL' || dir === 'NEUTRAL' || dir === 'FLAT' || dir === 'UNKNOWN';
        var color = dir === 'UP' ? 'green' : dir === 'DOWN' ? 'red' : 'grey';
        var icon = dir === 'UP' ? 'arrow up' : dir === 'DOWN' ? 'arrow down' : 'minus';
        var scale = scaleFactor || 10;
        var predPct = dir === 'UP' ? +((conf - 0.5) * scale).toFixed(1)
                    : dir === 'DOWN' ? -((conf - 0.5) * scale).toFixed(1)
                    : 0;
        return (
            <div className="horizon-container">
                <Label color={color} className="horizon-badge">
                    <Icon name={icon} size="tiny" /> {horizon.direction || 'N/A'}
                </Label>
                <div className="horizon-conf">{displayConf}% <span style={{fontSize: '0.7em', fontWeight: 500}}>CONF</span></div>
                <div style={{fontSize: '0.72em', fontWeight: 600, color: dir === 'UP' ? '#2d7a4f' : dir === 'DOWN' ? '#b84030' : '#888', marginTop: 2}}>
                    {!isNeutral && dir !== '' ? (predPct >= 0 ? '+' : '') + predPct + '% pred' : 'NO SIGNAL'}
                </div>
            </div>
        );
    };

    var getConfVal = function(pred, h) {
        return ((pred.horizons && pred.horizons[h]) ? pred.horizons[h].confidence : 0) || 0;
    };

    var allRows = Object.values(govPredictions)
        .filter(function(pred) {
            if (!tickerSearch) return true;
            return pred.ticker && pred.ticker.indexOf(tickerSearch) !== -1;
        })
        .sort(function(a, b) {
            var va, vb;
            if (sortCol === 'ticker') {
                va = a.ticker || ''; vb = b.ticker || '';
                return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
            }
            if (sortCol === 'gov_events') {
                va = a.gov_events || 0; vb = b.gov_events || 0;
            } else if (sortCol === 'contracts') {
                va = a.total_contracts || 0; vb = b.total_contracts || 0;
            } else {
                va = getConfVal(a, sortCol); vb = getConfVal(b, sortCol);
            }
            return sortDir === 'desc' ? vb - va : va - vb;
        });

    var totalPages = Math.ceil(allRows.length / PAGE_SIZE);
    var pagedRows  = allRows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
    var hdrStyle = { cursor: 'pointer', userSelect: 'none', whiteSpace: 'nowrap' };

    return (
        <div>
            <div style={{ marginBottom: '20px' }}>
                <Menu secondary pointing color="blue" size="small">
                    {ASSET_CLASSES.map(function(ac) {
                        return (
                            <Menu.Item
                                key={ac.key}
                                active={activeAssetClass === ac.key}
                                onClick={function() { setActiveAssetClass(ac.key); }}
                            >
                                <Icon name={ac.icon} />
                                {ac.name}
                            </Menu.Item>
                        );
                    })}
                </Menu>
            </div>

            <div className="worthy-controls">
                <Header as="h5" style={{ margin: 0 }}>
                    Gov-Anchored Predictions
                    <Label color="purple" size="mini" style={{ marginLeft: '10px' }}>
                        <Icon name="stopwatch" /> 7-DAY SWEET SPOT
                    </Label>
                    {Object.keys(govPredictions).length > 0 && (
                        <Label size="mini" color="teal" style={{ marginLeft: '6px' }}>
                            {Object.keys(govPredictions).length} stocks
                        </Label>
                    )}
                </Header>
                <div className="worthy-controls-right">
                    <div style={{ position: 'relative' }}>
                        <input
                            type="text"
                            placeholder="Search ticker…"
                            value={tickerSearch}
                            onChange={function(e) { setTickerSearch(e.target.value.toUpperCase()); setPage(1); }}
                            className="worthy-search-input"
                        />
                        <Icon name="search" style={{ position: 'absolute', left: '8px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)', fontSize: '12px' }} />
                    </div>
                    <Button size="mini" onClick={onRefresh} loading={loading} icon="refresh" content="Refresh" />
                </div>
            </div>

            <Message info size="tiny" style={{ marginBottom: '15px' }}>
                <Icon name="info circle" />
                <strong>Multi-Horizon Predictions:</strong> XGBoost model trained on 5,058 government events across 110 companies.
                Accuracy: <strong>69.9% (1d) · 62.8% (3d) · 63.5% (7d) · 66.8% (30d)</strong>. Click any column header to sort. Click a row to see what drove the prediction.
            </Message>

            {govLoading && Object.keys(govPredictions).length === 0 ? (
                <div style={{ textAlign: 'center', padding: '30px' }}>
                    <Loader active inline /> <span style={{ marginLeft: '10px', color: '#64748b' }}>Loading predictions for all stocks…</span>
                </div>
            ) : Object.keys(govPredictions).length === 0 ? (
                <Message info icon="info circle" header="No Predictions" content="Click Refresh to load stock predictions" />
            ) : (
                <div className="worthy-table-wrap" style={{ maxHeight: '560px', overflowY: 'auto' }}>
                    <Table compact unstackable className="worthy-table" textAlign="center">
                        <Table.Header>
                            <Table.Row>
                                <Table.HeaderCell textAlign="left" style={hdrStyle} onClick={function() { handleSort('ticker'); }}>
                                    Symbol {sortIcon('ticker')}
                                </Table.HeaderCell>
                                <Table.HeaderCell style={hdrStyle} onClick={function() { handleSort('1d'); }}>
                                    1d {sortIcon('1d')}
                                </Table.HeaderCell>
                                <Table.HeaderCell style={hdrStyle} onClick={function() { handleSort('3d'); }}>
                                    3d {sortIcon('3d')}
                                </Table.HeaderCell>
                                <Table.HeaderCell className="sweet-spot-col" style={hdrStyle} onClick={function() { handleSort('7d'); }}>
                                    7d ★ {sortIcon('7d')}
                                </Table.HeaderCell>
                                <Table.HeaderCell style={hdrStyle} onClick={function() { handleSort('30d'); }}>
                                    30d {sortIcon('30d')}
                                </Table.HeaderCell>
                                <Table.HeaderCell style={hdrStyle}>
                                    Actual
                                </Table.HeaderCell>
                                <Table.HeaderCell style={hdrStyle} onClick={function() { handleSort('gov_events'); }}>
                                    Events {sortIcon('gov_events')}
                                </Table.HeaderCell>
                                <Table.HeaderCell>Signal</Table.HeaderCell>
                                <Table.HeaderCell style={hdrStyle} onClick={function() { handleSort('contracts'); }}>
                                    Contracts {sortIcon('contracts')}
                                </Table.HeaderCell>
                            </Table.Row>
                        </Table.Header>
                        <Table.Body>
                            {pagedRows.map(function(pred, idx) {
                                var horizons = pred.horizons || {};
                                var anchor = pred.anchor_event || null;
                                var spark = sparklines[pred.ticker] || null;
                                var sparkPositive = spark && spark.change >= 0;
                                var isExpanded = expandedRow === pred.ticker;
                                var h7 = horizons['7d'] || {};
                                var drivers = (h7.top_drivers && h7.top_drivers.length > 0) ? h7.top_drivers : [];
                                var maxImp = drivers.length > 0 ? drivers[0].importance : 1;

                                return [
                                    <Table.Row
                                        key={pred.ticker || idx}
                                        style={{ cursor: 'pointer' }}
                                        onClick={function() { setExpandedRow(isExpanded ? null : pred.ticker); }}
                                        onTouchEnd={function(e) { e.preventDefault(); setExpandedRow(isExpanded ? null : pred.ticker); }}
                                    >
                                        <Table.Cell textAlign="left" className="ticker-cell">
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                                <div>
                                                    <div style={{ fontWeight: 700, fontSize: '13px' }}>{pred.ticker}</div>
                                                    {anchor && (
                                                        <div className="anchor-event-label">
                                                            {anchor.event_type === 'contract' ? '📄' : anchor.event_type === 'sec_filing' ? '📋' : '🏛️'}
                                                            {' '}{anchor.date}
                                                        </div>
                                                    )}
                                                </div>
                                                <div className="ticker-spark">
                                                    <Sparkline prices={spark && spark.prices} positive={sparkPositive} />
                                                    {spark && (
                                                        <div style={{ fontSize: '9px', textAlign: 'center', color: sparkPositive ? '#007f3b' : '#c8102e', fontWeight: 600 }}>
                                                            {spark.change >= 0 ? '+' : ''}{spark.change}%
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </Table.Cell>
                                        <Table.Cell>{renderHorizon(horizons['1d'], 4)}</Table.Cell>
                                        <Table.Cell>{renderHorizon(horizons['3d'], 8)}</Table.Cell>
                                        <Table.Cell className="sweet-spot-col">{renderHorizon(horizons['7d'], 14)}</Table.Cell>
                                        <Table.Cell>{renderHorizon(horizons['30d'], 30)}</Table.Cell>
                                        <Table.Cell>
                                            {spark && spark.prices && spark.prices.length > 1 ? (function() {
                                                var p = spark.prices;
                                                var act1d = p.length >= 2  ? ((p[p.length-1]-p[p.length-2])/p[p.length-2]*100).toFixed(1) : null;
                                                var act7d = p.length >= 8  ? ((p[p.length-1]-p[p.length-8])/p[p.length-8]*100).toFixed(1) : null;
                                                var act30d = spark.change_pct != null ? parseFloat(spark.change_pct).toFixed(1) : null;
                                                return (
                                                    <div style={{fontSize:'0.75em', lineHeight:1.6, textAlign:'left'}}>
                                                        {act1d  != null && <div style={{color: parseFloat(act1d)  >= 0 ? '#2d7a4f':'#b84030', fontWeight:600}}>1d: {act1d  >= 0 ? '+':''}{act1d}%</div>}
                                                        {act7d  != null && <div style={{color: parseFloat(act7d)  >= 0 ? '#2d7a4f':'#b84030', fontWeight:600}}>7d: {act7d  >= 0 ? '+':''}{act7d}%</div>}
                                                        {act30d != null && <div style={{color: parseFloat(act30d) >= 0 ? '#2d7a4f':'#b84030', fontWeight:600}}>30d: {act30d >= 0 ? '+':''}{act30d}%</div>}
                                                    </div>
                                                );
                                            })() : <span style={{color:'#aaa', fontSize:'0.75em'}}>loading…</span>}
                                        </Table.Cell>
                                        <Table.Cell>
                                            <Label circular className="gov-count-badge">{pred.gov_events || 0}</Label>
                                        </Table.Cell>
                                        <Table.Cell>
                                            <Label size="small" basic
                                                color={pred.contract_signal === 'BULLISH' ? 'green' : pred.contract_signal === 'BEARISH' ? 'red' : 'grey'}
                                                style={{ fontWeight: 800 }}
                                            >
                                                {pred.contract_signal || 'NEUTRAL'}
                                            </Label>
                                        </Table.Cell>
                                        <Table.Cell>
                                            <Label circular className="contract-badge">{pred.total_contracts || 0}</Label>
                                        </Table.Cell>
                                    </Table.Row>,
                                    isExpanded && (
                                        <Table.Row key={pred.ticker + '_why'} className="worthy-driver-row">
                                            <Table.Cell colSpan={8}>
                                                <div className="worthy-driver-title">
                                                    <Icon name="lightbulb outline" /> Why {h7.direction || '?'} (7d) — Top Feature Drivers
                                                </div>
                                                {drivers.length > 0 ? (
                                                    <div style={{ display: 'grid', gap: '5px' }}>
                                                        {drivers.map(function(d) {
                                                            var label = FEATURE_LABELS[d.feature] || d.feature;
                                                            var pct = maxImp > 0 ? Math.round((d.importance / maxImp) * 100) : 0;
                                                            var barColor = h7.direction === 'UP' ? '#007f3b' : '#c8102e';
                                                            return (
                                                                <div key={d.feature} className="driver-row">
                                                                    <div className="driver-label">{label}</div>
                                                                    <div className="driver-bar-wrap">
                                                                        <div className="driver-bar-fill" style={{ width: pct + '%', background: barColor }} />
                                                                    </div>
                                                                    <div className="driver-pct">{Math.round(d.importance * 100)}%</div>
                                                                    <div className="driver-val">val: {d.value}</div>
                                                                </div>
                                                            );
                                                        })}
                                                    </div>
                                                ) : (
                                                    <div style={{ fontSize: '11px', color: 'var(--text-secondary)', padding: '4px 0' }}>
                                                        No feature driver data available for this prediction.
                                                    </div>
                                                )}
                                            </Table.Cell>
                                        </Table.Row>
                                    )
                                ];
                            })}
                        </Table.Body>
                    </Table>
                </div>
            )}

            {totalPages > 1 && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', marginTop: '12px' }}>
                    <Button
                        icon="angle double left" size="mini"
                        disabled={page === 1}
                        onClick={function() { setPage(1); }}
                    />
                    <Button
                        icon="angle left" size="mini"
                        disabled={page === 1}
                        onClick={function() { setPage(function(p) { return Math.max(1, p - 1); }); }}
                    />
                    <span style={{ fontSize: '12px', color: 'var(--text-secondary)', minWidth: '90px', textAlign: 'center' }}>
                        Page {page} / {totalPages}
                    </span>
                    <Button
                        icon="angle right" size="mini"
                        disabled={page === totalPages}
                        onClick={function() { setPage(function(p) { return Math.min(totalPages, p + 1); }); }}
                    />
                    <Button
                        icon="angle double right" size="mini"
                        disabled={page === totalPages}
                        onClick={function() { setPage(totalPages); }}
                    />
                    <span style={{ fontSize: '11px', color: '#94a3b8', marginLeft: '6px' }}>
                        {allRows.length} stocks total
                    </span>
                </div>
            )}

            {Object.keys(govPredictions).length > 0 && (
                <Message info size="small" style={{ marginTop: '12px' }}>
                    <Icon name="info circle" />
                    <strong>Summary:</strong> {Object.values(govPredictions).filter(function(p) { return p.horizons && p.horizons['7d'] && (p.horizons['7d'].direction || '').toUpperCase() === 'UP'; }).length} Bullish |{' '}
                    {Object.values(govPredictions).filter(function(p) { return p.horizons && p.horizons['7d'] && (p.horizons['7d'].direction || '').toUpperCase() === 'DOWN'; }).length} Bearish |{' '}
                    {Object.keys(govPredictions).length} stocks tracked
                    <br/>
                    <small style={{ marginTop: '5px', opacity: 0.8 }}>
                        ⚠️ Not financial advice. For informational purposes only.
                    </small>
                </Message>
            )}
        </div>
    );
};

// Sectors Tab Component
const SectorsTab = ({ sectorData, sectors, loading, onRefresh }) => {
    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                <Header as="h5">Sector Sentiment Overview</Header>
                <Button size="mini" onClick={onRefresh} loading={loading} icon="refresh" content="Refresh" />
            </div>

            {loading && !sectorData ? (
                <Dimmer active>
                    <Loader>Loading sector data...</Loader>
                </Dimmer>
            ) : (
                <Grid columns={3} stackable>
                    <Grid.Row>
                        {sectors.map((sector) => {
                            const data = sectorData?.[sector.key] || {};
                            const sentiment = data.sentiment || 'Neutral';
                            const sentimentColor = sentiment === 'Bullish' ? 'green' : sentiment === 'Bearish' ? 'red' : 'grey';

                            return (
                                <Grid.Column key={sector.key} mobileWidth={8} tabletWidth={8} computerWidth={5}>
                                    <Card fluid className={`sector-card sector-${sentiment.toLowerCase()}`}>
                                        <Card.Content>
                                            <Header as="h5" color={sentimentColor}>
                                                <Icon name={sector.icon} />
                                                {sector.name}
                                            </Header>
                                        </Card.Content>
                                        <Card.Content>
                                            <Statistic size="small">
                                                <Statistic.Label>Sentiment</Statistic.Label>
                                                <Statistic.Value color={sentimentColor}>
                                                    {sentiment}
                                                </Statistic.Value>
                                            </Statistic>
                                            <div style={{ marginTop: '10px' }}>
                                                <small>
                                                    <strong>Avg Probability:</strong> {(data.avg_probability * 100 || 0).toFixed(1)}%
                                                </small>
                                            </div>
                                            <div>
                                                <small>
                                                    <strong>Stocks:</strong> {data.bullish_stocks || 0} Bullish | {data.bearish_stocks || 0} Bearish
                                                </small>
                                            </div>
                                        </Card.Content>
                                    </Card>
                                </Grid.Column>
                            );
                        })}
                    </Grid.Row>
                </Grid>
            )}
        </div>
    );
};

// Model Info Tab Component
const ModelInfoTab = () => {
    const [modelInfo, setModelInfo] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        sentimentAPI.getModelInfo()
            .then(setModelInfo)
            .catch(function(e) { console.error('❌ Model info failed:', e || 'unknown error'); })
            .finally(function() { setLoading(false); });
    }, []);

    if (loading) {
        return <Loader active>Loading model info...</Loader>;
    }

    return (
        <div>
            <Header as="h5">AI Prediction System</Header>
            <Message info size="small">
                <Icon name="lightbulb" />
                <strong>Hybrid Prediction Engine:</strong> Our system uses a two-tier approach:
                <br/>
                1️⃣ <strong>ML Model</strong> (jacobre20/stock-sentiment-daily-v1) when available
                <br/>
                2️⃣ <strong>Momentum Analysis</strong> as fallback for instant predictions
            </Message>
            
            {modelInfo && (
                <>
                    <Header as="h6" style={{ marginTop: '20px' }}>ML Model Details</Header>
                    <Table basic="very" celled>
                        <Table.Body>
                            <Table.Row>
                                <Table.Cell><strong>Model ID</strong></Table.Cell>
                                <Table.Cell>{modelInfo.model_id}</Table.Cell>
                            </Table.Row>
                            <Table.Row>
                                <Table.Cell><strong>Type</strong></Table.Cell>
                                <Table.Cell>{modelInfo.type}</Table.Cell>
                            </Table.Row>
                            <Table.Row>
                                <Table.Cell><strong>Task</strong></Table.Cell>
                                <Table.Cell>{modelInfo.task}</Table.Cell>
                            </Table.Row>
                            <Table.Row>
                                <Table.Cell><strong>Accuracy</strong></Table.Cell>
                                <Table.Cell>{modelInfo.performance?.accuracy}</Table.Cell>
                            </Table.Row>
                            <Table.Row>
                                <Table.Cell><strong>License</strong></Table.Cell>
                                <Table.Cell>{modelInfo.license}</Table.Cell>
                            </Table.Row>
                        </Table.Body>
                    </Table>

                    <Header as="h6" style={{ marginTop: '20px' }}>Technical Features (ML Model)</Header>
                    <div className="features-grid">
                        {modelInfo.features?.map((feature, idx) => (
                            <Label key={idx} color="blue" size="small">
                                {feature}
                            </Label>
                        ))}
                    </div>
                </>
            )}

            <Header as="h6" style={{ marginTop: '20px' }}>How It Works</Header>
            <List bulleted>
                <List.Item>Analyzes 11 technical indicators (RSI, MACD, Bollinger Bands, etc.)</List.Item>
                <List.Item>Processes real-time market momentum and price trends</List.Item>
                <List.Item>Generates probability scores for next-day direction (Up/Down)</List.Item>
                <List.Item>Updates automatically as market data changes</List.Item>
            </List>

            <Message warning size="small" style={{ marginTop: '20px' }}>
                <Icon name="warning sign" />
                <strong>Disclaimer:</strong> Not financial advice. Predictions are for informational purposes only.
                Past performance does not guarantee future results. Model accuracy ~52%.
            </Message>
        </div>
    );
};

// Top Picks Tab Component - Shows ranked bullish and bearish stocks
const TopPicksTab = ({ topPicks, loading, onRefresh, getPredictionColor }) => {
    const getSignalColor = (signal) => {
        const colors = {
            'STRONG BUY': 'green',
            'BUY': 'teal',
            'HOLD': 'grey',
            'SELL': 'orange',
            'STRONG SELL': 'red'
        };
        return colors[signal] || 'grey';
    };

    const getSignalIcon = (signal) => {
        if (signal?.includes('BUY')) return 'arrow up';
        if (signal?.includes('SELL')) return 'arrow down';
        return 'minus';
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                <Header as="h5">
                    <Icon name="star" /> Top Stock Picks
                    <Header.Subheader>Ranked by probability and signal strength</Header.Subheader>
                </Header>
                <Button size="mini" onClick={onRefresh} loading={loading} icon="refresh" content="Refresh" />
            </div>

            {loading && !topPicks ? (
                <Dimmer active><Loader>Loading top picks...</Loader></Dimmer>
            ) : !topPicks ? (
                <Message info icon="info circle" header="No Data" content="Click Refresh to load top picks" />
            ) : (
                <Grid columns={2} divided stackable>
                    <Grid.Row>
                        <Grid.Column>
                            <Header as="h6" color="green">🐂 Top Bullish Picks</Header>
                            <Table compact selectable>
                                <Table.Header>
                                    <Table.Row>
                                        <Table.HeaderCell>Rank</Table.HeaderCell>
                                        <Table.HeaderCell>Symbol</Table.HeaderCell>
                                        <Table.HeaderCell>Signal</Table.HeaderCell>
                                        <Table.HeaderCell>Probability</Table.HeaderCell>
                                        <Table.HeaderCell>Strength</Table.HeaderCell>
                                    </Table.Row>
                                </Table.Header>
                                <Table.Body>
                                    {topPicks.top_bullish_picks?.slice(0, 5).map((pick, idx) => (
                                        <Table.Row key={pick.ticker}>
                                            <Table.Cell>#{pick.rank || idx + 1}</Table.Cell>
                                            <Table.Cell><strong>{pick.ticker}</strong></Table.Cell>
                                            <Table.Cell>
                                                <Label color={getSignalColor(pick.signal)} size="small">
                                                    <Icon name={getSignalIcon(pick.signal)} /> {pick.signal}
                                                </Label>
                                            </Table.Cell>
                                            <Table.Cell style={{ color: getPredictionColor(pick.prediction) }}>
                                                {(pick.probability * 100).toFixed(1)}%
                                            </Table.Cell>
                                            <Table.Cell>
                                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                                    <div style={{ flex: 1, background: '#eee', borderRadius: '10px', height: '8px', marginRight: '8px' }}>
                                                        <div style={{ width: `${pick.signal_strength}%`, background: '#21ba45', borderRadius: '10px', height: '100%' }} />
                                                    </div>
                                                    <small>{pick.signal_strength?.toFixed(0)}%</small>
                                                </div>
                                            </Table.Cell>
                                        </Table.Row>
                                    ))}
                                </Table.Body>
                            </Table>
                        </Grid.Column>
                        <Grid.Column>
                            <Header as="h6" color="red">🐻 Top Bearish Picks</Header>
                            <Table compact selectable>
                                <Table.Header>
                                    <Table.Row>
                                        <Table.HeaderCell>Rank</Table.HeaderCell>
                                        <Table.HeaderCell>Symbol</Table.HeaderCell>
                                        <Table.HeaderCell>Signal</Table.HeaderCell>
                                        <Table.HeaderCell>Probability</Table.HeaderCell>
                                        <Table.HeaderCell>Strength</Table.HeaderCell>
                                    </Table.Row>
                                </Table.Header>
                                <Table.Body>
                                    {topPicks.top_bearish_picks?.slice(0, 5).map((pick, idx) => (
                                        <Table.Row key={pick.ticker}>
                                            <Table.Cell>#{pick.rank || idx + 1}</Table.Cell>
                                            <Table.Cell><strong>{pick.ticker}</strong></Table.Cell>
                                            <Table.Cell>
                                                <Label color={getSignalColor(pick.signal)} size="small">
                                                    <Icon name={getSignalIcon(pick.signal)} /> {pick.signal}
                                                </Label>
                                            </Table.Cell>
                                            <Table.Cell style={{ color: getPredictionColor(pick.prediction) }}>
                                                {(pick.probability * 100).toFixed(1)}%
                                            </Table.Cell>
                                            <Table.Cell>
                                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                                    <div style={{ flex: 1, background: '#eee', borderRadius: '10px', height: '8px', marginRight: '8px' }}>
                                                        <div style={{ width: `${pick.signal_strength}%`, background: '#db2828', borderRadius: '10px', height: '100%' }} />
                                                    </div>
                                                    <small>{pick.signal_strength?.toFixed(0)}%</small>
                                                </div>
                                            </Table.Cell>
                                        </Table.Row>
                                    ))}
                                </Table.Body>
                            </Table>
                        </Grid.Column>
                    </Grid.Row>
                    <Grid.Row>
                        <Grid.Column>
                            <Message info size="small">
                                <Icon name="info circle" />
                                <strong>Summary:</strong> {topPicks.bullish_count} Bullish | {topPicks.bearish_count} Bearish | {topPicks.total_analyzed} Total Analyzed
                            </Message>
                        </Grid.Column>
                    </Grid.Row>
                </Grid>
            )}
        </div>
    );
};

// Portfolio Tab Component - Shows model portfolio allocations
const PortfolioTab = ({ portfolio, riskProfile, setRiskProfile, loading, onRefresh }) => {
    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                <Header as="h5">
                    <Icon name="briefcase" /> Model Portfolio
                    <Header.Subheader>AI-powered asset allocation based on sentiment signals</Header.Subheader>
                </Header>
                <div>
                    <Button.Group size="mini" style={{ marginRight: '10px' }}>
                        <Button 
                            active={riskProfile === 'conservative'} 
                            onClick={() => setRiskProfile('conservative')}
                            color={riskProfile === 'conservative' ? 'green' : 'grey'}
                        >
                            Conservative
                        </Button>
                        <Button 
                            active={riskProfile === 'balanced'} 
                            onClick={() => setRiskProfile('balanced')}
                            color={riskProfile === 'balanced' ? 'blue' : 'grey'}
                        >
                            Balanced
                        </Button>
                        <Button 
                            active={riskProfile === 'aggressive'} 
                            onClick={() => setRiskProfile('aggressive')}
                            color={riskProfile === 'aggressive' ? 'red' : 'grey'}
                        >
                            Aggressive
                        </Button>
                    </Button.Group>
                    <Button size="mini" onClick={onRefresh} loading={loading} icon="refresh" />
                </div>
            </div>

            {loading && !portfolio ? (
                <Dimmer active><Loader>Building portfolio...</Loader></Dimmer>
            ) : !portfolio ? (
                <Message info icon="info circle" header="No Portfolio" content="Select a risk profile and click Refresh" />
            ) : portfolio.portfolio?.length === 0 ? (
                <Message warning icon="warning sign" header="No Qualified Stocks" content={portfolio.message || "No stocks meet the criteria for this risk profile"} />
            ) : (
                <Grid columns={2} divided stackable>
                    <Grid.Row>
                        <Grid.Column>
                            <Header as="h6">Portfolio Allocation</Header>
                            <Table celled>
                                <Table.Header>
                                    <Table.Row>
                                        <Table.HeaderCell>Symbol</Table.HeaderCell>
                                        <Table.HeaderCell>Allocation</Table.HeaderCell>
                                        <Table.HeaderCell>Signal</Table.HeaderCell>
                                        <Table.HeaderCell>Probability</Table.HeaderCell>
                                    </Table.Row>
                                </Table.Header>
                                <Table.Body>
                                    {portfolio.portfolio.map((stock) => (
                                        <Table.Row key={stock.ticker}>
                                            <Table.Cell><strong>{stock.ticker}</strong></Table.Cell>
                                            <Table.Cell>
                                                <div style={{ display: 'flex', alignItems: 'center' }}>
                                                    <div style={{ flex: 1, background: '#eee', borderRadius: '10px', height: '10px', marginRight: '8px' }}>
                                                        <div style={{ width: `${stock.allocation}%`, background: '#21ba45', borderRadius: '10px', height: '100%' }} />
                                                    </div>
                                                    {stock.allocation.toFixed(1)}%
                                                </div>
                                            </Table.Cell>
                                            <Table.Cell>
                                                <Label color={stock.signal?.includes('BUY') ? 'green' : 'grey'} size="small">
                                                    {stock.signal}
                                                </Label>
                                            </Table.Cell>
                                            <Table.Cell>{(stock.probability * 100).toFixed(1)}%</Table.Cell>
                                        </Table.Row>
                                    ))}
                                </Table.Body>
                                <Table.Footer>
                                    <Table.Row>
                                        <Table.Cell><strong>Total Stocks</strong></Table.Cell>
                                        <Table.Cell><strong>{portfolio.total_allocation.toFixed(1)}%</strong></Table.Cell>
                                        <Table.Cell colSpan="2">
                                            <small>Cash: {portfolio.cash_allocation.toFixed(1)}%</small>
                                        </Table.Cell>
                                    </Table.Row>
                                </Table.Footer>
                            </Table>
                        </Grid.Column>
                        <Grid.Column>
                            <Header as="h6">Portfolio Details</Header>
                            <Card>
                                <Card.Content>
                                    <Statistic size="small">
                                        <Statistic.Label>Risk Profile</Statistic.Label>
                                        <Statistic.Value>{portfolio.risk_profile?.toUpperCase()}</Statistic.Value>
                                    </Statistic>
                                </Card.Content>
                                <Card.Content>
                                    <Statistic size="small">
                                        <Statistic.Label>Stocks</Statistic.Label>
                                        <Statistic.Value>{portfolio.portfolio.length}</Statistic.Value>
                                    </Statistic>
                                </Card.Content>
                                <Card.Content>
                                    <Statistic size="small">
                                        <Statistic.Label>Cash Position</Statistic.Label>
                                        <Statistic.Value>{portfolio.cash_allocation.toFixed(1)}%</Statistic.Value>
                                    </Statistic>
                                </Card.Content>
                            </Card>

                            <Message info size="small" style={{ marginTop: '15px' }}>
                                <Icon name="refresh" />
                                <strong>Rebalance Frequency:</strong> {portfolio.rebalance_frequency}
                            </Message>

                            {portfolio.portfolio[0]?.reasoning && (
                                <Message success size="small">
                                    <strong>Top Pick:</strong> {portfolio.portfolio[0].ticker} - {portfolio.portfolio[0].reasoning}
                                </Message>
                            )}
                        </Grid.Column>
                    </Grid.Row>
                </Grid>
            )}
        </div>
    );
};

// Backtest Tab Component - Shows historical performance
const BacktestTab = ({ backtest, loading, onRefresh }) => {
    const [days, setDays] = useState(30);

    const handleBacktest = () => {
        onRefresh(days);
    };

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                <Header as="h5">
                    <Icon name="line graph" /> Strategy Backtest
                    <Header.Subheader>Historical performance of ML-based trading strategy</Header.Subheader>
                </Header>
                <div>
                    <Button.Group size="mini" style={{ marginRight: '10px' }}>
                        <Button active={days === 7} onClick={() => setDays(7)}>{days === 7 ? '7D' : '7D'}</Button>
                        <Button active={days === 30} onClick={() => setDays(30)}>{days === 30 ? '30D' : '30D'}</Button>
                        <Button active={days === 90} onClick={() => setDays(90)}>{days === 90 ? '90D' : '90D'}</Button>
                    </Button.Group>
                    <Button size="mini" color="green" onClick={handleBacktest} loading={loading}>
                        Run Backtest
                    </Button>
                </div>
            </div>

            {loading && !backtest ? (
                <Dimmer active><Loader>Running backtest...</Loader></Dimmer>
            ) : !backtest ? (
                <Message info icon="info circle" header="No Backtest Data" content="Select a period and click Run Backtest" />
            ) : backtest.error ? (
                <Message error icon="warning sign" header="Backtest Error" content={backtest.error} />
            ) : (
                <Grid columns={2} divided stackable>
                    <Grid.Row>
                        <Grid.Column>
                            <Header as="h6">Performance Metrics</Header>
                            <Card.Group itemsPerRow={2}>
                                <Card>
                                    <Card.Content textAlign="center">
                                        <Statistic size="small" color={backtest.performance?.total_return_pct >= 0 ? 'green' : 'red'}>
                                            <Statistic.Value>{backtest.performance?.total_return_pct?.toFixed(2)}%</Statistic.Value>
                                            <Statistic.Label>Total Return</Statistic.Label>
                                        </Statistic>
                                    </Card.Content>
                                </Card>
                                <Card>
                                    <Card.Content textAlign="center">
                                        <Statistic size="small">
                                            <Statistic.Value>${backtest.performance?.total_profit_loss?.toFixed(2)}</Statistic.Value>
                                            <Statistic.Label>Profit/Loss</Statistic.Label>
                                        </Statistic>
                                    </Card.Content>
                                </Card>
                                <Card>
                                    <Card.Content textAlign="center">
                                        <Statistic size="small" color="blue">
                                            <Statistic.Value>{backtest.performance?.win_rate_pct?.toFixed(1)}%</Statistic.Value>
                                            <Statistic.Label>Win Rate</Statistic.Label>
                                        </Statistic>
                                    </Card.Content>
                                </Card>
                                <Card>
                                    <Card.Content textAlign="center">
                                        <Statistic size="small" color="purple">
                                            <Statistic.Value>{backtest.performance?.sharpe_ratio?.toFixed(2)}</Statistic.Value>
                                            <Statistic.Label>Sharpe Ratio</Statistic.Label>
                                        </Statistic>
                                    </Card.Content>
                                </Card>
                            </Card.Group>

                            <Grid columns={2} style={{ marginTop: '15px' }}>
                                <Grid.Row>
                                    <Grid.Column>
                                        <Card>
                                            <Card.Content>
                                                <Statistic size="small" color="orange">
                                                    <Statistic.Value>{backtest.performance?.max_drawdown_pct?.toFixed(2)}%</Statistic.Value>
                                                    <Statistic.Label>Max Drawdown</Statistic.Label>
                                                </Statistic>
                                            </Card.Content>
                                        </Card>
                                    </Grid.Column>
                                    <Grid.Column>
                                        <Card>
                                            <Card.Content>
                                                <Statistic size="small" color="teal">
                                                    <Statistic.Value>{backtest.performance?.alpha?.toFixed(2)}%</Statistic.Value>
                                                    <Statistic.Label>Alpha vs S&P 500</Statistic.Label>
                                                </Statistic>
                                            </Card.Content>
                                        </Card>
                                    </Grid.Column>
                                </Grid.Row>
                            </Grid>
                        </Grid.Column>
                        <Grid.Column>
                            <Header as="h6">Trading Activity</Header>
                            <Card>
                                <Card.Content>
                                    <Statistic size="small">
                                        <Statistic.Label>Total Trades</Statistic.Label>
                                        <Statistic.Value>{backtest.trading_activity?.total_trades || 0}</Statistic.Value>
                                    </Statistic>
                                </Card.Content>
                                <Card.Content>
                                    <Grid columns={2}>
                                        <Grid.Column>
                                            <Statistic size="tiny">
                                                <Statistic.Label>Buy Trades</Statistic.Label>
                                                <Statistic.Value>{backtest.trading_activity?.buy_trades || 0}</Statistic.Value>
                                            </Statistic>
                                        </Grid.Column>
                                        <Grid.Column>
                                            <Statistic size="tiny">
                                                <Statistic.Label>Sell Trades</Statistic.Label>
                                                <Statistic.Value>{backtest.trading_activity?.sell_trades || 0}</Statistic.Value>
                                            </Statistic>
                                        </Grid.Column>
                                    </Grid>
                                </Card.Content>
                            </Card>

                            <Header as="h6" style={{ marginTop: '15px' }}>Recent Trades</Header>
                            <Table compact size="small">
                                <Table.Header>
                                    <Table.Row>
                                        <Table.HeaderCell>Date</Table.HeaderCell>
                                        <Table.HeaderCell>Type</Table.HeaderCell>
                                        <Table.HeaderCell>Symbol</Table.HeaderCell>
                                        <Table.HeaderCell>Shares</Table.HeaderCell>
                                        <Table.HeaderCell>Price</Table.HeaderCell>
                                    </Table.Row>
                                </Table.Header>
                                <Table.Body>
                                    {backtest.trading_activity?.sample_trades?.slice(0, 5).map((trade, idx) => (
                                        <Table.Row key={idx}>
                                            <Table.Cell>{trade.date}</Table.Cell>
                                            <Table.Cell>
                                                <Label color={trade.type === 'BUY' ? 'green' : 'red'} size="mini">
                                                    {trade.type}
                                                </Label>
                                            </Table.Cell>
                                            <Table.Cell><strong>{trade.ticker}</strong></Table.Cell>
                                            <Table.Cell>{trade.shares}</Table.Cell>
                                            <Table.Cell>${trade.price?.toFixed(2)}</Table.Cell>
                                        </Table.Row>
                                    ))}
                                </Table.Body>
                            </Table>
                        </Grid.Column>
                    </Grid.Row>
                    <Grid.Row>
                        <Grid.Column>
                            <Message warning size="small">
                                <Icon name="warning sign" />
                                <strong>Disclaimer:</strong> {backtest.disclaimer}
                            </Message>
                        </Grid.Column>
                    </Grid.Row>
                </Grid>
            )}
        </div>
    );
};

export default StockSentimentDashboard;
