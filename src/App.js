import React, { useState, useEffect, useRef, Suspense } from 'react';
import './App.css';
// // import API from './API/api'; // DISABLED - NewsAPI CORS  // DISABLED - NewsAPI CORS issues on free plan
import { articlesAPI, authAPI, rssAPI } from './API/governmentApi';
import { transformArticles } from './utils/contentRewriter';
// Eagerly loaded — required on initial render
import NewsCards from './components/NewsCards/NewsCards';
import MarketTicker from './components/MarketTicker/MarketTicker';
import BreakingNewsTicker from './components/BreakingNewsTicker/BreakingNewsTicker';
import ArticleReader from './components/ArticleReader/ArticleReader';
import TrendingTopics from './components/TrendingTopics/TrendingTopics';
import CategoryFilter from './components/CategoryFilter/CategoryFilter';
import AdComponent from './components/AdComponent/AdComponent';
import LoginModal from './components/LoginModal/LoginModal';
import RemoveAdsModal from './components/RemoveAdsModal/RemoveAdsModal';
import PullToRefresh from './components/PullToRefresh/PullToRefresh';
import {
	Container,
	Grid,
	Menu,
	Button,
	Icon,
	Tab,
	Label,
	Statistic,
	Segment,
	Header,
	Dropdown,
	Input,
	Form,
	Card,
	Accordion,
	Message,
} from 'semantic-ui-react';
import { useSemanticSearch } from './hooks/useSemanticSearch';

// Lazy loaded — deferred until tab is first visited
var GovernmentNewsCard = React.lazy(function() { return import('./components/GovernmentNewsCard/GovernmentNewsCard'); });
var SubscriptionPlans = React.lazy(function() { return import('./components/SubscriptionPlans/SubscriptionPlans'); });
var BreakingNewsPage = React.lazy(function() { return import('./components/BreakingNewsPage/BreakingNewsPage'); });
var NLPAnalysis = React.lazy(function() { return import('./components/NLPAnalysis/NLPAnalysis'); });
var TrendingNewsPage = React.lazy(function() { return import('./components/TrendingNewsPage/TrendingNewsPage'); });
var PolicyImpactDashboard = React.lazy(function() { return import('./components/PolicyImpactDashboard/PolicyImpactDashboard'); });
var GovShorts = React.lazy(function() { return import('./components/GovShorts/GovShorts'); });
var EconomicCalendar = React.lazy(function() { return import('./components/EconomicCalendar/EconomicCalendar'); });
var StockSentimentDashboard = React.lazy(function() { return import('./components/StockSentimentDashboard/StockSentimentDashboard'); });
var DeepAnalysisDashboard = React.lazy(function() { return import('./components/DeepAnalysisDashboard'); });
var PatentEvidenceDashboard = React.lazy(function() { return import('./components/PatentEvidenceDashboard'); });
var DefenseContracts = React.lazy(function() { return import('./components/DefenseContracts/DefenseContracts'); });
var TrendingPredictions = React.lazy(function() { return import('./components/TrendingPredictions/TrendingPredictions'); });
var EarningsCalendarWidget = React.lazy(function() { return import('./components/EarningsCalendarWidget/EarningsCalendarWidget'); });
var InsiderTrading = React.lazy(function() { return import('./components/InsiderTrading/InsiderTrading'); });
var SentimentTimeline = React.lazy(function() { return import('./components/SentimentTimeline/SentimentTimeline'); });
var PortfolioTracker = React.lazy(function() { return import('./components/PortfolioTracker/PortfolioTracker'); });
var PriceAlerts = React.lazy(function() { return import('./components/PriceAlerts/PriceAlerts'); });
var GeopoliticalRisk = React.lazy(function() { return import('./components/GeopoliticalRisk/GeopoliticalRisk'); });
var WatchlistHeatmap = React.lazy(function() { return import('./components/WatchlistHeatmap/WatchlistHeatmap'); });
var EventExplainer = React.lazy(function() { return import('./components/EventExplainer/EventExplainer'); });
var SearchComponent = React.lazy(function() { return import('./components/Search/SearchComponent'); });
var ImpactTrends = React.lazy(function() { return import('./components/ImpactTrends/ImpactTrends'); });
var MarketToolsWidget = React.lazy(function() { return import('./components/MarketToolsWidget/MarketToolsWidget'); });
var PrivacyPolicy = React.lazy(function() { return import('./components/LegalScreens/PrivacyPolicy'); });

class TabErrorBoundary extends React.Component {
	constructor(props) { super(props); this.state = { hasError: false }; }
	static getDerivedStateFromError() { return { hasError: true }; }
	render() {
		if (this.state.hasError) {
			return <div style={{ padding: '20px', color: '#888', textAlign: 'center' }}>Unable to load this section.</div>;
		}
		return this.props.children;
	}
}

// Category metadata for heatmap tiles
const CATEGORY_META = {
  general:    { emoji: '🌍', accent: '#3949ab', label: 'General'    },
  markets:    { emoji: '📈', accent: '#00897b', label: 'Markets'    },
  economy:    { emoji: '💹', accent: '#e65100', label: 'Economy'    },
  technology: { emoji: '💻', accent: '#6a1b9a', label: 'Technology' },
  policy:     { emoji: '🏛️', accent: '#1565c0', label: 'Policy'     },
  health:     { emoji: '🏥', accent: '#b71c1c', label: 'Health'     },
  finance:    { emoji: '💰', accent: '#00695c', label: 'Finance'    },
};

function App() {
	let sources = [];
	const [data, setData] = useState({
		isArticleVisible: false,
		articles: [],
		value: '',
		result: [],
		currentCategory: 'all',
		governmentArticles: [],
		isLoadingGov: false,
		activeTab: 0,
		isLoggedIn: false,
		userTier: 'free',
		dailyLimit: 50,
		requestsToday: 0,
		showSubscription: false,
		showLoginModal: false,
		showRemoveAdsModal: false,
		isLoading: false,
		breakingNews: [],
		trendingTopics: [],
		trendingNews: [],
		hasPremium: false,
		interstitialCount: 0,
		breakingNewsLastUpdated: new Date(),
		selectedArticleForReading: null,
		articleReaderOpen: false,
		articlesReadThisSession: 0,
		showInterstitial: false,
		mobileMenuOpen: false,
		bookmarks: (function() { try { return JSON.parse(localStorage.getItem('predovex_bookmarks') || '[]'); } catch(e) { return []; } })(),
		watchlistKeywords: [],
		watchlistNews: [],
		newWatchlistKeyword: '',
		marketPrices: { crypto: [], stocks: [], forex: [], metals: [], bonds: [], mutual_funds: [], etfs: [], cash: [], real_estate: [] },
		marketAccordionIndex: -1,
		isDarkMode: localStorage.getItem('darkMode') === 'true',
		disclaimerDismissed: localStorage.getItem('predovex_disclaimer') === 'true',
		showPrivacyPolicy: false,
		newsLoadError: false,
		// New: Filtered articles and sorting
		filteredArticles: [],
		activeFilter: null,  // 'high-impact', 'positive', 'negative', or category name
		sortBy: 'relevance',  // 'relevance', 'date', 'impact'
		sortOrder: 'desc',     // 'asc' or 'desc'
		// AI Features
		enableClustering: false,  // Group similar articles
		enableDeduplication: false,  // Remove duplicates
		clusteredArticles: [],  // Articles after clustering
		aiFeaturesLoaded: false,  // Track if AI features initialized
		// Personalized Recommendations
		personalizedArticles: [],  // "For You" recommendations
		readingHistory: [],  // Track read articles
		// Topic Modeling
		topicModelLoaded: false,
		// Sentiment Trends
		sentimentTrends: {}
	});

	// Initialize Semantic Search
	const { 
		query: semanticQuery, 
		setQuery: setSemanticQuery, 
		results: semanticResults, 
		isLoading: isSemanticLoading,
		isModelLoaded 
	} = useSemanticSearch(data.articles);

	const loadMarketPrices = async () => {
		try {
			const res = await rssAPI.getMarketPrices();
			if (res) setData(prev => ({ ...prev, marketPrices: res }));
		} catch (e) {
			console.error('Error loading market prices:', e);
		}
	};

	const handleAccordionClick = (e, titleProps) => {
		const { index } = titleProps;
		const newIndex = data.marketAccordionIndex === index ? -1 : index;
		setData(prev => ({ ...prev, marketAccordionIndex: newIndex }));
	};

	const renderMarketAccordion = (items, title, icon, color, index) => (
		<div className="asset-accordion-item">
			<Accordion.Title
				active={data.marketAccordionIndex === index}
				index={index}
				onClick={handleAccordionClick}
				className={`asset-accordion-title ${color} ${data.marketAccordionIndex === index ? 'active' : ''}`}
			>
				<Icon name="dropdown" className="dropdown-icon" />
				<Icon name={icon} className={`category-icon ${color}`} />
				<span className="category-label">{title}</span>
				{items && items.length > 0 && (
					<span className="count-badge">{items.length}</span>
				)}
			</Accordion.Title>
			<Accordion.Content active={data.marketAccordionIndex === index} className="asset-accordion-content">
				<div className="asset-items-list">
					{items && items.map((item, idx) => (
						<div key={idx} className="asset-item-card">
							<div className="asset-item-info">
								<div className="asset-item-symbol">{item.symbol}</div>
								<div className="asset-item-desc">{item.desc}</div>
							</div>
							<div className="asset-item-price">
								<div className="asset-item-value">
									{item.unit === '%' ? '' : item.unit === 'oz' ? '' : '$'}{item.price.toLocaleString()}{item.unit || ''}
								</div>
								<div className={`asset-item-change ${item.change >= 0 ? 'positive' : 'negative'}`}>
									{item.change >= 0 ? '▲' : '▼'} {Math.abs(item.change)}%
								</div>
							</div>
						</div>
					))}
				</div>
			</Accordion.Content>
		</div>
	);

	const getDefenseNewsArticles = () => {
		const keywords = [
			'defense', 'national security', 'military', 'pentagon', 'army', 'navy',
			'air force', 'space force', 'missile', 'cybersecurity', 'homeland',
			'nato', 'weapons', 'contract', 'aerospace', 'security'
		];
		const merged = []
			.concat(data.articles || [])
			.concat(data.breakingNews || [])
			.concat(data.trendingNews || []);
		const seen = new Set();
		const unique = merged.filter(article => {
			const key = article.url || article.title;
			if (!key || seen.has(key)) return false;
			seen.add(key);
			return true;
		});
		const defenseArticles = unique.filter(article => {
			const text = `${article.title || ''} ${article.description || ''} ${article.content || ''}`.toLowerCase();
			return keywords.some(keyword => text.includes(keyword));
		});
		if (defenseArticles.length > 0) return defenseArticles.slice(0, 50);

		return [
			{
				title: 'Pentagon procurement signals continued demand for aerospace, cyber, and readiness programs',
				description: 'Predovex is tracking federal contract activity across major defense primes, logistics agencies, and national security technology programs.',
				content: 'Defense and national security procurement remains active across aviation sustainment, missile defense, secure communications, cyber modernization, and logistics support.',
				source: 'Predovex Defense Desk',
				category: 'policy',
				impact_level: 'High',
				published_at: new Date().toISOString(),
				url: 'local-defense-brief-1'
			},
			{
				title: 'Defense contractors show broad contract flow across DoD, Navy, Air Force, and logistics agencies',
				description: 'Local intelligence view highlights award flow for Lockheed Martin, Boeing, Northrop Grumman, General Dynamics, and RTX.',
				content: 'Contract activity is distributed across platform sustainment, mission systems, logistics, cybersecurity, and advanced weapons programs.',
				source: 'Predovex Contracts Monitor',
				category: 'markets',
				impact_level: 'Medium',
				published_at: new Date(Date.now() - 3600000).toISOString(),
				url: 'local-defense-brief-2'
			},
			{
				title: 'National security technology demand remains focused on cyber, space, intelligence, and command systems',
				description: 'Federal buyers continue to prioritize modernization programs with relevance for software, satellite, and secure network vendors.',
				content: 'The defense technology pipeline points to continued budget focus on resilient communications, surveillance, space systems, and AI-enabled operations.',
				source: 'Predovex Security Brief',
				category: 'technology',
				impact_level: 'Medium',
				published_at: new Date(Date.now() - 7200000).toISOString(),
				url: 'local-defense-brief-3'
			}
		];
	};

	const loadWatchlistNews = async () => {
		if (!data.isLoggedIn) return;
		try {
			const news = await authAPI.getWatchlistNews();
			const keywords = await authAPI.getWatchlist();
			setData(prev => ({ 
				...prev, 
				watchlistNews: news || [], 
				watchlistKeywords: keywords.keywords || [] 
			}));
		} catch (error) {
			console.error('Error loading watchlist:', error);
		}
	};

	const addToWatchlist = async () => {
		if (!data.newWatchlistKeyword) return;
		try {
			await authAPI.addToWatchlist(data.newWatchlistKeyword);
			setData(prev => ({ ...prev, newWatchlistKeyword: '' }));
			loadWatchlistNews();
		} catch (error) {
			console.error('Error adding to watchlist:', error);
		}
	};

	const removeFromWatchlist = async (keyword) => {
		try {
			await authAPI.removeFromWatchlist(keyword);
			loadWatchlistNews();
		} catch (error) {
			console.error('Error removing from watchlist:', error);
		}
	};

	useEffect(() => {
		checkAuth();
		loadRSSNews('all');
		loadBreakingNews();
		loadTrendingNews();
		loadTrendingTopics();
		loadWatchlistNews();
		loadMarketPrices();
		getNewsSources();
		
		return () => {};
	}, []);

	// Auto-refresh main news every 30 minutes (resets when category/country changes)
	useEffect(() => {
		const interval = setInterval(function() {
			loadRSSNews(data.currentCategory, data.currentCountry);
			loadBreakingNews();
			loadTrendingNews();
			loadTrendingTopics();
		}, 30 * 60 * 1000);
		return () => clearInterval(interval);
	}, [data.currentCategory, data.currentCountry]);

	// Auto-refresh when switching tabs
	const tabMountedRef = useRef(false);
	const newsLastLoadedRef = useRef(0);
	const CACHE_TTL = 5 * 60 * 1000; // 5 minutes
	useEffect(function() {
		if (!tabMountedRef.current) {
			tabMountedRef.current = true;
			return;
		}
		var now = Date.now();
		var stale = now - newsLastLoadedRef.current > CACHE_TTL;
		if (stale) {
			newsLastLoadedRef.current = now;
			loadRSSNews(data.currentCategory, data.currentCountry);
			loadBreakingNews();
			loadTrendingNews();
			loadTrendingTopics();
		}
		if (data.activeTab === 1) loadMarketPrices();
	}, [data.activeTab]);

	const checkAuth = async () => {
		const token = localStorage.getItem('token');
		const premium = localStorage.getItem('hasPremium');
		if (token) {
			try {
				const user = await authAPI.getCurrentUser();
				setData(prev => ({
					...prev,
					isLoggedIn: true,
					userTier: user.tier,
					dailyLimit: user.daily_limit,
					requestsToday: user.requests_today,
					hasPremium: premium === 'true' || user.tier === 'premium',
				}));
			} catch (error) {
				localStorage.removeItem('token');
			}
		}
	};

	const loadRSSNews = async (category, country = data.currentCountry) => {
		setData(prev => ({ ...prev, isLoading: true }));
		try {
			// Try RSS feeds first (fetch 200 to get more results)
			const articles = await rssAPI.getAll(category, 200, country);
			if (articles && articles.length > 0) {
				const IMPACT_ORDER = { 'High': 0, 'Medium': 1, 'Low': 2 };
				
				// Transform all articles to appear as original Predovex content
				let transformedArticles = transformArticles(articles);
				
				// AI Feature: Remove duplicates first (lazy load for performance)
				if (data.enableDeduplication) {
					const { duplicateDetector } = await import('./utils/aiUtils');
					transformedArticles = await duplicateDetector.detectDuplicates(transformedArticles, 0.92);
				}
				
				// AI Feature: Cluster similar articles (lazy load for performance)
				if (data.enableClustering) {
					const { newsClusterer } = await import('./utils/aiUtils');
					const clusters = await newsClusterer.clusterArticles(transformedArticles, 0.85);
					setData(prev => ({ ...prev, clusteredArticles: clusters }));
					const stats = newsClusterer.getClusterStats(clusters);
				}
				
				// Sort by impact level
				transformedArticles = transformedArticles.sort((a, b) =>
					(IMPACT_ORDER[a.impact_level] !== undefined ? IMPACT_ORDER[a.impact_level] : 2) -
					(IMPACT_ORDER[b.impact_level] !== undefined ? IMPACT_ORDER[b.impact_level] : 2)
				);

				// HIGH-REVENUE AD INJECTION
				if (!data.hasPremium && transformedArticles.length > 5) {
					const highValueAds = [
						{
							title: "Trade Global Markets with 0% Commission",
							description: "Join 10M+ investors on eToro. Access stocks, crypto, and ETFs with zero fees. Exclusive for Predovex users.",
							url: "https://www.etoro.com/",
							source: "eToro Global",
							urlToImage: "https://images.unsplash.com/photo-1611974714025-467f56112705?w=500&q=80",
							isSponsored: true,
							publishedAt: new Date().toISOString()
						},
						{
							title: "Protect Your Policy Research with NordLayer",
							description: "Enterprise-grade security for government contractors. Secure your connection today.",
							url: "https://nordlayer.com/",
							source: "Nord Security",
							urlToImage: "https://images.unsplash.com/photo-1563986768609-322da13575f3?w=500&q=80",
							isSponsored: true,
							publishedAt: new Date().toISOString()
						}
					];
					transformedArticles.splice(2, 0, highValueAds[0]);
					transformedArticles.splice(8, 0, highValueAds[1]);
				}

				setData(prev => ({
					...prev,
					articles: transformedArticles,
					isArticleVisible: true,
					isLoading: false,
					currentCategory: category,
					currentCountry: country
				}));
				
				// Load personalized recommendations after articles are loaded (lazy load)
				setTimeout(() => {
					loadPersonalizedRecommendations(transformedArticles);
				}, 100);  // Defer to not block initial render
			} else {
				// Fallback to NewsAPI if RSS returns empty
				const query = category === 'all' ? 'news' : category;
				// Fallback to RSS - NewsAPI disabled
				const articles = await rssAPI.getAll(category, 100, country);
				const fallbackArticles = { articles: articles || [] };
				// Mark API articles
				const IMPACT_ORDER = { 'High': 0, 'Medium': 1, 'Low': 2 };
				const markedFallback = (fallbackArticles.articles || []).map(article => ({
					...article,
					isFromRSS: false,
					sourceLabel: article.source && article.source.name
						? article.source.name
						: 'News API'
				})).sort((a, b) =>
					(IMPACT_ORDER[a.impact_level] !== undefined ? IMPACT_ORDER[a.impact_level] : 2) -
					(IMPACT_ORDER[b.impact_level] !== undefined ? IMPACT_ORDER[b.impact_level] : 2)
				);
				setData(prev => ({
					...prev,
					articles: markedFallback,
					isArticleVisible: true, 
					isLoading: false,
					currentCategory: category
				}));
			}
		} catch (error) {
			console.error('Error loading RSS news, using fallback:', error);
			// Fallback to NewsAPI on error
			try {
				const query = category === 'all' ? 'news' : category;
				// Fallback to RSS - NewsAPI disabled
				const articles = await rssAPI.getAll(category, 100, country);
				const fallbackArticles = { articles: articles || [] };
				// Mark API articles
				const IMPACT_ORDER = { 'High': 0, 'Medium': 1, 'Low': 2 };
				const markedFallback = (fallbackArticles.articles || []).map(article => ({
					...article,
					isFromRSS: false,
					sourceLabel: article.source && article.source.name
						? article.source.name
						: 'News API'
				})).sort((a, b) =>
					(IMPACT_ORDER[a.impact_level] !== undefined ? IMPACT_ORDER[a.impact_level] : 2) -
					(IMPACT_ORDER[b.impact_level] !== undefined ? IMPACT_ORDER[b.impact_level] : 2)
				);
				setData(prev => ({ 
					...prev, 
					articles: markedFallback, 
					isArticleVisible: true, 
					isLoading: false,
					currentCategory: category
				}));
			} catch (fallbackError) {
				console.error('Fallback also failed:', fallbackError);
				setData(prev => ({ ...prev, isLoading: false, newsLoadError: true }));
			}
		}
	};

	const loadBreakingNews = async () => {
		try {
			const breaking = await rssAPI.getBreaking(20);
			setData(prev => ({
				...prev,
				breakingNews: breaking || [],
				breakingNewsLastUpdated: new Date()
			}));
		} catch (error) {
			console.error('Error loading breaking news:', error);
		}
	};

	const loadTrendingNews = async () => {
		try {
			const trending = await rssAPI.getTrendingNews(20);
			setData(prev => ({ ...prev, trendingNews: trending || [] }));
		} catch (error) {
			console.error('Error loading trending news:', error);
		}
	};

	const loadTrendingTopics = async () => {
		try {
			const trending = await rssAPI.getTrending();
			setData(prev => ({ ...prev, trendingTopics: trending || [] }));
		} catch (error) {
			console.error('Error loading trending topics:', error);
		}
	};

	const handleSearchChange = (e, { value }) => {
		updateData('value', value);
		setSemanticQuery(value);
	};

	const updateData = (updateKey, updateValue) => {
		setData({ ...data, [updateKey]: updateValue });
	};

	const getHeadlines = function (category) {
		loadRSSNews(category);
	};

	const getNewsSources = function () {
		// DISABLED: NewsAPI sources call
		// API.get('sources').then(res => {
		// 	sources = res.sources;
		// });
	};

	const searchOnEnter = function (event) {
		if (event.keyCode === 13) {
			if (data.value) {
				// DISABLED: NewsAPI search - using backend search instead
				// API.get(`everything?q=${data.value}`).then(res =>
				// 	updateData('result', res.articles)
				// );
			} else {
				updateData('result', []);
			}
		}
	};

	const categoryChange = function (event, { value }) {
		setData(prev => ({ ...prev, currentCategory: value }));
		loadRSSNews(value, data.currentCountry);
	};

	const countryChange = function (event, { value }) {
		setData(prev => ({ ...prev, currentCountry: value }));
		loadRSSNews(data.currentCategory, value);
	};


	const getIntelligenceStats = () => {
		const articles = data.articles || [];
		return {
			highImpact: articles.filter(a => a.impact_level === 'High').length,
			positive: articles.filter(a => a.sentiment === 'Positive').length,
			total: articles.length
		};
	};

	const getSentimentHeatmap = () => {
		const categories = ['general', 'markets', 'economy', 'technology', 'policy', 'health', 'finance'];
		const heatmap = {};
		
		categories.forEach(cat => {
			const catArticles = (data.articles || []).filter(a => a.category === cat);
			if (catArticles.length === 0) {
				heatmap[cat] = { score: 50, label: 'Neutral', color: 'grey' };
				return;
			}
			
			const pos = catArticles.filter(a => a.sentiment === 'Positive').length;
			const neg = catArticles.filter(a => a.sentiment === 'Negative').length;
			const total = catArticles.length;
			
			// Calculate a score from 0 to 100
			const score = Math.round(((pos - neg + total) / (2 * total)) * 100);
			
			let label = 'Neutral';
			let color = 'grey';
			if (score > 60) { label = 'Bullish'; color = 'green'; }
			else if (score < 40) { label = 'Bearish'; color = 'red'; }
			
			heatmap[cat] = { score, label, color, count: total };
		});
		
		return heatmap;
	};

	const stats = getIntelligenceStats();
	const heatmap = getSentimentHeatmap();

	const handleLogin = async (email, password) => {
		try {
			const response = await authAPI.login(email, password);
			setData(prev => ({
				...prev,
				isLoggedIn: true,
				userTier: response.tier,
				dailyLimit: response.daily_limit,
			}));
			return { success: true };
		} catch (error) {
			return {
				success: false,
				error:
					error.response && error.response.data
						? error.response.data.detail || 'Login failed'
						: 'Login failed',
			};
		}
	};

	const handleLogout = () => {
		authAPI.logout();
		setData(prev => ({
			...prev,
			isLoggedIn: false,
			userTier: 'free',
			hasPremium: false,
			dailyLimit: 50,
			requestsToday: 0,
			watchlistKeywords: [],
			watchlistNews: [],
		}));
	};

	// AI Feature: Load personalized recommendations (lazy load)
	const loadPersonalizedRecommendations = async (allArticles) => {
		try {
			const { userPreferenceLearner } = await import('./utils/aiUtils');
			// Get recommendations based on user history
			const recs = await userPreferenceLearner.getRecommendations(allArticles, 15);
			setData(prev => ({ ...prev, personalizedArticles: recs }));
		} catch (error) {
			console.error('Failed to load personalized recommendations:', error);
		}
	};

	// AI Feature: Track article read for personalization (lazy load)
	const trackArticleRead = async (article, readDuration = 30) => {
		try {
			const { userPreferenceLearner } = await import('./utils/aiUtils');
			await userPreferenceLearner.articleRead(article, readDuration);
			
			// Reload recommendations with new history
			if (data.articles.length > 0) {
				loadPersonalizedRecommendations(data.articles);
			}
		} catch (error) {
			console.error('Failed to track article read:', error);
		}
	};

	// AI Feature: Auto-tag articles with topics (lazy load)
	const autoTagArticles = async (articles) => {
		try {
			const { topicModeler } = await import('./utils/aiUtils');
			const tagged = await topicModeler.categorizeBatch(articles.slice(0, 50));  // First 50 for performance
			return tagged;
		} catch (error) {
			console.error('Failed to auto-tag articles:', error);
			return articles;
		}
	};

	const handleUpgrade = plan => {
		localStorage.setItem('tier', plan);
		localStorage.setItem('hasPremium', 'true');
		setData(prev => ({
			...prev,
			userTier: plan,
			hasPremium: true,
			dailyLimit: plan === 'enterprise' ? -1 : plan === 'pro' ? 5000 : 50,
		}));
		alert(`🎉 Upgraded to ${plan} plan! Enjoy full access to all premium features.`);
	};

	const handleRemoveAdsSubscribe = () => {
		localStorage.setItem('hasPremium', 'true');
		setData(prev => ({ ...prev, hasPremium: true }));
		alert('Thank you for subscribing! Ads have been removed.');
	};

	const handleTopicClick = (topic) => {
		// Search for the topic - DISABLED NewsAPI, using backend instead
		setData(prev => ({ ...prev, value: topic }));
		// API.get(`everything?q=${topic}`).then(res =>
		// 	updateData('result', res.articles)
		// );
	};

	// New: Handle filter click (High Impact, Positive, Negative)
	const handleFilterClick = (filterType) => {
		try {
			const articles = data.articles || [];
			let filtered = [];

			if (filterType === 'high-impact') {
				filtered = articles.filter(a => a.impact_level === 'High');
			} else if (filterType === 'positive') {
				filtered = articles.filter(a => a.sentiment === 'Positive');
			} else if (filterType === 'negative') {
				filtered = articles.filter(a => a.sentiment === 'Negative');
			} else if (filterType === 'clear') {
				// Clear all filters
				setData(prev => ({
					...prev,
					activeFilter: null,
					filteredArticles: [],
					sortBy: 'relevance',
					sortOrder: 'desc'
				}));
				return;
			}

			// Sort the filtered articles
			filtered = sortArticles(filtered, data.sortBy, data.sortOrder);

			setData(prev => ({
				...prev,
				activeFilter: filterType,
				filteredArticles: filtered
			}));
		} catch (error) {
			console.error('Filter error:', error);
			// Fallback: just show all articles
			setData(prev => ({
				...prev,
				activeFilter: null,
				filteredArticles: []
			}));
		}
	};

	// New: Sort articles
	const sortArticles = (articles, sortBy = 'relevance', sortOrder = 'desc') => {
		const sorted = [...articles];
		sorted.sort((a, b) => {
			let comparison = 0;

			if (sortBy === 'date') {
				const dateA = new Date(a.published_at || a.publishedAt || 0);
				const dateB = new Date(b.published_at || b.publishedAt || 0);
				comparison = dateA - dateB;
			} else if (sortBy === 'impact') {
				const impactOrder = { 'High': 3, 'Medium': 2, 'Low': 1 };
				const impactA = impactOrder[a.impact_level] || 0;
				const impactB = impactOrder[b.impact_level] || 0;
				comparison = impactA - impactB;
			} else if (sortBy === 'sentiment') {
				const sentimentOrder = { 'Positive': 2, 'Neutral': 1, 'Negative': 0 };
				const sentA = sentimentOrder[a.sentiment] || 1;
				const sentB = sentimentOrder[b.sentiment] || 1;
				comparison = sentA - sentB;
			}

			return sortOrder === 'desc' ? -comparison : comparison;
		});
		return sorted;
	};

	// New: Handle sort change
	const handleSortChange = (newSortBy) => {
		const newOrder = data.sortOrder === 'asc' ? 'desc' : 'asc';
		
		// If there's an active filter, re-sort filtered articles
		if (data.activeFilter && data.filteredArticles.length > 0) {
			const sorted = sortArticles(data.filteredArticles, newSortBy, newOrder);
			setData(prev => ({
				...prev,
				sortBy: newSortBy,
				sortOrder: newOrder,
				filteredArticles: sorted
			}));
		} else {
			// Sort all articles
			const sorted = sortArticles(data.articles, newSortBy, newOrder);
			setData(prev => ({
				...prev,
				sortBy: newSortBy,
				sortOrder: newOrder,
				articles: sorted
			}));
		}
	};

	// Handle article click - open article reader
	const handleArticleClick = (article) => {
		if (!article) return;
		
		// Track reading for personalization
		trackArticleRead(article, 30);  // Assume 30 second read
		
		const newReadCount = data.articlesReadThisSession + 1;
		const shouldShowAd = !data.hasPremium && newReadCount % 3 === 0;

		setData(prev => ({
			...prev,
			selectedArticleForReading: article,
			articleReaderOpen: true,
			articlesReadThisSession: newReadCount,
			showInterstitial: shouldShowAd
		}));
	};

	const safeFormatDate = (dateVal) => {
		if (!dateVal) return 'Recently';
		try {
			const d = new Date(dateVal);
			return isNaN(d.getTime()) ? 'Recently' : d.toLocaleString();
		} catch (e) {
			return 'Recently';
		}
	};
	var TabFallback = <div style={{ padding: '40px', textAlign: 'center', color: '#888' }}>Loading...</div>;

	const panes = [
		{
			menuItem: (
				<>
					<Icon name="lightning" color="yellow" />
					Daily Briefing
				</>
			),
			render: () => (
				<Tab.Pane>
					{!data.hasPremium && <AdComponent type="banner" />}
					<Suspense fallback={TabFallback}>
						<GovShorts
							articles={data.articles}
							onArticleClick={handleArticleClick}
						/>
					</Suspense>
					{!data.hasPremium && <AdComponent type="native" />}
				</Tab.Pane>
			),
		},
		{
			menuItem: (
				<>
					<Icon name="heart" color="red" />
					For You
				</>
			),
			render: () => (
				<Tab.Pane>
					<Segment secondary style={{ marginBottom: '15px' }}>
						<Header as="h3">
							<Icon name="magic" /> Personalized For You
						</Header>
						<p>
							AI-powered recommendations based on your reading history and preferences.
							{data.personalizedArticles.length > 0 
								? ` Showing ${data.personalizedArticles.length} personalized articles.`
								: ' Read more articles to get better recommendations.'}
						</p>
					</Segment>
					<NewsCards
						articles={data.personalizedArticles.length > 0 ? data.personalizedArticles : data.articles.slice(0, 10)}
						onArticleClick={handleArticleClick}
						onBookmarkChange={(bm) => setData(prev => ({ ...prev, bookmarks: bm }))}
					/>
				</Tab.Pane>
			),
		},
		{
			menuItem: (
				<>
					<Icon name="chart area" color="blue" />
					Intelligence Dashboard
				</>
			),
			render: () => (
				<Tab.Pane>
					<Suspense fallback={TabFallback}><ImpactTrends /></Suspense>
				</Tab.Pane>
			),
		},
		{
			menuItem: (
				<>
					<Icon name="line graph" color="purple" />
					Policy Impact
				</>
			),
			render: () => (
				<Tab.Pane>
					<Suspense fallback={TabFallback}><PolicyImpactDashboard /></Suspense>
				</Tab.Pane>
			),
		},
		{
			menuItem: (
				<>
					<Icon name="shield alternate" color="blue" />
					Defense News
				</>
			),
			render: () => (
				<Tab.Pane>
					<Suspense fallback={TabFallback}>
					<DefenseContracts />
					</Suspense>
					{/* Defense News Feed */}
					<Segment raised style={{ marginTop: '20px' }}>
						<Header as="h3">
							<Icon name="newspaper" />
							Defense & National Security News
						</Header>
						<NewsCards
							articles={getDefenseNewsArticles()}
							onArticleClick={handleArticleClick}
						/>
					</Segment>
				</Tab.Pane>
			),
		},
		{
			menuItem: (
				<>
					<Icon name="fire" color="purple" />
					Trending Predictions
				</>
			),
			render: () => (
				<Tab.Pane>
					<Suspense fallback={TabFallback}><TrendingPredictions /></Suspense>
				</Tab.Pane>
			),
		},
		{
			menuItem: (
				<>
					<Icon name="chart line" color="green" />
					Markets
				</>
			),
			render: () => (
				<Tab.Pane>
					<MarketTicker />
					<TabErrorBoundary>
						<Suspense fallback={TabFallback}>
							<StockSentimentDashboard marketPrices={data.marketPrices} />
							<DeepAnalysisDashboard />
						</Suspense>
					</TabErrorBoundary>

					{/* Market Intelligence Section */}
					<Grid stackable columns={2} style={{ marginTop: '20px' }}>
						{/* Left Column: Market Data */}
						<Grid.Column width={6}>
							{/* Asset Class Summary */}
							<Segment raised>
								<Header as="h3" textAlign="center">
									<Icon name="university" />
									Asset Class Summary
								</Header>
								<div className="asset-class-accordion">
									<Accordion styled fluid>
										{renderMarketAccordion(data.marketPrices.stocks, "Stocks (Equities)", "line graph", "blue", 0)}
										{renderMarketAccordion(data.marketPrices.bonds, "Bonds (Fixed Income)", "file alternate outline", "teal", 1)}
										{renderMarketAccordion(data.marketPrices.mutual_funds, "Mutual Funds", "users", "purple", 2)}
										{renderMarketAccordion(data.marketPrices.etfs, "ETFs", "exchange", "purple", 3)}
										{renderMarketAccordion(data.marketPrices.cash, "Cash & Equivalents", "money bill alternate outline", "green", 4)}
										{renderMarketAccordion(data.marketPrices.real_estate, "Real Estate (REITs)", "home", "brown", 5)}
										{renderMarketAccordion(data.marketPrices.metals, "Commodities / Metals", "diamond", "yellow", 6)}
										{renderMarketAccordion(data.marketPrices.crypto, "Digital Assets / Crypto", "bitcoin", "orange", 7)}
									</Accordion>
								</div>
							</Segment>
							
							{/* Economic Calendar */}
							<Segment raised>
								<Suspense fallback={TabFallback}><EconomicCalendar /></Suspense>
							</Segment>
						</Grid.Column>

						{/* Right Column: Market News */}
						<Grid.Column width={10}>
							<Header as="h3">
								<Icon name="newspaper" />
								Market Intelligence Feed
							</Header>
							<NewsCards
								articles={data.articles.filter(a =>
									['markets', 'crypto', 'forex', 'stocks', 'metals', 'investing', 'analysis']
									.includes(a.category)
								)}
								onArticleClick={handleArticleClick}
							/>
						</Grid.Column>
					</Grid>
				</Tab.Pane>
			),
		},
		{
			menuItem: (
				<>
					<Icon name="certificate" color="yellow" />
					Patent Evidence
				</>
			),
			render: () => (
				<Tab.Pane>
					<Suspense fallback={TabFallback}><PatentEvidenceDashboard /></Suspense>
				</Tab.Pane>
			),
		},
		{
			menuItem: (
				<>
					<Icon name="newspaper" />
					{data.currentCategory === 'all' ? 'All News' : 
					 data.currentCategory.charAt(0).toUpperCase() + data.currentCategory.slice(1) + ' News'}
				</>
			),
			render: () => (
				<Tab.Pane>
					<PullToRefresh onRefresh={function() { return new Promise(function(resolve) { loadRSSNews(data.currentCategory); setTimeout(resolve, 1500); }); }}>
					{/* Breaking News Ticker - Only show if user doesn't have premium */}
					{!data.hasPremium && <BreakingNewsTicker breakingNews={data.breakingNews} />}

					{/* Top Banner Ad - Only show if user doesn't have premium */}
					{!data.hasPremium && <AdComponent type="banner" />}

					<Grid columns={2} stackable>
						<Grid.Column width={12}>
							{data.value && data.value.length >= 3 && (
								<Message info icon>
									<Icon name={isSemanticLoading ? 'notched circle' : 'lightning'} loading={isSemanticLoading} />
									<Message.Content>
										<Message.Header>
											{isSemanticLoading ? 'AI is analyzing your query...' : 'Semantic Search Results'}
										</Message.Header>
										Found {semanticResults.length} articles matching the <em>meaning</em> of "{data.value}"
									</Message.Content>
								</Message>
							)}
							
							{/* Filter & Sort Controls */}
							{data.activeFilter && (
								<Segment secondary style={{ marginBottom: '15px', background: data.isDarkMode ? 'rgba(255,255,255,0.05)' : '#f0f8ff' }}>
									<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
										<div>
											<Label color={data.activeFilter === 'high-impact' ? 'red' : data.activeFilter === 'positive' ? 'green' : 'blue'} size="large">
												<Icon name="filter" /> 
												{data.activeFilter === 'high-impact' ? 'High Impact Articles' : 
												 data.activeFilter === 'positive' ? 'Positive Sentiment' : 
												 data.activeFilter === 'negative' ? 'Negative Sentiment' : 'All Articles'}
											</Label>
											<span style={{ marginLeft: '10px', fontWeight: 'bold' }}>
												{data.filteredArticles.length} articles found
											</span>
										</div>
										<div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
											<Label basic>Sort by:</Label>
											<Button 
												size="small" 
												active={data.sortBy === 'date'} 
												onClick={() => handleSortChange('date')}
											>
												<Icon name="calendar" /> Date
											</Button>
											<Button 
												size="small" 
												active={data.sortBy === 'impact'} 
												onClick={() => handleSortChange('impact')}
											>
												<Icon name="diamond" /> Impact
											</Button>
											<Button 
												size="small" 
												active={data.sortBy === 'sentiment'} 
												onClick={() => handleSortChange('sentiment')}
											>
												<Icon name="smile" /> Sentiment
											</Button>
											<Button 
												icon="exchange" 
												size="small" 
												onClick={() => handleSortChange(data.sortBy)}
												title={`Toggle ${data.sortOrder === 'asc' ? 'descending' : 'ascending'} order`}
											/>
											<Button 
												color="red" 
												size="small" 
												onClick={() => handleFilterClick('clear')}
											>
												<Icon name="close" /> Clear Filter
											</Button>
										</div>
									</div>
								</Segment>
							)}

							{data.newsLoadError && !data.isLoading && data.articles.length === 0 && (
								<div style={{ textAlign: 'center', padding: '40px 20px' }}>
									<Icon name="warning circle" size="huge" style={{ color: '#c8553d' }} />
									<p style={{ fontFamily: 'IBM Plex Sans, sans-serif', marginTop: 12, color: '#3d3a35' }}>
										Unable to load articles. Check your connection.
									</p>
									<Button
										onClick={function() {
											setData(function(prev) { return Object.assign({}, prev, { newsLoadError: false }); });
											loadRSSNews(data.currentCategory);
										}}
									>
										<Icon name="refresh" /> Retry
									</Button>
								</div>
							)}

							<NewsCards
								articles={data.value && data.value.length >= 3 ? semanticResults :
								        data.activeFilter && data.filteredArticles.length > 0 ? data.filteredArticles :
								        data.enableClustering && data.clusteredArticles.length > 0 ? data.clusteredArticles :
								        data.articles}
								loading={data.isLoading || isSemanticLoading}
								onArticleClick={handleArticleClick}
								onBookmarkChange={(bm) => setData(prev => ({ ...prev, bookmarks: bm }))}
							/>
							
							{/* In-feed Native Ads - Every 10 articles */}
							{!data.hasPremium && data.articles.length > 10 && (
								<>
									<AdComponent type="native" />
									<AdComponent type="native" />
								</>
							)}
						</Grid.Column>
						<Grid.Column width={4}>
							<div style={{ position: 'sticky', top: '20px' }}>
								{/* Trending Topics Sidebar */}
								<TrendingTopics 
									trending={data.trendingTopics} 
									onTopicClick={handleTopicClick}
								/>

								{!data.hasPremium && <Suspense fallback={<span/>}><MarketToolsWidget /></Suspense>}
								
								{/* Sidebar Ad */}
								{!data.hasPremium && <AdComponent type="banner" />}
								
								{/* Remove Ads CTA */}
								{!data.hasPremium && (
									<Segment textAlign="center" className="remove-ads-cta">
										<Icon name="star" color="yellow" size="big" />
										<h4>Tired of Ads?</h4>
										<p>Get Premium Access - Free Beta!</p>
										<Button
											color="green"
											fluid
											onClick={() =>
												setData(prev => ({ ...prev, showRemoveAdsModal: true }))
											}
										>
											<Icon name="remove" />
											Activate Premium (Free)
										</Button>
									</Segment>
								)}
							</div>
						</Grid.Column>
					</Grid>
					</PullToRefresh>
				</Tab.Pane>
			),
		},
		{
			menuItem: (
				<>
					<Icon name="bolt" color="red" />
					Breaking News
				</>
			),
			render: () => (
				<Tab.Pane>
					{!data.hasPremium && <AdComponent type="banner" />}
					{data.breakingNews && data.breakingNews.length > 0 ? (
						<Suspense fallback={TabFallback}>
							<BreakingNewsPage
								breakingNews={data.breakingNews}
								onRefresh={loadBreakingNews}
								lastUpdated={data.breakingNewsLastUpdated}
								onArticleClick={handleArticleClick}
							/>
						</Suspense>
					) : (
						<Container textAlign="center" style={{ padding: '50px 0' }}>
							<Icon name="notched circle" loading size="huge" color="blue" />
							<Header as="h2">Loading Breaking News...</Header>
							<p>Fetching latest updates from multiple sources</p>
							<Button onClick={loadBreakingNews} color="blue">
								<Icon name="refresh" /> Refresh
							</Button>
						</Container>
					)}
				</Tab.Pane>
			),
		},
		{
			menuItem: (
				<>
					<Icon name="fire" color="orange" />
					Trending
				</>
			),
			render: () => (
				<Tab.Pane>
					{!data.hasPremium && <AdComponent type="banner" />}
					<Suspense fallback={TabFallback}>
						<TrendingNewsPage
							trendingNews={data.trendingNews}
							onRefresh={loadTrendingNews}
							onArticleClick={handleArticleClick}
						/>
					</Suspense>
					{!data.hasPremium && <AdComponent type="native" />}
				</Tab.Pane>
			),
		},
		{
			menuItem: (
				<>
					<Icon name="eye" color="teal" />
					Watchlist
				</>
			),
			render: () => (
				<Tab.Pane>
					{!data.isLoggedIn ? (
						<Segment textAlign="center" padding="50">
							<Icon name="lock" size="huge" color="grey" />
							<Header as="h2">Login to Create Your Watchlist</Header>
							<p>Track specific keywords like "H1B", "GST", or "Bitcoin" automatically.</p>
							<Button color="blue" onClick={() => setData(prev => ({ ...prev, showLoginModal: true }))}>
								Login Now
							</Button>
						</Segment>
					) : (
						<Grid stackable>
							<Grid.Column width={16}>
								<Segment color="teal">
									<Header as="h3">
										<Icon name="settings" />
										Manage Your Intelligence
									</Header>
									<Form onSubmit={addToWatchlist}>
										<Input
											placeholder="Add keyword or ticker (e.g. H1B, AAPL, Bitcoin)..."
											value={data.newWatchlistKeyword}
											onChange={(e) => {
												const val = e.target.value;
												setData(prev => ({ ...prev, newWatchlistKeyword: val }));
											}}
											action={<Button color="teal" type="submit" icon="add" />}
										/>
									</Form>
									<div style={{ marginTop: '15px' }}>
										{data.watchlistKeywords && data.watchlistKeywords.map(keyword => (
											<Label key={keyword} color="teal" size="large" style={{ marginBottom: '5px' }}>
												{keyword}
												<Icon name="delete" onClick={() => removeFromWatchlist(keyword)} />
											</Label>
										))}
									</div>
								</Segment>
							</Grid.Column>
							{/* Price Heatmap */}
							<Grid.Column width={16}>
								<Suspense fallback={TabFallback}><WatchlistHeatmap watchlistKeywords={data.watchlistKeywords} /></Suspense>
							</Grid.Column>
							{/* Price Alerts */}
							<Grid.Column width={16}>
								<Suspense fallback={TabFallback}><PriceAlerts /></Suspense>
							</Grid.Column>
							<Grid.Column width={16}>
								{!data.hasPremium && <AdComponent type="banner" />}
								<Header as="h2" dividing>
									<Icon name="filter" />
									Your Personalized Feed
								</Header>
								{data.watchlistNews.length > 0 ? (
									<NewsCards
										articles={data.watchlistNews}
										onArticleClick={handleArticleClick}
									/>
								) : (
									<Segment textAlign="center" basic>
										<Icon name="search" size="large" color="grey" />
										<p>No articles found matching your keywords yet. Try adding more general terms!</p>
									</Segment>
								)}
							</Grid.Column>
						</Grid>
					)}
				</Tab.Pane>
			),
		},
		{
			menuItem: '💰 Subscription',
			render: () => (
				<Tab.Pane>
					<Suspense fallback={TabFallback}>
						<SubscriptionPlans
							currentTier={data.userTier}
							onUpgrade={handleUpgrade}
						/>
					</Suspense>
				</Tab.Pane>
			),
		},
		{
			menuItem: (
				<>
					<Icon name="lightbulb outline" color="purple" />
					AI Analysis
				</>
			),
			render: () => (
				<Tab.Pane>
					{!data.hasPremium && <AdComponent type="banner" />}
					<Suspense fallback={TabFallback}><NLPAnalysis articles={data.articles} /></Suspense>
				</Tab.Pane>
			),
		},
		{
			menuItem: (
				<>
					<Icon name="bookmark" color="yellow" />
					Saved
					{data.bookmarks && data.bookmarks.length > 0 && (
						<span style={{ marginLeft: '6px', background: '#2185d0', color: 'white', borderRadius: '10px', padding: '1px 7px', fontSize: '11px', fontWeight: 700 }}>
							{data.bookmarks.length}
						</span>
					)}
				</>
			),
			render: () => (
				<Tab.Pane>
					{data.bookmarks && data.bookmarks.length > 0 ? (
						<>
							<Header as="h3" dividing>
								<Icon name="bookmark" color="yellow" /> Saved Articles ({data.bookmarks.length})
							</Header>
							<NewsCards
								articles={data.bookmarks}
								onArticleClick={handleArticleClick}
								onBookmarkChange={(bm) => setData(prev => ({ ...prev, bookmarks: bm }))}
							/>
						</>
					) : (
						<Segment textAlign="center" basic style={{ padding: '60px 20px' }}>
							<Icon name="bookmark outline" size="huge" color="grey" />
							<Header as="h3" style={{ color: '#aaa' }}>No saved articles yet</Header>
							<p style={{ color: '#bbb' }}>Click the bookmark icon on any article to save it here.</p>
						</Segment>
					)}
				</Tab.Pane>
			),
		},
		// ── pane 15: Portfolio Tracker ─────────────────────────────
		{
			menuItem: (
				<>
					<Icon name="chart pie" color="teal" />
					Portfolio
				</>
			),
			render: () => (
				<Tab.Pane>
					<Suspense fallback={TabFallback}><PortfolioTracker /></Suspense>
				</Tab.Pane>
			),
		},
		// ── pane 16: Trading Intelligence (Earnings + Insider + Sentiment + Explainer + Geo) ──
		{
			menuItem: (
				<>
					<Icon name="spy" color="purple" />
					Trading Intel
				</>
			),
			render: () => (
				<Tab.Pane>
					<TabErrorBoundary>
						<Suspense fallback={TabFallback}>
						<Grid stackable>
							<Grid.Row>
								<Grid.Column width={16}>
									<TabErrorBoundary><EarningsCalendarWidget /></TabErrorBoundary>
								</Grid.Column>
							</Grid.Row>
							<Grid.Row columns={2}>
								<Grid.Column width={10}>
									<TabErrorBoundary><SentimentTimeline /></TabErrorBoundary>
								</Grid.Column>
								<Grid.Column width={6}>
									<TabErrorBoundary><GeopoliticalRisk /></TabErrorBoundary>
								</Grid.Column>
							</Grid.Row>
							<Grid.Row>
								<Grid.Column width={16}>
									<TabErrorBoundary><EventExplainer /></TabErrorBoundary>
								</Grid.Column>
							</Grid.Row>
							<Grid.Row>
								<Grid.Column width={16}>
									<TabErrorBoundary><InsiderTrading /></TabErrorBoundary>
								</Grid.Column>
							</Grid.Row>
						</Grid>
						</Suspense>
					</TabErrorBoundary>
				</Tab.Pane>
			),
		},
	];

	const renderGovernmentNews = () => {
		if (data.governmentArticles.length === 0) {
			return (
				<Segment textAlign="center" style={{ padding: '40px' }}>
					<Icon name="newspaper" size="huge" color="grey" />
					<h3>No government articles yet</h3>
					<p>Click "Load Government News" to fetch from official sources</p>
				</Segment>
			);
		}
		return (
			<Suspense fallback={TabFallback}>
				{data.governmentArticles.map((article, index) => (
					<GovernmentNewsCard key={index} article={article} />
				))}
			</Suspense>
		);
	};

	const loadGovernmentNews = async () => {
		if (!data.isLoggedIn) {
			setData(prev => ({ ...prev, showLoginModal: true }));
			return;
		}

		setData(prev => ({ ...prev, isLoadingGov: true }));
		try {
			const articles = await articlesAPI.getAll(data.currentCategory, 25);
			setData(prev => ({
				...prev,
				governmentArticles: articles || [],
				requestsToday: prev.requestsToday + 1,
			}));
		} catch (error) {
			console.error('Error loading government news:', error);
			if (error.response && error.response.status === 429) {
				setData(prev => ({ ...prev, showSubscription: true }));
			}
		} finally {
			setData(prev => ({ ...prev, isLoadingGov: false }));
		}
	};

	const toggleDarkMode = () => {
		const newMode = !data.isDarkMode;
		setData(prev => ({ ...prev, isDarkMode: newMode }));
		localStorage.setItem('darkMode', newMode);
	};


	// ── Design system nav groups ──────────────────────────────
	const NAV_GROUPS = [
		{ id: 'frontpage', label: 'Front Page', pane: 0 },
		{ id: 'news', label: 'News', subs: [
			{ id: 'news-foryou',   label: 'For You',  pane: 1  },
			{ id: 'news-all',      label: 'All News', pane: 8  },
			{ id: 'news-breaking', label: 'Breaking', pane: 9  },
			{ id: 'news-trending', label: 'Trending', pane: 10 },
		]},
		{ id: 'intel', label: 'Intelligence', subs: [
			{ id: 'intel-dash',   label: 'Dashboard',    pane: 2  },
			{ id: 'intel-policy', label: 'Policy Impact',pane: 3  },
			{ id: 'intel-pred',   label: 'Predictions',  pane: 5  },
			{ id: 'intel-pat',    label: 'Patent Intel', pane: 7  },
			{ id: 'intel-ai',     label: 'AI Analysis',  pane: 13 },
		]},
		{ id: 'markets',  label: 'Markets',  pane: 6  },
		{ id: 'defense',  label: 'Defense',  pane: 4  },
		{ id: 'account',  label: 'Account',  subs: [
			{ id: 'acc-watch', label: 'Watchlist',    pane: 11 },
			{ id: 'acc-saved', label: 'Saved',        pane: 14 },
			{ id: 'acc-sub',   label: 'Subscription', pane: 12 },
		]},
		{ id: 'portfolio',     label: 'Portfolio',     pane: 15 },
		{ id: 'trading-intel', label: 'Trading Intel', pane: 16 },
	];

	// Find which group is active
	let _activeGroup = NAV_GROUPS[0];
	NAV_GROUPS.forEach(g => {
		if (!g.subs && g.pane === data.activeTab) _activeGroup = g;
		if (g.subs) g.subs.forEach(s => { if (s.pane === data.activeTab) _activeGroup = g; });
	});
	const activeGroupSubs = _activeGroup.subs || null;
	const isFrontPage = data.activeTab === 0;
	const todayLabel = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });

	return (
		<div
			className={'gp-root' + (data.isDarkMode ? ' dark-mode' : '')}
			data-theme={data.isDarkMode ? 'dark' : 'light'}
		>
			{/* ═══════════════════════════════════
			    PREDOVEX MASTHEAD
			    3-column: date · big serif title · account
			    ═══════════════════════════════════ */}
			<header className="gp-mast">
				<div className="gp-mast-left">
					<span>Vol. XIV</span>
					<span className="gp-mast-sep">·</span>
					<span>{todayLabel}</span>
					{data.hasPremium && (
						<>
							<span className="gp-mast-sep">·</span>
							<span style={{ color: 'var(--gp-accent)' }}>PREMIUM</span>
						</>
					)}
				</div>

				<div>
					<h1 className="gp-mast-title">Pre<em>dovex</em></h1>
					<div className="gp-mast-sub">Markets · Intelligence · Policy · Defense · Established 2024</div>
				</div>

				<div className="gp-mast-right">
					{data.isLoggedIn ? (
						<button className="gp-acct-chip" onClick={handleLogout} title="Click to logout">
							<span className="gp-acct-dot"></span>
							<span className="gp-acct-name">{data.userEmail || 'USER'}</span>
							<span className="gp-acct-tier">{data.userTier ? data.userTier.toUpperCase() : 'FREE'}</span>
						</button>
					) : (
						<button
							className="gp-acct-btn"
							onClick={() => setData(prev => ({ ...prev, showLoginModal: true }))}
						>
							Sign In
						</button>
					)}
					<button
						className="gp-acct-btn"
						onClick={toggleDarkMode}
						style={{ padding: '5px 8px', fontSize: '14px' }}
						title={data.isDarkMode ? 'Light mode' : 'Dark mode'}
					>
						{data.isDarkMode ? '☀' : '☾'}
					</button>
				</div>
			</header>

			{/* ── Live market ticker (always visible) ── */}
			<MarketTicker />

			{/* ═══════════════════════════════════
			    PRIMARY NAV — grouped sections
			    ═══════════════════════════════════ */}
			<nav className="gp-nav" style={{ position: 'sticky', top: 0, zIndex: 200 }}>
				{NAV_GROUPS.map(group => (
					<button
						key={group.id}
						className={_activeGroup.id === group.id ? 'active' : ''}
						onClick={() => {
							const targetPane = group.subs ? group.subs[0].pane : group.pane;
							setData(prev => ({ ...prev, activeTab: targetPane, mobileMenuOpen: false }));
						}}
					>
						{group.label}
						{group.subs && <span className="gp-nav-caret">▾</span>}
					</button>
				))}
				<span className="gp-nav-spacer" />
				<div className="gp-search">
					<span className="ico">⌕</span>
					<Suspense fallback={<span/>}>
						<SearchComponent
							value={data.value}
							onSearchChange={handleSearchChange}
							result={data.result}
							searchOnEnter={searchOnEnter}
						/>
					</Suspense>
				</div>
			</nav>

			{/* ── Subnav (shown when active group has children) ── */}
			{activeGroupSubs && (
				<nav className="gp-subnav">
					<span className="gp-subnav-lbl">{_activeGroup.label} /</span>
					{activeGroupSubs.map(sub => (
						<button
							key={sub.id}
							className={data.activeTab === sub.pane ? 'active' : ''}
							onClick={() => setData(prev => ({ ...prev, activeTab: sub.pane }))}
						>
							{sub.label}
						</button>
					))}
				</nav>
			)}

			{/* ═══════════════════════════════════
			    MAIN CONTENT SHELL
			    ═══════════════════════════════════ */}
			<div style={{ maxWidth: '1440px', margin: '0 auto', padding: '20px 28px 60px' }}>

				{/* ── Intelligence stats + sector heatmap ── */}
				<div className="intel-dashboard" style={{ marginBottom: '24px' }}>
					<div className="intel-stats-row">
						<div
							className="intel-stat-card intel-stat-card--red"
							onClick={() => handleFilterClick('high-impact')}
							style={{ cursor: 'pointer' }}
							title="View High Impact articles"
						>
							<div className="intel-stat-circle" style={{ borderColor: 'var(--gp-dn, #c8102e)' }}>
								<span className="intel-stat-value" style={{ color: 'var(--gp-dn, #c8102e)' }}>{stats.highImpact}</span>
							</div>
							<span className="intel-stat-label">High Impact</span>
						</div>
						<div
							className="intel-stat-card intel-stat-card--green"
							onClick={() => handleFilterClick('positive')}
							style={{ cursor: 'pointer' }}
							title="View Positive sentiment articles"
						>
							<div className="intel-stat-circle" style={{ borderColor: 'var(--gp-up, #007f3b)' }}>
								<span className="intel-stat-value" style={{ color: 'var(--gp-up, #007f3b)' }}>{stats.positive}</span>
							</div>
							<span className="intel-stat-label">Positive</span>
						</div>
						<div
							className="intel-stat-card intel-stat-card--blue"
							onClick={() => handleFilterClick('clear')}
							style={{ cursor: 'pointer' }}
							title="View all articles"
						>
							<div className="intel-stat-circle" style={{ borderColor: '#00a3e0' }}>
								<span className="intel-stat-value" style={{ color: '#00a3e0' }}>{stats.total}</span>
							</div>
							<span className="intel-stat-label">Total Articles</span>
						</div>
					</div>

					<div className="heatmap-segment">
						<div className="heatmap-header">
							<span className="heatmap-header-title">SECTOR SENTIMENT</span>
							<span className="heatmap-header-sub">click a tile to filter</span>
						</div>
						<div className="heatmap-grid">
							{Object.keys(heatmap).map(cat => {
								const item = heatmap[cat];
								const meta = CATEGORY_META[cat] || { emoji: '📰', accent: '#607d8b', label: cat };
								const noData = !item.count;
								const isActive = data.currentCategory === cat;
								const sentClass = noData ? '' : item.score > 60 ? ' up' : item.score < 40 ? ' dn' : '';
								return (
									<button
										key={cat}
										className={`heatmap-tile${sentClass}${isActive ? ' active' : ''}${noData ? ' nodata' : ''}`}
										onClick={() => {
											setData(prev => ({ ...prev, currentCategory: cat, activeTab: 2 }));
											loadRSSNews(cat, data.currentCountry);
										}}
									>
										<div className="heatmap-tile__top">
											<span className="heatmap-tile__emoji">{meta.emoji}</span>
											<span className="heatmap-tile__n">{item.count || '—'}</span>
										</div>
										<div className="heatmap-tile__cat">{meta.label}</div>
										<div className="heatmap-tile__score">{noData ? '—' : `${item.score}`}<span className="heatmap-tile__unit">/100</span></div>
										<div className="heatmap-tile__sent">
											{noData ? 'NO DATA' : item.label.toUpperCase()}
										</div>
									</button>
								);
							})}
						</div>
					</div>
				</div>

				{/* ── AI Features row ── */}
				<div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap', padding: '10px 0 16px', borderBottom: '1px solid var(--gp-rule)', marginBottom: '20px' }}>
					<span style={{ fontFamily: 'var(--gp-font-mono)', fontSize: '10px', letterSpacing: '0.16em', textTransform: 'uppercase', color: 'var(--gp-ink-mute)' }}>AI Features</span>
					<Button
						size="small"
						toggle
						active={data.enableDeduplication}
						onClick={() => setData(prev => ({ ...prev, enableDeduplication: !prev.enableDeduplication }))}
						title="Remove duplicate articles from different sources"
					>
						<Icon name="copy outline" /> Dedup
					</Button>
					<Button
						size="small"
						toggle
						active={data.enableClustering}
						onClick={() => setData(prev => ({ ...prev, enableClustering: !prev.enableClustering }))}
						title="Group similar articles together"
					>
						<Icon name="sitemap" /> Cluster
					</Button>
					{data.activeTab === 8 && (
						<div style={{ marginLeft: 'auto' }}>
							<CategoryFilter
								value={data.currentCategory}
								onChange={categoryChange}
							/>
						</div>
					)}
					{(data.enableDeduplication || data.enableClustering) && (
						<Label size="small" color="green" style={{ marginLeft: 'auto' }}>
							<Icon name="check" /> AI Active
						</Label>
					)}
				</div>

				{/* ── Active pane content ── */}
				<div>
					{panes[data.activeTab].render()}
				</div>
			</div>

			{/* ═══════════════════════════════════
			    FOOTER
			    ═══════════════════════════════════ */}
			<footer className="gp-foot">
				<div>© 2026 Predovex · Intelligence Platform</div>
				<div className="gp-foot-mid">Signal preserved. Noise filtered.</div>
				<div className="gp-foot-right">
					<button
						onClick={function() { setData(function(prev) { return Object.assign({}, prev, { showPrivacyPolicy: true }); }); }}
						style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', font: 'inherit', padding: 0 }}
					>
						Privacy
					</button>
					{' · '}
					<span>Not investment advice</span>
				</div>
			</footer>

			{/* Financial disclaimer banner — shown once per device */}
			{!data.disclaimerDismissed && (
				<div style={{
					position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 9998,
					background: '#14110d', color: '#f3ede0',
					padding: '10px 16px', display: 'flex', alignItems: 'center',
					gap: '12px', fontSize: '11px', fontFamily: 'IBM Plex Sans, sans-serif',
					borderTop: '2px solid #c8553d',
				}}>
					<Icon name="warning sign" style={{ color: '#c8553d', flexShrink: 0 }} />
					<span style={{ flex: 1, lineHeight: 1.5 }}>
						<strong>Not investment advice.</strong> Predovex provides ML predictions and market data for informational and educational purposes only. Past model performance does not guarantee future results. Always consult a qualified financial adviser.
					</span>
					<button
						onClick={function() {
							localStorage.setItem('predovex_disclaimer', 'true');
							setData(function(prev) { return Object.assign({}, prev, { disclaimerDismissed: true }); });
						}}
						style={{
							background: '#c8553d', border: 'none', color: '#f3ede0',
							padding: '6px 14px', cursor: 'pointer', flexShrink: 0,
							fontFamily: 'IBM Plex Mono, monospace', fontSize: '10px',
							textTransform: 'uppercase', letterSpacing: '0.08em',
						}}
					>
						Understood
					</button>
				</div>
			)}

			{/* ═══════════════════════════════════
			    MODALS
			    ═══════════════════════════════════ */}
			<LoginModal
				open={data.showLoginModal}
				onClose={() => setData(prev => ({ ...prev, showLoginModal: false }))}
				onLoginSuccess={() => {
					setData(prev => ({
						...prev,
						isLoggedIn: true,
						userTier: localStorage.getItem('tier') || 'free',
						dailyLimit: parseInt(localStorage.getItem('dailyLimit')) || 50,
					}));
					checkAuth();
				}}
			/>
			<RemoveAdsModal
				open={data.showRemoveAdsModal}
				onClose={() => setData(prev => ({ ...prev, showRemoveAdsModal: false }))}
				onSubscribe={handleRemoveAdsSubscribe}
			/>
			<ArticleReader
				article={data.selectedArticleForReading}
				open={data.articleReaderOpen}
				allArticles={data.articles}
				onClose={() => setData(prev => ({ ...prev, articleReaderOpen: false, selectedArticleForReading: null }))}
			/>
			{data.showInterstitial && (
				<AdComponent
					type="interstitial"
					onClose={() => setData(prev => ({ ...prev, showInterstitial: false }))}
				/>
			)}

			{/* Privacy Policy full-screen overlay */}
			{data.showPrivacyPolicy && (
				<div style={{
					position: 'fixed', inset: 0, zIndex: 10000,
					background: 'var(--gp-paper, #f3ede0)',
					overflowY: 'auto',
				}}>
					<Suspense fallback={TabFallback}>
						<PrivacyPolicy onClose={function() { setData(function(prev) { return Object.assign({}, prev, { showPrivacyPolicy: false }); }); }} />
					</Suspense>
				</div>
			)}
		</div>
	);
}

export default App;
