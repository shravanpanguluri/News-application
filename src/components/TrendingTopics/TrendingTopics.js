import React from 'react';
import { Segment, Header, List, Icon } from 'semantic-ui-react';
import './TrendingTopics.css';

const TrendingTopics = ({ trending = [], onTopicClick }) => {
	if (trending.length === 0) return null;

	return (
		<Segment className="trending-segment">
			<Header as="h3" className="trending-header">
				<Icon name="fire" color="orange" />
				Trending Topics
			</Header>
			<List divided relaxed>
				{trending.map((topic, idx) => (
					<List.Item
						key={idx}
						className="trending-item"
						onClick={() => onTopicClick && onTopicClick(topic.topic)}
						style={{ cursor: 'pointer' }}
					>
						<List.Content>
							<div className="trending-topic-wrapper">
								<span className="trending-rank">#{idx + 1}</span>
								<span className="trending-topic-name">{topic.topic}</span>
								<span className="trending-count">
									{topic.count} articles
								</span>
							</div>
						</List.Content>
					</List.Item>
				))}
			</List>
		</Segment>
	);
};

export default TrendingTopics;
