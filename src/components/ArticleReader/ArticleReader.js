import React, { useState, useEffect } from 'react';
import { Modal, Header, Button, Icon, Segment, Loader, Divider, List, Grid, Statistic, Label } from 'semantic-ui-react';
import { narrativeDNA } from '../../utils/narrativeDNA';
import { BACKEND_URL } from '../../API/governmentApi';
import './ArticleReader.css';

const ArticleReader = ({ article, open, onClose, allArticles }) => {
	const [articleData, setArticleData] = useState(null);
	const [loading, setLoading] = useState(false);
	const [aiGenes, setAiGenes] = useState(null);
	const [analyzing, setAnalyzing] = useState(false);
	const [userTier, setUserTier] = useState(localStorage.getItem('tier') || 'free');

	useEffect(() => {
		if (open && article) {
			if (article.url) {
				fetchIntelligenceBrief(article.url);
			} else {
				setArticleData({ success: false, fallback: true });
			}
			runAIAnalysis(article);
			setUserTier(localStorage.getItem('tier') || 'free');
		} else if (!open) {
			setArticleData(null);
			setAiGenes(null);
		}
	}, [open, article]);

	const runAIAnalysis = async (art) => {
		setAnalyzing(true);
		try {
			const text = art.content || art.description || art.ai_summary || art.title;
			const genes = await narrativeDNA.extractGenes(text, art.title);
			setAiGenes(genes);
		} catch (err) {
			console.error('AI Analysis failed:', err);
		} finally {
			setAnalyzing(false);
		}
	};

	const fetchIntelligenceBrief = async (url) => {
		setLoading(true);
		try {
			const response = await fetch(`${BACKEND_URL}/article/fetch?url=${encodeURIComponent(url)}`);
			const data = await response.json();
			setArticleData(data);
		} catch (err) {
			console.error('Error fetching intelligence brief:', err);
			setArticleData({ success: false, fallback: true });
		} finally {
			setLoading(false);
		}
	};

	if (!article) return null;

	const isDarkMode = document.body.parentElement.classList.contains('dark-mode') || document.querySelector('.dark-mode');
	const hasIntelBrief = !!(articleData && articleData.intel_brief);
	const showArticleBodyView = false;
	const articleBody = article.content || article.description || '';
	const articleSummary = article.ai_summary && article.ai_summary !== 'Summary unavailable.' ? article.ai_summary : article.description;
	const extractedParagraphs = hasIntelBrief && Array.isArray(articleData.intel_brief.full_reconstructed_report)
		? articleData.intel_brief.full_reconstructed_report
		: [];
	const sourceParagraphs = extractedParagraphs.length > 0
		? extractedParagraphs
		: (articleBody || article.description || article.title || '')
			.split(/\n+/)
			.map(function(para) { return para.trim(); })
			.filter(function(para) { return para.length > 0; });
	const analysisText = sourceParagraphs.join(' ');
	const sourceSentences = analysisText
		.split(/(?<=[.!?])\s+/)
		.map(function(sentence) { return sentence.trim(); })
		.filter(function(sentence) { return sentence.length > 35; });
	const executiveSummary = (articleData && articleData.intel_brief && articleData.intel_brief.executive_summary) ||
		(articleSummary && articleSummary !== 'Summary unavailable.' ? articleSummary : null) ||
		sourceSentences[0] ||
		article.title;
	const criticalInsights = (articleData && articleData.intel_brief && articleData.intel_brief.critical_insights && articleData.intel_brief.critical_insights.length > 0)
		? articleData.intel_brief.critical_insights
		: (sourceSentences.length > 0 ? sourceSentences.slice(0, 5) : [executiveSummary]);
	const contextualBrief = (articleData && articleData.intel_brief && articleData.intel_brief.contextual_brief) ||
		[
			`Predovex is analyzing this report as a ${article.category || 'general'} intelligence signal from ${article.source || 'the source publication'}.`,
			analysisText
				? `The available article text points to operational, market, policy, or reputational implications that should be monitored as the story develops.`
				: `The source did not expose full body text locally, so this analysis is based on the article metadata and summary available in the feed.`
		].join('\n\n');
	const strategicOutlook = (articleData && articleData.intel_brief && articleData.intel_brief.strategic_outlook) ||
		`Predovex will continue monitoring this story for follow-on developments, actor responses, and second-order market or policy effects.`;
	const framingConfidence = aiGenes && aiGenes.framing && Number.isFinite(aiGenes.framing.confidence)
		? Math.round(aiGenes.framing.confidence * 100)
		: 72;

	return (
		<Modal open={open} onClose={onClose} size="large" closeIcon className={`intel-reader-modal ${isDarkMode ? 'dark' : ''}`}>
			<Modal.Header style={{ background: 'var(--gp-ink, #1a1a18)', color: 'var(--gp-paper, #fdfaf5)', borderBottom: 'none' }}>
				<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
					<span>
						<Icon name="shield" color="red" />
						PREDOVEX INTELLIGENCE REPORT [CONFIDENTIAL]
					</span>
					<Label color="red" basic={!isDarkMode} inverted={isDarkMode}>LIVE ANALYSIS</Label>
				</div>
			</Modal.Header>
			
			<Modal.Content scrolling style={{ background: 'var(--gp-paper, #fdfaf5)', color: 'var(--gp-ink, #1a1a18)' }}>
				<div style={{ textAlign: 'center', marginBottom: '20px', borderBottom: `2px double ${isDarkMode ? '#333' : '#eee'}`, paddingBottom: '10px' }}>
					<Header as="h1" style={{ fontSize: '2.5rem', textTransform: 'uppercase', letterSpacing: '1px', color: isDarkMode ? 'white' : 'inherit' }}>
						{article.title}
					</Header>
					<div style={{ color: 'var(--gp-ink-mute, #888)', fontWeight: 'bold' }}>
						OFFICE OF STRATEGIC INTELLIGENCE | REPORT ID: {Math.random().toString(36).substr(2, 9).toUpperCase()}
					</div>
				</div>

				{loading ? (
					<div style={{ padding: '100px', textAlign: 'center' }}>
						<Loader active inline="centered" size="huge" inverted={isDarkMode}>PROCESSING INTELLIGENCE...</Loader>
					</div>
				) : showArticleBodyView ? (
					/* ── RSS-based article view when full fetch fails ── */
					<div>
						{/* Hero image */}
						{(article.image || article.urlToImage) && (
							<div style={{ width: '100%', maxHeight: '340px', overflow: 'hidden', borderRadius: '8px', marginBottom: '24px' }}>
								<img
									src={article.image || article.urlToImage}
									alt={article.title}
									style={{ width: '100%', height: '340px', objectFit: 'cover', display: 'block' }}
									onError={function(e) { e.target.style.display = 'none'; }}
								/>
							</div>
						)}

						{/* Source + date bar */}
						<div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '18px', flexWrap: 'wrap' }}>
							<Label style={{ background: 'var(--gp-ink, #1a1a18)', color: 'var(--gp-paper, #fdfaf5)', borderRadius: '0', fontSize: '11px', fontWeight: 700, letterSpacing: '0.5px' }}>
								{article.source || 'News Source'}
							</Label>
							{article.published_at && (
								<span style={{ color: 'var(--gp-ink-mute, #888)', fontSize: '13px' }}>
									<Icon name="clock outline" />
									{new Date(article.published_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
								</span>
							)}
							<span style={{ marginLeft: 'auto', color: 'var(--gp-ink-mute, #888)', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}>
								<Icon name="shield alternate" size="small" /> Predovex Portal View
							</span>
						</div>

						{/* Article body content */}
						{articleBody && (
							<div style={{
								fontSize: '16px',
								lineHeight: '1.85',
								color: 'var(--gp-ink, #1a1a18)',
								marginBottom: '24px',
								borderLeft: '3px solid var(--gp-accent, #c8553d)',
								paddingLeft: '20px',
							}}>
								<Header as="h3" style={{ color: 'var(--gp-ink, #1a1a18)', marginBottom: '14px' }}>
									<Icon name="newspaper outline" /> FULL STORY
								</Header>
								{articleBody.split(/\n+/).map(function(para, i) {
									return para.trim().length > 0
										? <p key={i} style={{ margin: '0 0 14px 0' }}>{para.trim()}</p>
										: null;
								})}
							</div>
						)}

						{/* AI Summary section */}
						{articleSummary && (
							<Segment style={{
								background: 'var(--gp-rule, rgba(0,0,0,0.04))',
								border: '1px solid var(--gp-rule-2, #d8d0c0)',
								borderLeft: '4px solid var(--gp-accent, #c8553d)',
								borderRadius: '0',
								marginBottom: '20px'
							}}>
								<Header as="h5" style={{ color: 'var(--gp-accent, #c8553d)', marginBottom: '8px' }}>
									<Icon name="lightbulb outline" /> AI Summary
								</Header>
								<p style={{ color: isDarkMode ? '#b8d0e8' : '#3a4f63', lineHeight: '1.7', margin: 0 }}>
									{articleSummary}
								</p>
							</Segment>
						)}

						{/* View original link */}
						<div style={{ textAlign: 'right', paddingTop: '12px', borderTop: '1px solid var(--gp-rule-2, #d8d0c0)' }}>
							<span style={{ color: 'var(--gp-ink-mute, #888)', fontSize: '12px', marginRight: '12px' }}>
								<Icon name="info circle" size="small" /> Portal view — some content may be abbreviated
							</span>
							<Button
								size="small"
								style={{ background: 'transparent', color: 'var(--gp-accent, #c8553d)', border: '1px solid var(--gp-accent, #c8553d)', borderRadius: '0' }}
								onClick={function() { window.open(article.url, '_blank'); }}
							>
								<Icon name="external alternate" /> Full Article
							</Button>
						</div>
					</div>
				) : (
					<div className="intel-content">
						{/* Executive Summary */}
						<Segment raised color="black" style={{ borderLeft: '10px solid var(--gp-ink, #1a1a18)', background: 'var(--gp-paper, #fdfaf5)', color: 'var(--gp-ink, #1a1a18)' }}>
							<Header as="h2" inverted={isDarkMode}>
								<Icon name="file alternate outline" />
								FULL ANALYSIS
							</Header>
							<p style={{ fontSize: '1.2rem', lineHeight: '1.8', color: isDarkMode ? '#ccc' : '#333' }}>
								{executiveSummary}
							</p>
							<p style={{ fontSize: '1rem', lineHeight: '1.7', color: isDarkMode ? '#aaa' : '#555', marginTop: '12px' }}>
								{contextualBrief}
							</p>
						</Segment>

						<Divider horizontal inverted={isDarkMode}>
							<Header as="h4" inverted={isDarkMode}><Icon name="search" /> ANALYST FINDINGS</Header>
						</Divider>

						{/* Premium Intelligence - Powered by AI */}
						<div style={{ marginTop: '30px' }}>
							<Header as="h3" color="purple" dividing>
								<Icon name="diamond" /> 
								AI-POWERED PREMIUM INTELLIGENCE
								{userTier === 'free' && <Label color="yellow" size="mini" style={{ marginLeft: '10px' }}>PRO ONLY</Label>}
							</Header>

							{analyzing ? (
								<Loader active inline="centered">Generating Strategic Narrative DNA...</Loader>
							) : aiGenes ? (
								<div style={{ filter: userTier === 'free' ? 'blur(4px)' : 'none', pointerEvents: userTier === 'free' ? 'none' : 'auto', transition: 'all 0.5s ease' }}>
									<Grid stackable columns={3}>
										<Grid.Column>
											<Segment tertiary inverted={isDarkMode} color="purple">
												<Header as="h4"><Icon name="eye" /> Strategic Framing</Header>
												<div style={{ textTransform: 'capitalize', fontSize: '1.2rem', fontWeight: 'bold' }}>
													{aiGenes.framing.primary} Perspective
												</div>
												<p style={{ opacity: 0.8, fontSize: '0.9rem' }}>
													The narrative is currently dominated by {aiGenes.framing.primary} considerations, showing high confidence in this framing ({framingConfidence}%).
												</p>
											</Segment>
										</Grid.Column>
										<Grid.Column>
											<Segment tertiary inverted={isDarkMode} color="blue">
												<Header as="h4"><Icon name="smile outline" /> Key Actor Sentiment</Header>
												<Statistic size="mini" color={aiGenes.sentiment.score > 0 ? 'green' : 'red'} inverted={isDarkMode}>
													<Statistic.Value>{aiGenes.sentiment.score.toFixed(2)}</Statistic.Value>
													<Statistic.Label>{aiGenes.sentiment.score > 0 ? 'OPTIMISTIC' : 'CONCERNED'}</Statistic.Label>
												</Statistic>
												<p style={{ opacity: 0.8, fontSize: '0.9rem' }}>
													Sentiment intensity: {Math.round(aiGenes.sentiment.magnitude * 100)}%
												</p>
											</Segment>
										</Grid.Column>
										<Grid.Column>
											<Segment tertiary inverted={isDarkMode} color="orange">
												<Header as="h4"><Icon name="lightbulb" /> Strategic Action</Header>
												<p style={{ fontSize: '1rem', fontWeight: 'bold' }}>
													{aiGenes.framing.primary === 'economic' ? 'Hedge against volatility' : 
													 aiGenes.framing.primary === 'security' ? 'Review geopolitical exposure' : 
													 'Monitor for policy shifts'}
												</p>
												<p style={{ opacity: 0.8, fontSize: '0.9rem' }}>
													AI Recommendation based on {aiGenes.emotionalTone} tone detected in report.
												</p>
											</Segment>
										</Grid.Column>
									</Grid>
								</div>
							) : null}

							{userTier === 'free' && (
								<div style={{
									background: 'rgba(0,0,0,0.05)',
									padding: '30px',
									borderRadius: '12px',
									textAlign: 'center',
									marginTop: '-120px',
									position: 'relative',
									zIndex: 10,
									backdropFilter: 'blur(2px)'
								}}>
									<Icon name="lock" size="large" color="yellow" />
									<Header as="h3">Upgrade to Pro for AI Intelligence</Header>
									<p>Unlock deep-dive narrative analysis, actor sentiment, and strategic recommendations for this report.</p>
									<Button 
										color="yellow" 
										onClick={() => {
											localStorage.setItem('tier', 'pro');
											localStorage.setItem('hasPremium', 'true');
											setUserTier('pro');
											alert('🎉 Premium access activated! Enjoy full AI intelligence features.');
										}}
									>
										Upgrade Now (Free Beta)
									</Button>
								</div>
							)}
						</div>

						{/* Critical Insights */}

						<Grid stackable columns={2}>
							<Grid.Column width={10}>
								<Header as="h3" dividing inverted={isDarkMode}>CRITICAL ANALYTICS</Header>
								<List bulleted size="large" style={{ lineHeight: '2', color: isDarkMode ? '#bbb' : 'inherit' }}>
									{(() => {
										return criticalInsights.slice(0, 5).map((s, i) => (
											<List.Item key={i} style={{ marginBottom: '10px' }}>{s.trim()}</List.Item>
										));
									})()}
								</List>
								
								<div style={{ marginTop: '30px', padding: '20px', background: isDarkMode ? 'rgba(255,255,255,0.03)' : '#f4f7f9', borderRadius: '12px', border: `1px solid ${isDarkMode ? '#333' : '#e1e8ed'}` }}>
									<Header as="h4" style={{ color: 'var(--gp-accent, #c8553d)', marginBottom: '15px', textTransform: 'uppercase', letterSpacing: '1px' }}>
										<Icon name="info circle" /> Analyst's Contextual Briefing
									</Header>
									<div style={{ fontSize: '1.1rem', lineHeight: '1.7', color: isDarkMode ? '#bbb' : '#444', whiteSpace: 'pre-wrap' }}>
										{contextualBrief}
									</div>
								</div>
							</Grid.Column>
							<Grid.Column width={6}>
								<Segment color="red" secondary inverted={isDarkMode}>
									<Header as="h4" inverted={isDarkMode}><Icon name="warning sign" /> RISK ASSESSMENT</Header>
									<Statistic size="mini" color={article.impact_level === 'High' ? 'red' : 'orange'} inverted={isDarkMode}>
										<Statistic.Value>{article.impact_level ? article.impact_level.toUpperCase() : 'LOW'}</Statistic.Value>
										<Statistic.Label>PROBABILITY OF IMPACT</Statistic.Label>
									</Statistic>
								</Segment>
							</Grid.Column>
						</Grid>

						{/* Strategic Outlook */}
						<Segment tertiary style={{ marginTop: '30px', borderTop: '4px solid var(--gp-accent, #c8553d)' }}>
							<Header as="h3" color="blue" inverted={isDarkMode}>
								<Icon name="external alternate" />
								STRATEGIC OUTLOOK
							</Header>
							<p style={{ fontSize: '1.1rem', fontStyle: 'italic' }}>
								{strategicOutlook}
							</p>
						</Segment>

						<div style={{ marginTop: '40px', textAlign: 'center', opacity: 0.5 }}>
							<Divider inverted={isDarkMode} />
							<p style={{ color: isDarkMode ? '#888' : 'inherit' }}>PREPARED PROACTIVELY BY PREDOVEX ANALYSIS BUREAU</p>
							<Button 
								basic 
								inverted={isDarkMode}
								size="mini" 
								onClick={() => window.open(article.url, '_blank')}
							>
								VIEW RAW SOURCE DATA
							</Button>
						</div>
					</div>
				)}
			</Modal.Content>
		</Modal>
	);
};

export default ArticleReader;
