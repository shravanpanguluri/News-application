import React, { useState, useEffect, memo } from 'react';
import { Pagination, Label, Icon } from 'semantic-ui-react';
import NewsCardSkeleton from './NewsCardSkeleton';
import { sanitizeArticleText } from '../../utils/textSanitizer';
import './NewsCards.css';

function hapticLight() {
	try {
		import('@capacitor/haptics').then(function(m) {
			m.Haptics.impact({ style: m.ImpactStyle.Light }).catch(function() {});
		}).catch(function() {});
	} catch (e) {}
}

function hapticMedium() {
	try {
		import('@capacitor/haptics').then(function(m) {
			m.Haptics.impact({ style: m.ImpactStyle.Medium }).catch(function() {});
		}).catch(function() {});
	} catch (e) {}
}

const STORAGE_KEY = 'predovex_bookmarks';
const AI_CACHE_KEY = 'predovex_ai_cache';

// AI Cache to avoid re-analyzing same articles
function getAiCache() {
	try { return JSON.parse(localStorage.getItem(AI_CACHE_KEY) || '{}'); }
	catch (e) { return {}; }
}

function saveAiCache(cache) {
	try { localStorage.setItem(AI_CACHE_KEY, JSON.stringify(cache)); } catch (e) {}
}

function getBookmarks() {
	try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }
	catch (e) { return []; }
}

// Memoize component to prevent unnecessary re-renders
export default memo(function NewsCards(props) {
	const [currentPage, setCurrentPage] = useState(1);
	const [bookmarks, setBookmarks] = useState(getBookmarks);
	const [aiAnalysis, setAiAnalysis] = useState({});
	const [aiLoading, setAiLoading] = useState(false);
	const [aiFeaturesLoaded, setAiFeaturesLoaded] = useState(false);
	const [tldrMap, setTldrMap] = useState({});
	const [tldrLoading, setTldrLoading] = useState({});
	const articlesPerPage = 9;

	const handleTldr = async function(e, article) {
		e.preventDefault();
		e.stopPropagation();
		var key = article.url || article.title;
		if (tldrMap[key]) {
			// toggle off
			setTldrMap(function(prev) { var n = Object.assign({}, prev); delete n[key]; return n; });
			return;
		}
		setTldrLoading(function(prev) { var n = Object.assign({}, prev); n[key] = true; return n; });
		try {
			var BACKEND_URL = (function() {
				if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') return 'http://127.0.0.1:8000';
				return 'https://predovex-application.onrender.com';
			})();
			var res = await fetch(BACKEND_URL + '/api/article/summarize?title=' + encodeURIComponent(article.title || '') + '&content=' + encodeURIComponent((article.description || '') + ' ' + (article.content || '')));
			var data = await res.json();
			if (data.summary) {
				setTldrMap(function(prev) { var n = Object.assign({}, prev); n[key] = data.summary; return n; });
			}
		} catch (ex) {}
		setTldrLoading(function(prev) { var n = Object.assign({}, prev); delete n[key]; return n; });
	};

	// Lazy load AI features only when needed (performance optimization)
	useEffect(() => {
		if (!props.articles || props.articles.length === 0) return;
		
		// Load AI utilities dynamically (don't block initial render)
		const loadAiFeatures = async () => {
			try {
				const { readingLevelAnalyzer, clickbaitDetector, fakeNewsDetector } = await import('../../utils/aiUtils');
				setAiFeaturesLoaded(true);
				
				// Analyze articles with caching
				analyzeArticlesWithCache(
					props.articles.slice(0, 5),
					readingLevelAnalyzer,
					clickbaitDetector,
					fakeNewsDetector
				).catch(function(e) { console.error('AI analysis failed:', e); });
			} catch (error) {
				console.error('Failed to load AI features:', error);
			}
		};
		
		loadAiFeatures();
	}, [props.articles]);

	// Analyze articles with caching
	const analyzeArticlesWithCache = async (articles, readingLevelAnalyzer, clickbaitDetector, fakeNewsDetector) => {
		setAiLoading(true);
		const cache = getAiCache();
		const analysis = {};
		let cacheHits = 0;
		
		for (const article of articles) {
			const url = article.url || article.internalTrackingUrl;
			const articleHash = url ? btoa(url).substring(0, 20) : null;
			
			// Check cache first (valid for 24 hours)
			if (articleHash && cache[articleHash] && (Date.now() - cache[articleHash].timestamp) < 86400000) {
				analysis[url] = cache[articleHash].data;
				cacheHits++;
				continue;
			}
			
			// Analyze article
			const readingLevel = readingLevelAnalyzer.analyze(article);
			const clickbait = await clickbaitDetector.detect(article.title);
			const credibility = await fakeNewsDetector.detect(article);
			
			analysis[url] = { readingLevel, clickbait, credibility };
			
			// Save to cache
			if (articleHash) {
				cache[articleHash] = {
					data: analysis[url],
					timestamp: Date.now()
				};
			}
		}
		
		setAiAnalysis(analysis);
		setAiLoading(false);
		saveAiCache(cache);
		console.log(`✅ AI Analysis: ${cacheHits}/${articles.length} from cache, ${articles.length - cacheHits} analyzed`);
	};

	const handleCardClick = (e, article) => {
		if (e) { e.preventDefault(); e.stopPropagation(); }
		hapticLight();
		if (props.onArticleClick) props.onArticleClick(article);
	};

	const toggleBookmark = (e, article) => {
		e.preventDefault();
		e.stopPropagation();
		hapticMedium();
		const isBookmarked = bookmarks.some(function(b) { return b.url === article.url; });
		const updated = isBookmarked
			? bookmarks.filter(function(b) { return b.url !== article.url; })
			: [article].concat(bookmarks);
		setBookmarks(updated);
		localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
		if (props.onBookmarkChange) props.onBookmarkChange(updated);
	};

	const isBookmarked = function(article) {
		return bookmarks.some(function(b) { return b.url === article.url; });
	};

	const safeFormatDate = (dateVal) => {
		if (!dateVal) return 'Recently';
		try {
			const d = new Date(dateVal);
			return isNaN(d.getTime()) ? 'Recently' : d.toLocaleDateString();
		} catch (e) { return 'Recently'; }
	};

	// Show skeletons while loading
	if (props.loading) {
		return (
			<div className="news-container">
				<div className="news-grid">
					{[1,2,3,4,5,6,7,8,9].map(function(i) {
						return <NewsCardSkeleton key={i} />;
					})}
				</div>
			</div>
		);
	}

	const totalArticles = props.articles ? props.articles.length : 0;
	const totalPages    = Math.ceil(totalArticles / articlesPerPage);
	const indexOfLast   = currentPage * articlesPerPage;
	const indexOfFirst  = indexOfLast - articlesPerPage;
	const currentArticles = props.articles
		? props.articles.slice(indexOfFirst, indexOfLast)
		: [];

	const handlePageChange = (e, { activePage }) => {
		setCurrentPage(activePage);
		window.scrollTo({ top: 0, behavior: 'smooth' });
	};

	return (
		<div className="news-container">
			<div className="news-grid">
				{currentArticles && currentArticles.length > 0
					? currentArticles.map((article, idx) => (
						(() => {
							var title = sanitizeArticleText(article.title, 'Untitled');
							var description = sanitizeArticleText(article.description);
							var sourceValue = article.source && typeof article.source === 'object' ? article.source.name : article.source;
							var source = sanitizeArticleText(article.sourceLabel || sourceValue, 'Predovex Intelligence');
							var tldrKey = article.url || article.title;
							var tldr = sanitizeArticleText(tldrMap[tldrKey]);

							return (
						<div
							key={idx}
							className="news-card-wrapper"
							onClick={(e) => handleCardClick(e, article)}
							style={{ maxWidth: '100%', overflow: 'hidden', cursor: 'pointer' }}
						>
							<div className="news-card-image">
								{article.image || article.urlToImage ? (
									<img
										src={article.image || article.urlToImage}
										alt={title}
										style={{ width: '100%', height: '180px', objectFit: 'cover' }}
										loading="lazy"  // Native lazy loading
										decoding="async"  // Async decoding for better performance
									/>
								) : (
									<div className="news-card-image-placeholder">
										<i className="newspaper icon" style={{ fontSize: '48px', color: 'white' }}></i>
									</div>
								)}

								{/* Impact badge */}
								{article.impact_level && (
									<span className={'impact-badge impact-badge--' + article.impact_level.toLowerCase()}>
										{article.impact_level}
									</span>
								)}

								{/* Bookmark button */}
								        <button
								              className={'bookmark-btn' + (isBookmarked(article) ? ' bookmark-btn--active' : '')}
								              onClick={(e) => toggleBookmark(e, article)}
								              title={isBookmarked(article) ? 'Remove bookmark' : 'Save article'}
								        >
								              <i className={'bookmark' + (isBookmarked(article) ? '' : ' outline') + ' icon'} />
								        </button>
								</div>

								<div className="news-card-content" style={{ borderTop: article.isSponsored ? '4px solid #f1c40f' : 'none' }}>
								        {article.isSponsored && (
								              <Label color="yellow" size="mini" style={{ marginBottom: '10px' }}>
								              <Icon name="star" /> SPONSORED CONTENT
								              </Label>
								        )}
								        
								        {/* AI Analysis Badges */}
								        {aiAnalysis[article.url || article.internalTrackingUrl] && (
								        	<div style={{ marginBottom: '10px', display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
								        		{/* Reading Level Badge */}
								        		{(() => {
								        			const rl = aiAnalysis[article.url || article.internalTrackingUrl].readingLevel;
								        			return (
								        				<Label size="mini" style={{ background: rl.level.color, color: 'white' }} title={`Read time: ${rl.readTime} min`}>
								        					<Icon name="book" /> {rl.level.label} ({rl.readTime}m)
								        				</Label>
								        			);
								        		})()}
								        		
								        		{/* Clickbait Warning */}
								        		{(() => {
								        			const cb = aiAnalysis[article.url || article.internalTrackingUrl].clickbait;
								        			if (cb.isClickbait || cb.score > 50) {
								        				return (
								        					<Label size="mini" color="orange" title={`Clickbait score: ${cb.score}%`}>
								        						<Icon name="warning" /> Sensational
								        					</Label>
								        				);
								        			}
								        			return null;
								        		})()}
								        		
								        		{/* Credibility Score */}
								        		{(() => {
								        			const cred = aiAnalysis[article.url || article.internalTrackingUrl].credibility;
								        			return (
								        				<Label size="mini" color={cred.color} title={`${cred.label} (${cred.credibilityScore}/100)`}>
								        					<Icon name={cred.credibilityScore >= 70 ? 'check circle' : 'warning'} /> {cred.credibilityScore}/100
								        				</Label>
								        			);
								        		})()}
								        	</div>
								        )}
								        {aiLoading && (
								        	<Label size="mini" color="grey">
								        		<Icon name="spinner" loading /> AI Analyzing...
								        	</Label>
								        )}
								        
								        <h3 className="news-card-title">
								              {title.length > 55
								              ? title.substr(0, 55) + '...'
								              : title}
								        </h3>

								{description && !tldr && (
									<p className="news-card-description">
										{description.length > 95
											? description.substr(0, 95) + '...'
											: description}
									</p>
								)}
								{tldr && (
									<p className="news-card-tldr">
										<span className="news-card-tldr-badge">TLDR</span>
										{tldr}
									</p>
								)}
								<div className="news-card-meta">
									<span className="news-card-source">
										<Icon name="shield" color="red" size="small" />
										{source}
									</span>
									<span className="news-card-date">
										{safeFormatDate(article.published_at || article.publishedAt)}
									</span>
									{article.predovexID && (
										<span className="news-card-id" style={{ fontSize: '10px', color: '#999', marginLeft: '8px' }}>
											{article.predovexID}
										</span>
									)}
									<button
										className={'news-card-tldr-btn' + (tldrMap[article.url || article.title] ? ' news-card-tldr-btn--active' : '')}
										onClick={function(e) { handleTldr(e, article); }}
										disabled={!!tldrLoading[article.url || article.title]}
										title="AI TLDR summary"
									>
										{tldrLoading[article.url || article.title] ? '…' : 'TLDR'}
									</button>
								</div>
							</div>
						</div>
							);
						})()
					))
					: <p style={{ textAlign: 'center', gridColumn: '1/-1', color: '#666' }}>No articles available</p>
				}
			</div>

			{totalPages > 1 && (
				<div className="pagination-container">
					<Pagination
						activePage={currentPage}
						onPageChange={handlePageChange}
						totalPages={totalPages}
						size="large"
						secondary
						pointing
					/>
					<p className="pagination-info">
						Page {currentPage} of {totalPages} | Showing {currentArticles.length} of {totalArticles} articles
					</p>
				</div>
			)}
		</div>
	);
});
