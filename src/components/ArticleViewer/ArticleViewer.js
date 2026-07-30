import React from 'react';
import { Modal, Header, Image, Button, Icon, Segment, Divider } from 'semantic-ui-react';
import { sanitizeArticleText } from '../../utils/textSanitizer';

const ArticleViewer = ({ article, open, onClose }) => {
	if (!article) return null;
	const title = sanitizeArticleText(article.title, 'Untitled');
	const source = sanitizeArticleText(
		article.source && typeof article.source === 'object' ? article.source.name : article.source,
		'Unknown'
	);
	const summary = sanitizeArticleText(article.ai_summary);
	const description = sanitizeArticleText(article.description);

	const safeFormatDate = (dateVal) => {
		if (!dateVal) return 'Recently';
		try {
			const d = new Date(dateVal);
			return isNaN(d.getTime()) ? 'Recently' : d.toLocaleString();
		} catch (e) {
			return 'Recently';
		}
	};

	return (
		<Modal open={open} onClose={onClose} size="large" closeIcon centered={false}>
			<Modal.Header>
				{title}
			</Modal.Header>
			<Modal.Content scrolling>
				{(article.image || article.urlToImage) && (
					<Image
						src={article.image || article.urlToImage}
						wrapped
						ui={false}
						style={{ 
							maxHeight: '300px', 
							objectFit: 'cover', 
							marginBottom: '20px', 
							borderRadius: '8px',
							width: '100%'
						}}
					/>
				)}

				<Segment secondary>
					<Header as="h4" style={{ marginBottom: '10px' }}>
						<Icon name="newspaper" /> Source: {source}
					</Header>
					<p style={{ color: '#666', marginBottom: '0' }}>
						<Icon name="calendar" /> Published: {safeFormatDate(article.published_at || article.publishedAt)}
					</p>
				</Segment>

				{summary && (
					<Segment color="blue" style={{ background: '#f0f7ff' }}>
						<Header as="h3">
							<Icon name="lightbulb" color="yellow" />
							Predovex Smart Summary
						</Header>
						<p style={{ fontSize: '1.1rem', fontStyle: 'italic', lineHeight: '1.6' }}>{summary}</p>
					</Segment>
				)}

				{description && (
					<div style={{ marginBottom: '20px' }}>
						<Header as="h3" color="blue">Description</Header>
						<p style={{ lineHeight: '1.8', fontSize: '16px' }}>{description}</p>
					</div>
				)}

				<Divider />

				<Segment color="blue">
					<Header as="h5">
						<Icon name="info circle" /> Note
					</Header>
					<p>
						This is a summary of the article. For the complete story with images, videos, 
						and additional details, visit the original source.
					</p>
				</Segment>
			</Modal.Content>
			<Modal.Actions>
				<Button onClick={onClose}>
					<Icon name="close" />
					Close
				</Button>
				<Button
					color="blue"
					onClick={() => window.open(article.url, '_blank', 'noopener,noreferrer')}
					primary
					fluid
				>
					<Icon name="external" />
					Read Full Article on Source Website
				</Button>
			</Modal.Actions>
		</Modal>
	);
};

export default ArticleViewer;
