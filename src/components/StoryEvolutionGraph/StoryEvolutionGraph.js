import React, { useState } from 'react';
import { Grid, Card, Image, Label, Icon } from 'semantic-ui-react';
import { getFramingColor, getSentimentColor } from '../../utils/narrativeDNA';
import './StoryEvolutionGraph.css';

const StoryEvolutionGraph = ({ stories = [], onStorySelect }) => {
  const [selectedStory, setSelectedStory] = useState(null);

  if (!stories || stories.length === 0) {
    return (
      <div className="story-graph-empty">
        <Icon name="sitemap" size="huge" color="grey" />
        <h3>No stories to analyze yet</h3>
        <p>Articles with NLP analysis will appear here</p>
      </div>
    );
  }

  // Sort by time
  const sortedStories = [...stories]
    .filter(s => s.genes && s.published_at)
    .sort((a, b) => new Date(b.published_at) - new Date(a.published_at));

  const handleStoryClick = (story) => {
    setSelectedStory(story);
    if (onStorySelect) onStorySelect(story);
  };

  return (
    <div className="story-evolution-grid">
      <Grid columns={3} stackable>
        {sortedStories.map((story, idx) => (
          <Grid.Column key={story.id || idx}>
            <StoryNode 
              story={story} 
              onClick={() => handleStoryClick(story)}
              isSelected={selectedStory && selectedStory.id === story.id}
            />
          </Grid.Column>
        ))}
      </Grid>

      {selectedStory && (
        <StoryDetails 
          story={selectedStory} 
          onClose={() => setSelectedStory(null)}
        />
      )}
    </div>
  );
};

const StoryNode = ({ story, onClick, isSelected }) => {
  const { genes } = story;
  if (!genes) return null;

  return (
    <Card 
      fluid 
      className={`story-node ${isSelected ? 'selected' : ''}`}
      onClick={onClick}
      style={{ borderLeft: `4px solid ${getFramingColor(genes.framing.primary)}` }}
    >
      {story.image && (
        <Image src={story.image} wrapped alt={story.title} />
      )}
      
      <Card.Content>
        <div className="story-node-header">
          <Card.Header className="story-node-title">
            {story.title.length > 60 ? story.title.substring(0, 60) + '...' : story.title}
          </Card.Header>
          <div className="story-node-badges">
            <Label 
              size="small" 
              style={{ background: getFramingColor(genes.framing.primary), color: 'white' }}
            >
              {genes.framing.primary}
            </Label>
            <Label 
              size="small"
              style={{ background: getSentimentColor(genes.sentiment.score), color: 'white' }}
            >
              {genes.sentiment.score > 0 ? '😊' : genes.sentiment.score < 0 ? '😔' : '😐'}
            </Label>
          </div>
        </div>

        <Card.Meta className="story-node-meta">
          <span>
            <Icon name="building" /> {story.source}
          </span>
          <span>
            <Icon name="time" /> {getTimeAgo(new Date(story.published_at))}
          </span>
        </Card.Meta>

        {genes.entities && (genes.entities.people.length > 0 || genes.entities.organizations.length > 0) && (
          <div className="story-node-entities">
            {genes.entities.people.slice(0, 2).map((person, i) => (
              <Label key={i} size="tiny" pointing>
                <Icon name="user" /> {person}
              </Label>
            ))}
            {genes.entities.organizations.slice(0, 2).map((org, i) => (
              <Label key={i} size="tiny" pointing>
                <Icon name="building" /> {org}
              </Label>
            ))}
          </div>
        )}
      </Card.Content>

      <Card.Content extra>
        <div className="story-node-footer">
          <span className="sentiment-score">
            Sentiment: <strong style={{ color: getSentimentColor(genes.sentiment.score) }}>
              {genes.sentiment.score.toFixed(2)}
            </strong>
          </span>
          <span className="tone-tag">
            {genes.emotionalTone}
          </span>
        </div>
      </Card.Content>
    </Card>
  );
};

const StoryDetails = ({ story, onClose }) => {
  const { genes } = story;
  if (!genes) return null;

  return (
    <div className="story-details-overlay" onClick={onClose}>
      <div className="story-details-panel" onClick={e => e.stopPropagation()}>
        <div className="story-details-header">
          <h3>{story.title}</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="story-details-content">
          <div className="detail-section">
            <h4><Icon name="chart pie" /> Framing Analysis</h4>
            <div className="framing-tags">
              <Label style={{ background: getFramingColor(genes.framing.primary), color: 'white' }}>
                Primary: {genes.framing.primary}
              </Label>
              {genes.framing.secondary && (
                <Label style={{ background: getFramingColor(genes.framing.secondary), color: 'white' }}>
                  Secondary: {genes.framing.secondary}
                </Label>
              )}
            </div>
          </div>

          <div className="detail-section">
            <h4><Icon name="heart" /> Sentiment Analysis</h4>
            <div className="sentiment-bar-container">
              <div 
                className="sentiment-bar-fill"
                style={{ 
                  left: `${50 + genes.sentiment.score * 50}%`,
                  background: getSentimentColor(genes.sentiment.score)
                }}
              />
              <div className="sentiment-labels">
                <span>Negative</span>
                <span>Neutral</span>
                <span>Positive</span>
              </div>
            </div>
            <p className="sentiment-value">
              Score: <strong>{genes.sentiment.score.toFixed(2)}</strong> | 
              Magnitude: <strong>{genes.sentiment.magnitude.toFixed(2)}</strong>
            </p>
          </div>

          <div className="detail-section">
            <h4><Icon name="users" /> Entities Detected</h4>
            <div className="entities-grid">
              {genes.entities.people.length > 0 && (
                <div className="entity-group">
                  <strong>People:</strong>
                  {genes.entities.people.map((person, i) => (
                    <Label key={i} size="small">{person}</Label>
                  ))}
                </div>
              )}
              {genes.entities.organizations.length > 0 && (
                <div className="entity-group">
                  <strong>Organizations:</strong>
                  {genes.entities.organizations.map((org, i) => (
                    <Label key={i} size="small">{org}</Label>
                  ))}
                </div>
              )}
              {genes.entities.places.length > 0 && (
                <div className="entity-group">
                  <strong>Places:</strong>
                  {genes.entities.places.map((place, i) => (
                    <Label key={i} size="small">{place}</Label>
                  ))}
                </div>
              )}
            </div>
          </div>

          {genes.keyClaims && genes.keyClaims.length > 0 && (
            <div className="detail-section">
              <h4><Icon name="quote left" /> Key Claims</h4>
              <ul className="claims-list">
                {genes.keyClaims.map((claim, i) => (
                  <li key={i} className="claim-item">
                    "{claim.text}"
                    {claim.speaker !== 'Unknown' && (
                      <span className="claim-speaker"> — {claim.speaker}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <a 
            href={story.url}
            target="_blank"
            rel="noopener noreferrer"
            className="read-full-btn"
          >
            <Icon name="external" /> Read Full Article
          </a>
        </div>
      </div>
    </div>
  );
};

function getTimeAgo(date) {
  const seconds = Math.floor((new Date() - date) / 1000);
  
  if (seconds < 60) return 'Just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default StoryEvolutionGraph;
