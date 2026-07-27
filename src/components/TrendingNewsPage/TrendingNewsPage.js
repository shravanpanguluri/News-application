import React from 'react';
import { Container, Grid, Card, Image, Icon, Segment, Header, Label, Button, Statistic } from 'semantic-ui-react';
import './TrendingNewsPage.css';

const TrendingNewsPage = ({ trendingNews = [], onRefresh, onArticleClick }) => {
	if (!trendingNews || trendingNews.length === 0) {
		return (
			<Container textAlign="center" style={{ padding: '50px 0' }}>
				<Icon name="fire" size="huge" color="orange" />
				<Header as="h2" color="grey">No Trending News</Header>
				<p>Check back later for trending stories</p>
				<Button onClick={onRefresh} color="orange">
					<Icon name="refresh" /> Refresh
				</Button>
			</Container>
		);
	}

	return (
		<Container className="trending-news-container">
			<Header as="h1" className="trending-header">
				<Icon name="fire" color="orange" />
				Trending Now
				<Header.Subheader>
					Most talked about stories right now
				</Header.Subheader>
			</Header>

			<div className="trending-stats">
				<Segment textAlign="center">
					<Grid columns={3} divided>
						<Grid.Column>
							<Statistic label="Trending Stories" value={trendingNews.length} />
						</Grid.Column>
						<Grid.Column>
							<Statistic label="Updated" value="Real-time" />
						</Grid.Column>
						<Grid.Column>
							<Statistic label="Sources" value={getUniqueSources(trendingNews)} />
						</Grid.Column>
					</Grid>
				</Segment>
			</div>

			<Grid columns={1} stackable>
				{trendingNews.map((article, idx) => (
					<Grid.Column key={idx}>
						<TrendingCard 
							article={article} 
							rank={idx + 1} 
							onClick={() => onArticleClick && onArticleClick(article)}
						/>
					</Grid.Column>
				))}
			</Grid>
		</Container>
	);
};

const TrendingCard = ({ article, rank, onClick }) => {
	const isHot = rank <= 5;
	const isRising = rank <= 10;

	return (
		<Card fluid className={`trending-card ${rank <= 3 ? 'top-story' : ''}`} style={{ cursor: 'pointer' }} onClick={onClick}>
			<Card.Content>
				<div className="trending-rank">
					<div className={`rank-badge ${isHot ? 'hot' : isRising ? 'rising' : ''}`}>
						#{rank}
					</div>
					{isHot && (
						<Label color="red" size="small" ribbon>
							<Icon name="fire" /> HOT
						</Label>
					)}
				</div>

				{article.image ? (
					<Image
						src={article.image}
						wrapped
						alt={article.title}
						className="trending-image"
					/>
				) : (
					<div className="trending-image-placeholder">
						<Icon name="newspaper" size="huge" />
					</div>
				)}

				<Card.Header className="trending-title">
					{article.title}
				</Card.Header>

				<Card.Meta className="trending-meta">
					<span className="source">
						<Icon name="building" /> {article.source}
					</span>
					<span className="time">
						<Icon name="time" /> {getTimeAgo(article.published_at || article.publishedAt)}
					</span>
					{article.category && (
						<Label size="tiny" color="teal">
							{article.category}
						</Label>
					)}
				</Card.Meta>

				<Card.Description className="trending-description">
					{article.description && article.description.length > 150
						? article.description.substring(0, 150) + '...'
						: article.description}
				</Card.Description>

				{article.content && (
					<div className="trending-content-preview">
						<Icon name="file text outline" />
						<span>{getWordCount(article.content)} words</span>
					</div>
				)}
			</Card.Content>

			<Card.Content extra>
				<div className="trending-actions">
					<Button
						color="orange"
						fluid
					>
						<Icon name="expand" /> View Summary
					</Button>
				</div>
			</Card.Content>
		</Card>
	);
};

// Helper functions
function getTimeAgo(dateVal) {
	if (!dateVal) return 'Recently';
	const date = new Date(dateVal);
	if (isNaN(date.getTime())) return 'Recently';
	
	const seconds = Math.floor((new Date() - date) / 1000);
	
	if (seconds < 60) return 'Just now';
	if (seconds < 0) return 'Just now';
	if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
	if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
	return `${Math.floor(seconds / 86400)}d ago`;
}

function getUniqueSources(articles) {
	const sources = new Set(articles.map(a => a.source));
	return sources.size;
}

function getWordCount(content) {
	return content.split(/\s+/).length;
}

export default TrendingNewsPage;
