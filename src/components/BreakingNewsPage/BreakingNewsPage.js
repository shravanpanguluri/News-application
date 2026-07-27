import React from 'react';
import { Container, Header, Card, Image, Grid, Segment, Icon, Button, Label } from 'semantic-ui-react';
import './BreakingNewsPage.css';

const BreakingNewsPage = ({ breakingNews = [], onRefresh, lastUpdated, onArticleClick }) => {
	if (!breakingNews || breakingNews.length === 0) {
		return (
			<Container textAlign="center" style={{ padding: '50px 0' }}>
				<Icon name="newspaper" size="huge" color="grey" />
				<Header as="h2" color="grey">No Breaking News</Header>
				<p>Check back later for the latest updates</p>
				<Button onClick={onRefresh} color="blue">
					<Icon name="refresh" /> Refresh
				</Button>
			</Container>
		);
	}

	const formatDate = (dateVal) => {
		const val = dateVal || new Date();
		const d = new Date(val);
		return isNaN(d.getTime()) ? 'Recently' : d.toLocaleString();
	};

	return (
		<Container className="breaking-news-page">
			<Header as="h1" className="breaking-page-header">
				<Icon name="bolt" color="red" />
				Breaking News
				<Label color="red" ribbon>
					LIVE
				</Label>
			</Header>
			
			<div className="breaking-page-meta">
				<span>
					<Icon name="clock" />
					Last updated: {lastUpdated ? formatDate(lastUpdated) : 'Just now'}
				</span>
				<Button onClick={onRefresh} size="small" color="blue" style={{ marginLeft: '15px' }}>
					<Icon name="refresh" /> Refresh Now
				</Button>
			</div>

			<Grid columns={1} mobile={1} tablet={2} computer={3} stackable>
				{breakingNews.map((article, idx) => (
					<Grid.Column key={idx}>
						<Card
							fluid
							className="breaking-news-card"
							style={{ cursor: 'pointer' }}
							onClick={() => onArticleClick && onArticleClick(article)}
						>
							{article.image ? (
								<Image src={article.image} wrapped />
							) : (
								<div className="breaking-news-image-placeholder">
									<Icon name="newspaper" size="huge" />
								</div>
							)}
							<Card.Content>
								<div className="breaking-news-badge">
									<Icon name="bolt" /> BREAKING
								</div>
								<Card.Header>{article.title}</Card.Header>
								<Card.Meta>
									<span className="breaking-news-source">
										<Icon name="building" /> {article.source}
									</span>
									<span className="breaking-news-time">
										<Icon name="time" /> {formatDate(article.published_at || article.publishedAt)}
									</span>
								</Card.Meta>
								<Card.Description>
									{article.description && article.description.length > 150
										? article.description.substring(0, 150) + '...'
										: article.description}
								</Card.Description>
							</Card.Content>
							<Card.Content extra>
								<Button fluid color="red">
									<Icon name="expand" /> View Summary
								</Button>
							</Card.Content>
						</Card>
					</Grid.Column>
				))}
			</Grid>
		</Container>
	);
};

export default BreakingNewsPage;
