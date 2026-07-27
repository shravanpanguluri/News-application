import React, { useState, useEffect } from 'react';
import { Container, Segment, Header, Grid, Card, Icon, Label, Button, Dimmer, Loader, Statistic } from 'semantic-ui-react';
import { useNLP } from '../../hooks/useNLP';
import StoryEvolutionGraph from '../StoryEvolutionGraph/StoryEvolutionGraph';
import { getFramingColor, getSentimentColor } from '../../utils/narrativeDNA';
import './NLPAnalysis.css';

const NLPAnalysis = ({ articles = [] }) => {
  const { ready, processing, analyzeArticles, loadingProgress, cacheStats } = useNLP();
  const [enrichedArticles, setEnrichedArticles] = useState([]);
  const [selectedStory, setSelectedStory] = useState(null);

  useEffect(() => {
    if (articles.length > 0 && ready) {
      processArticles();
    }
  }, [articles, ready]);

  const processArticles = async () => {
    try {
      const enriched = await analyzeArticles(articles.slice(0, 30));
      setEnrichedArticles(enriched || []);
    } catch (e) {
      console.error('NLP analysis failed:', e);
    }
  };

  const handleStorySelect = (story) => {
    setSelectedStory(story);
  };

  if (!ready) {
    return (
      <Container className="nlp-loading-container">
        <Dimmer active inverted>
          <Loader inverted size="large">
            <div className="nlp-loading-text">
              Initializing AI...
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${loadingProgress}%` }}
                />
              </div>
              <span>{loadingProgress}%</span>
            </div>
          </Loader>
        </Dimmer>
        <Segment basic>
          <Header as="h2" textAlign="center">
            <Icon name="brain" />
            AI-Powered News Analysis
          </Header>
          <p textAlign="center">
            Loading TensorFlow.js models for narrative analysis...
          </p>
        </Segment>
      </Container>
    );
  }

  return (
    <Container className="nlp-analysis-container">
      <Header as="h1" textAlign="center" className="nlp-header">
        <Icon name="project diagram" color="purple" />
        Narrative DNA Analysis
        <Header.Subheader>
          AI-powered story evolution tracking and bias detection
        </Header.Subheader>
      </Header>

      {/* Stats Overview */}
      <Grid columns={4} divided stackable className="nlp-stats">
        <Grid.Column>
          <Statistic color="blue">
            <Statistic.Value>{enrichedArticles.length}</Statistic.Value>
            <Statistic.Label>Stories Analyzed</Statistic.Label>
          </Statistic>
        </Grid.Column>
        <Grid.Column>
          <Statistic color="green">
            <Statistic.Value>{cacheStats.size}</Statistic.Value>
            <Statistic.Label>Embeddings Cached</Statistic.Label>
          </Statistic>
        </Grid.Column>
        <Grid.Column>
          <Statistic color="orange">
            <Statistic.Value>
              {enrichedArticles.filter(a => a.genes && a.genes.sentiment && a.genes.sentiment.score > 0.3).length}
            </Statistic.Value>
            <Statistic.Label>Positive Stories</Statistic.Label>
          </Statistic>
        </Grid.Column>
        <Grid.Column>
          <Statistic color="red">
            <Statistic.Value>
              {enrichedArticles.filter(a => a.genes && a.genes.sentiment && a.genes.sentiment.score < -0.3).length}
            </Statistic.Value>
            <Statistic.Label>Negative Stories</Statistic.Label>
          </Statistic>
        </Grid.Column>
      </Grid>

      {/* Story Evolution Graph */}
      <Segment className="graph-segment">
        <Header as="h2">
          <Icon name="sitemap" />
          Story Evolution Map
        </Header>
        <p className="graph-description">
          Each node represents a news story. Size indicates emotional intensity, 
          color shows framing type, and connections show semantic similarity.
        </p>
        <StoryEvolutionGraph 
          stories={enrichedArticles} 
          onStorySelect={handleStorySelect}
        />
      </Segment>

      {/* Framing Distribution */}
      <Segment>
        <Header as="h3">
          <Icon name="pie chart" />
          Framing Distribution
        </Header>
        <Grid columns={6} divided>
          {getFramingDistribution(enrichedArticles).map((frame, i) => (
            <Grid.Column key={i} textAlign="center">
              <div 
                className="framing-circle"
                style={{ 
                  background: frame.color,
                  width: `${60 + frame.count * 10}px`,
                  height: `${60 + frame.count * 10}px`
                }}
              >
                <span className="framing-count">{frame.count}</span>
              </div>
              <p className="framing-label">{frame.name}</p>
            </Grid.Column>
          ))}
        </Grid>
      </Segment>

      {/* Analyzed Articles Grid */}
      <Segment>
        <Header as="h3">
          <Icon name="newspaper" />
          Analyzed Articles
          <Label color="purple" floating>
            {enrichedArticles.length} stories
          </Label>
        </Header>

        {processing && (
          <Dimmer active inverted>
            <Loader inverted>Analyzing articles with AI...</Loader>
          </Dimmer>
        )}

        <Grid columns={1} stackable>
          {enrichedArticles.map((article, idx) => (
            <Grid.Column key={idx}>
              <ArticleCard 
                article={article} 
                onSelect={() => handleStorySelect({
                  ...article,
                  genes: article.genes
                })}
              />
            </Grid.Column>
          ))}
        </Grid>
      </Segment>
    </Container>
  );
};

// Article Card with NLP insights
const ArticleCard = ({ article, onSelect }) => {
  const { genes } = article;
  
  if (!genes) return null;

  return (
    <Card fluid className="nlp-article-card" onClick={onSelect}>
      <Card.Content>
        <div className="card-header">
          <Card.Header>{article.title}</Card.Header>
          <div className="card-badges">
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
              {genes.sentiment.score > 0 ? '😊' : genes.sentiment.score < 0 ? '😔' : '😐'}{' '}
              {genes.sentiment.score.toFixed(2)}
            </Label>
            <Label size="small" color="teal">
              {genes.emotionalTone}
            </Label>
          </div>
        </div>

        <Card.Meta>
          <span className="date">
            <Icon name="calendar" />
            {new Date(article.published_at).toLocaleDateString()}
          </span>
          <span className="source">
            <Icon name="shield" color="red" />
            GOVPULSE INTELLIGENCE BUREAU
          </span>
        </Card.Meta>

        <Card.Description>
          {article.description && article.description.substring(0, 150)}...
        </Card.Description>

        {/* Entities */}
        {(genes.entities.people.length > 0 || genes.entities.organizations.length > 0) && (
          <div className="entities-section">
            {genes.entities.people.length > 0 && (
              <div className="entity-group">
                <Icon name="user" />
                <span className="entity-label">People:</span>
                {genes.entities.people.slice(0, 3).map((person, i) => (
                  <Label key={i} size="tiny">{person}</Label>
                ))}
              </div>
            )}
            
            {genes.entities.organizations.length > 0 && (
              <div className="entity-group">
                <Icon name="building" />
                <span className="entity-label">Orgs:</span>
                {genes.entities.organizations.slice(0, 3).map((org, i) => (
                  <Label key={i} size="tiny">{org}</Label>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Key Claims */}
        {genes.keyClaims.length > 0 && (
          <div className="claims-section">
            <Header as="h5">
              <Icon name="quote left" />
              Key Claims
            </Header>
            <ul className="claims-list">
              {genes.keyClaims.slice(0, 2).map((claim, i) => (
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
      </Card.Content>
      
      <Card.Content extra>
        <Button primary fluid size="small">
          <Icon name="search" /> View Full Analysis
        </Button>
      </Card.Content>
    </Card>
  );
};

// Helper function
function getFramingDistribution(articles) {
  const distribution = {
    economic: { name: 'Economic', count: 0, color: '#3498db' },
    security: { name: 'Security', count: 0, color: '#e74c3c' },
    humanitarian: { name: 'Humanitarian', count: 0, color: '#2ecc71' },
    political: { name: 'Political', count: 0, color: '#9b59b6' },
    scientific: { name: 'Scientific', count: 0, color: '#f39c12' },
    moral: { name: 'Moral', count: 0, color: '#1abc9c' },
    general: { name: 'General', count: 0, color: '#95a5a6' }
  };

  articles.forEach(article => {
    const frame = (article.genes && article.genes.framing && article.genes.framing.primary) || 'general';
    if (distribution[frame]) {
      distribution[frame].count++;
    }
  });

  return Object.values(distribution).filter(d => d.count > 0);
}

export default NLPAnalysis;
