import React from 'react';
import { Card, Image, Button, Label, Icon } from 'semantic-ui-react';
import moment from 'moment';

const GovernmentNewsCard = ({ article, onClick }) => {
	const getCountryFlag = countryCode => {
		const flags = {
			in: '🇮🇳',
			us: '🇺🇸',
		};
		return flags[countryCode] || '🌐';
	};

	const getSourceColor = source => {
		const colors = {
			pib: 'orange',
			federal_register: 'blue',
			govinfo: 'green',
			data_gov_in: 'red',
		};
		return colors[source] || 'grey';
	};

	const getImpactColor = score => {
		if (score >= 7) return 'red';
		if (score >= 4) return 'orange';
		return 'green';
	};

	const getImpactLevelColor = level => {
		const colors = {
			High: 'red',
			Medium: 'orange',
			Low: 'green',
		};
		return colors[level] || 'grey';
	};

	const getSentimentColor = sentiment => {
		const colors = {
			Positive: 'green',
			Negative: 'red',
			Neutral: 'blue',
		};
		return colors[sentiment] || 'grey';
	};

	const getSentimentIcon = sentiment => {
		const icons = {
			Positive: 'thumbs up',
			Negative: 'thumbs down',
			Neutral: 'info circle',
		};
		return icons[sentiment] || 'info';
	};

	const calculateReadTime = text => {
		const wordsPerMinute = 200;
		const words = text ? text.split(/\s+/).length : 0;
		const minutes = Math.ceil(words / wordsPerMinute);
		return minutes || 1;
	};

	const formatDate = date => {
		// Handle different date field names
		const dateVal = date || article.publishedAt || article.published_at;
		if (!dateVal) return 'Just now';
		const m = moment(dateVal);
		return m.isValid() ? m.fromNow() : 'Recently';
	};

	const handleCardClick = (e) => {
		if (e) e.preventDefault();
		if (onClick) onClick(article);
	};

	return (
		<Card 
			fluid 
			onClick={handleCardClick}
			style={{ 
				marginBottom: '25px', 
				border: '1px solid rgba(255, 255, 255, 0.3)',
				background: 'rgba(255, 255, 255, 0.8)',
				backdropFilter: 'blur(10px)',
				boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.1)',
				borderRadius: '12px',
				cursor: 'pointer'
			}}
		>
			<Card.Content>
				<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
					<div style={{ flex: 1 }}>
						{/* Country Flag and Source */}
						<div style={{ marginBottom: '12px', display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
							<Label size="small" color="red">
								<Icon name="shield" />
								GOVPULSE INTELLIGENCE
							</Label>
							<Label size="small">
								{getCountryFlag(article.country)} {(article.country || 'Global').toUpperCase()}
							</Label>
							<Label size="small" color="grey" basic>
								<Icon name="wait" /> {calculateReadTime(article.description + (article.ai_summary || ""))} min read
							</Label>
							{article.impact_level && (
								<Label
									size="small"
									color={getImpactLevelColor(article.impact_level)}
									style={{ marginLeft: '5px' }}
								>
									<Icon name="diamond" />
									{article.impact_level} Impact
								</Label>
							)}
							{article.sentiment && (
								<Label
									size="small"
									color={getSentimentColor(article.sentiment)}
									style={{ marginLeft: '5px' }}
								>
									<Icon name={getSentimentIcon(article.sentiment)} />
									{article.sentiment}
								</Label>
							)}
						</div>

						{/* Title */}
						<Card.Header
							style={{
								fontSize: '1.2rem',
								color: '#2185d0',
								marginBottom: '10px',
								display: 'block',
							}}
						>
							{article.title}
						</Card.Header>

						{/* Description */}
						{article.description && (
							<Card.Description
								style={{
									color: '#666',
									marginBottom: '15px',
									lineHeight: '1.6',
								}}
							>
								{article.description.length > 300
									? `${article.description.substring(0, 300)}...`
									: article.description}
							</Card.Description>
						)}

						{/* AI Summary */}
						{article.ai_summary && (
							<div
								style={{
									background: '#f0f7ff',
									padding: '12px',
									borderRadius: '8px',
									marginBottom: '15px',
									borderLeft: '4px solid #2185d0',
								}}
							>
								<div style={{ fontWeight: 'bold', color: '#2185d0', marginBottom: '5px' }}>
									<Icon name="lightbulb" /> Smart Summary
								</div>
								<div style={{ color: '#444', fontStyle: 'italic', fontSize: '0.95rem', whiteSpace: 'pre-line' }}>
									{article.ai_summary}
								</div>
							</div>
						)}

						{/* Tags */}
						{article.tags && article.tags.length > 0 && (
							<div style={{ marginBottom: '10px' }}>
								{article.tags.slice(0, 5).map((tag, index) => (
									<Label key={index} size="tiny" color="teal">
										{tag}
									</Label>
								))}
							</div>
						)}

						{/* Metadata */}
						<div
							style={{
								display: 'flex',
								justifyContent: 'space-between',
								alignItems: 'center',
								fontSize: '0.9rem',
								color: '#999',
							}}
						>
							<span>
								<Icon name="calendar" />
								{formatDate(article.published_at)}
							</span>
							<span>
								<Icon name="folder" />
								{article.category}
							</span>
						</div>
					</div>
				</div>
			</Card.Content>

			<Card.Content extra>
				<Button
					color="blue"
					fluid
					onClick={handleCardClick}
				>
					<Icon name="expand" />
					View Summary & Analysis
				</Button>
			</Card.Content>
		</Card>
	);
};

export default GovernmentNewsCard;
