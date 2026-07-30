import React, { useState, useEffect } from 'react';
import { Segment, Icon, Container } from 'semantic-ui-react';
import './BreakingNewsTicker.css';

const BreakingNewsTicker = ({ breakingNews = [] }) => {
	const [currentIndex, setCurrentIndex] = useState(0);
	const [isPaused, setIsPaused] = useState(false);

	useEffect(() => {
		if (breakingNews.length === 0) return;

		const interval = setInterval(() => {
			if (!isPaused) {
				setCurrentIndex((prev) => (prev + 1) % breakingNews.length);
			}
		}, 4000); // Change every 4 seconds

		return () => clearInterval(interval);
	}, [breakingNews.length, isPaused]);

	if (breakingNews.length === 0) return null;

	const currentArticle = breakingNews[currentIndex];

	return (
		<Container fluid className="breaking-news-container">
			<Segment className="breaking-news-segment" attached="bottom">
				<div
					className="breaking-news-content"
					onMouseEnter={() => setIsPaused(true)}
					onMouseLeave={() => setIsPaused(false)}
				>
					<div className="breaking-news-label">
						<Icon name="bolt" color="red" />
						BREAKING
					</div>
					<div className="breaking-news-text">
						<span className="breaking-news-title">
							{currentArticle && currentArticle.title ? currentArticle.title : 'Loading...'}
						</span>
						<span className="breaking-news-source">
							<Icon name="shield" color="red" size="small" /> PREDOVEX INTELLIGENCE
						</span>
					</div>
					<div className="breaking-news-indicators">
						{breakingNews.map((_, idx) => (
							<span
								key={idx}
								className={`indicator ${idx === currentIndex ? 'active' : ''}`}
								onClick={() => setCurrentIndex(idx)}
							/>
						))}
					</div>
				</div>
			</Segment>
		</Container>
	);
};

export default BreakingNewsTicker;
