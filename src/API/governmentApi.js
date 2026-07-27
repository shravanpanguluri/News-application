import axios from 'axios';

// Backend API URL - Use environment variable, check localhost, or default to Render
const getBackendUrl = () => {
	if (process.env.REACT_APP_BACKEND_URL) return process.env.REACT_APP_BACKEND_URL;
	
	const hostname = window.location.hostname;
	const nativeCapacitor = window.Capacitor && typeof window.Capacitor.isNativePlatform === 'function' && window.Capacitor.isNativePlatform();
	if (nativeCapacitor) {
		// A phone's localhost is the phone itself, not the development Mac.
		return 'https://govpulse-application.onrender.com';
	}
	if (hostname === 'localhost' || hostname === '127.0.0.1') {
		// Local FastAPI backend
		return 'http://127.0.0.1:8000';
	}
	
	return 'https://govpulse-application.onrender.com';
};

export const BACKEND_URL = getBackendUrl();

// Create axios instance for government API
const governmentAPI = axios.create({
	baseURL: `${BACKEND_URL}`,
	timeout: 120000, // 120 seconds (RSS feeds take time)
	headers: {
		'Content-Type': 'application/json',
		'Accept': 'application/json'
	}
});

// Request interceptor - add auth token
governmentAPI.interceptors.request.use(
	function(config) {
		const token = localStorage.getItem('token');
		if (token) {
			config.headers.Authorization = 'Bearer ' + token;
		}
		return config;
	},
	function(err) {
		// Always reject with a real Error so browsers can display it
		var e = (err instanceof Error) ? err : new Error(String(err || 'Request setup failed'));
		return Promise.reject(e);
	}
);

// Response interceptor - handle errors
governmentAPI.interceptors.response.use(
	function(response) {
		return response.data || response;
	},
	function(error) {
		if (error && error.response) {
			if (error.response.status === 426) {
				console.warn('426 Error - Retrying connection...');
			}
			if (error.response.status === 401 && error.config && !error.config.url.includes('/auth/')) {
				localStorage.removeItem('token');
			}
			if (error.response.status === 429) {
				console.warn('Daily limit exceeded.');
			}
		}

		if (error && !error.response) {
			console.error('Network error - Backend may be unavailable:', error.message || error);
		}

		// Always reject with a real Error so browsers can display rejection reason
		var e = (error instanceof Error) ? error : new Error(
			(error && error.message) ? error.message : 'Network request failed'
		);
		return Promise.reject(e);
	}
);

// Auth API calls
export const authAPI = {
	register: async (email, password, tier = 'free') => {
		try {
			const response = await governmentAPI.post('/auth/register', {
				email,
				password,
				tier,
			});
			return response;
		} catch (error) {
			throw error;
		}
	},

	login: async (email, password) => {
		try {
			const response = await governmentAPI.post('/auth/login', {
				email,
				password,
			});
			if (response.access_token) {
				localStorage.setItem('token', response.access_token);
				localStorage.setItem('tier', response.tier);
				localStorage.setItem('dailyLimit', response.daily_limit);
			}
			return { success: true, ...response };
		} catch (error) {
			return {
				success: false,
				error:
					error.response && error.response.data
						? error.response.data.detail || 'Login failed'
						: 'Login failed',
			};
		}
	},

	logout: () => {
		localStorage.removeItem('token');
		localStorage.removeItem('tier');
		localStorage.removeItem('dailyLimit');
	},

	getCurrentUser: async () => {
		const response = await governmentAPI.get('/user/me');
		return response;
	},

	getWatchlist: async () => {
		const response = await governmentAPI.get('/user/watchlist');
		return response;
	},

	addToWatchlist: async keyword => {
		const response = await governmentAPI.post(`/user/watchlist?keyword=${keyword}`);
		return response;
	},

	removeFromWatchlist: async keyword => {
		const response = await governmentAPI.delete(`/user/watchlist/${keyword}`);
		return response;
	},

	getWatchlistNews: async () => {
		const response = await governmentAPI.get('/user/watchlist/news');
		return response;
	},
};

// Articles API calls
export const articlesAPI = {
	getAll: async (country = 'all', limit = 25) => {
		const response = await governmentAPI.get('/articles', {
			params: { country, limit },
		});
		return response;
	},

	getByCategory: async (category, limit = 20) => {
		const response = await governmentAPI.get(`/articles/category/${category}`, {
			params: { limit },
		});
		return response;
	},

	search: async (query, limit = 20) => {
		const response = await governmentAPI.get('/search', {
			params: { q: query, limit },
		});
		return response;
	},
};

// Subscription API calls
export const subscriptionAPI = {
	getPlans: async () => {
		const response = await governmentAPI.get('/subscription/plans');
		return response;
	},
};

// RSS Feed API calls
export const rssAPI = {
	getAll: async (category = 'all', limit = 100, country = 'all') => {
		// Retry logic for Render free tier (backend may be sleeping)
		for (let attempt = 0; attempt < 3; attempt++) {
			try {
				const response = await governmentAPI.get('/rss/all', {
					params: { category, limit, country },
					timeout: 60000, // 60 seconds for RSS
				});
				if (attempt > 0) console.log(`✅ RSS request succeeded on attempt ${attempt + 1}`);
				return response;
			} catch (error) {
				if (attempt < 2) {
					console.log(`⏳ RSS request failed (attempt ${attempt + 1}), retrying in 2s...`);
					await new Promise(resolve => setTimeout(resolve, 2000));
				} else {
					console.error('❌ RSS request failed after 3 attempts:', error.message);
					throw error;
				}
			}
		}
	},

	getBreaking: async (limit = 20) => {
		const response = await governmentAPI.get('/rss/breaking', {
			params: { limit },
		});
		return response;
	},

	getTrending: async () => {
		const response = await governmentAPI.get('/rss/trending');
		return response;
	},

	getTrendingNews: async (limit = 20) => {
		const response = await governmentAPI.get('/rss/trending-news', {
			params: { limit },
		});
		return response;
	},

	getByCategory: async (category, limit = 50, country = 'all') => {
		const response = await governmentAPI.get(`/rss/category/${category}`, {
			params: { limit, country },
		});
		return response;
	},

	getMarketPrices: async () => {
		const response = await governmentAPI.get('/markets/prices');
		return response;
	},
};

// Stock Sentiment API calls
export const sentimentAPI = {
	getPrediction: async (ticker) => {
		console.log('📡 Calling sentiment API for:', ticker, 'URL:', `${BACKEND_URL}/markets/sentiment/predict/${ticker}`);
		const response = await governmentAPI.get(`/markets/sentiment/predict/${ticker}`);
		console.log('📡 Response:', response);
		return response;
	},

	getBatchPredictions: async (tickers) => {
		const url = `/markets/sentiment/batch?tickers=${tickers.join(',')}`;
		console.log('📡 Calling batch API:', tickers, 'Full URL:', `${BACKEND_URL}${url}`);
		const response = await governmentAPI.get(url);
		console.log('📡 Batch response:', response);
		return response;
	},

	getSectorSentiment: async (sector) => {
		const response = await governmentAPI.get(`/markets/sentiment/sector/${sector}`);
		return response;
	},

	getAllSectorsSentiment: async () => {
		const response = await governmentAPI.get('/markets/sentiment/all-sectors');
		return response;
	},

	getModelInfo: async () => {
		const response = await governmentAPI.get('/markets/sentiment/model-info');
		return response;
	},

	// Enhanced endpoints - Trading Signals & Portfolio
	getTopPicks: async (tickers, limit = 10) => {
		const url = `/markets/sentiment/top-picks?tickers=${tickers.join(',')}&limit=${limit}`;
		const response = await governmentAPI.get(url);
		return response;
	},

	getPortfolio: async (tickers, riskProfile = 'balanced') => {
		const url = `/markets/sentiment/portfolio?tickers=${tickers.join(',')}&risk_profile=${riskProfile}`;
		const response = await governmentAPI.get(url);
		return response;
	},

	getBacktest: async (tickers, days = 30, initialCapital = 10000) => {
		const url = `/markets/sentiment/backtest?tickers=${tickers.join(',')}&days=${days}&initial_capital=${initialCapital}`;
		const response = await governmentAPI.get(url);
		return response;
	},

	getTradingSignal: async (ticker) => {
		const response = await governmentAPI.get(`/markets/sentiment/signals/${ticker}`);
		return response;
	},
};

// Patent-Critical API calls (FOIA, USAspending, Correlation, Prediction)
export const patentAPI = {
	// India-Specific Intelligence (Differentiator)
	getIndiaNotifications: async (limit = 10) => {
		return await governmentAPI.get('/api/india/notifications', { params: { limit } });
	},

	getIndiaRBIActions: async (limit = 5) => {
		return await governmentAPI.get('/api/india/rbi-actions', { params: { limit } });
	},

	// FOIA Engine
	getRecentFOIA: async (agency = null, limit = 50) => {
		const params = { limit };
		if (agency) params.agency = agency;
		return await governmentAPI.get('/api/foia/recent', { params });
	},

	getFOIAByCompany: async (companyName, limit = 50) => {
		return await governmentAPI.get(`/api/foia/company/${companyName}`, { params: { limit } });
	},

	getFOIADocsForTicker: async (ticker, companyName = null) => {
		const params = companyName ? { company_name: companyName } : {};
		return await governmentAPI.get(`/api/foia/ticker/${ticker}`, { params });
	},

	getFOIASignals: async (ticker, companyName = null) => {
		const params = companyName ? { company_name: companyName } : {};
		return await governmentAPI.get(`/api/foia/signals/${ticker}`, { params });
	},

	// USAspending Integration
	getContracts: async (ticker, companyName = null, limit = 50) => {
		const params = { limit };
		if (companyName) params.company_name = companyName;
		return await governmentAPI.get(`/api/usaspending/contracts/${ticker}`, { params });
	},

	getContractTrends: async (ticker, companyName = null) => {
		const params = companyName ? { company_name: companyName } : {};
		return await governmentAPI.get(`/api/usaspending/trends/${ticker}`, { params });
	},

	getAgencySpending: async (companyName, limit = 50) => {
		return await governmentAPI.get(`/api/usaspending/agencies/${companyName}`, { params: { limit } });
	},

	getTopContractors: async (limit = 50) => {
		return await governmentAPI.get('/api/usaspending/top-contractors', { params: { limit } });
	},

	// Correlation Tracking
	trackEvent: async (ticker, eventType, eventDescription, companyName = null) => {
		const params = { ticker, event_type: eventType, event_description: eventDescription };
		if (companyName) params.company_name = companyName;
		return await governmentAPI.post('/api/correlation/track', null, { params });
	},

	getCorrelationData: async (ticker) => {
		return await governmentAPI.get(`/api/correlation/${ticker}`);
	},

	getAccuracyStats: async () => {
		return await governmentAPI.get('/api/correlation/accuracy/stats');
	},

	exportEvidence: async () => {
		return await governmentAPI.get('/api/correlation/export/evidence');
	},

	// Prediction & Backtesting
	predictImpact: async (ticker, eventType, signalScore = 50, amount = 0) => {
		return await governmentAPI.get(`/api/prediction/impact/${ticker}`, {
			params: { event_type: eventType, signal_score: signalScore, amount }
		});
	},

	runBacktest: async (ticker = null, holdDays = 7) => {
		const params = { hold_days: holdDays };
		if (ticker) params.ticker = ticker;
		return await governmentAPI.post('/api/backtest/run', null, { params });
	},

	getBacktestEvidence: async () => {
		return await governmentAPI.get('/api/backtest/evidence');
	}
};

export default governmentAPI;
