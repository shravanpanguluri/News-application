import React, { useState, useEffect } from 'react';
import { Segment, Header, Icon, Card, Loader, Dimmer, Button, Statistic, Label, Grid, Divider, Container } from 'semantic-ui-react';
import './TrendingPredictions.css';
import { BACKEND_URL } from '../../API/governmentApi';

const TrendingPredictions = () => {
    const [trending, setTrending] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [filter, setFilter] = useState('all');

    const fetchTrending = async () => {
        try {
            setLoading(true);
            setError(null);

            const response = await fetch(`${BACKEND_URL}/gdelt/trending?days=1&limit=20`);

            if (!response.ok) {
                throw new Error('Failed to fetch trending topics');
            }

            const data = await response.json();
            setTrending(data);
        } catch (err) {
            console.error('❌ Error fetching trending topics:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTrending();
    }, []);

    const getTrendIcon = (index) => {
        if (index === 0) return 'fire';
        if (index === 1) return 'arrow up';
        if (index === 2) return 'chart line';
        return 'trending up';
    };

    const getTrendColor = (index) => {
        if (index === 0) return 'red';
        if (index === 1) return 'orange';
        if (index === 2) return 'yellow';
        return 'blue';
    };

    const getPredictionTime = (count) => {
        if (count >= 800) return '6-12 hours';
        if (count >= 600) return '12-24 hours';
        if (count >= 400) return '24-36 hours';
        return '36-48 hours';
    };

    const getIntensityLevel = (count) => {
        if (count >= 800) return { label: 'VIRAL', color: 'red' };
        if (count >= 600) return { label: 'HIGH', color: 'orange' };
        if (count >= 400) return { label: 'MEDIUM', color: 'yellow' };
        return { label: 'EMERGING', color: 'blue' };
    };

    const filterTopics = (topics) => {
        if (filter === 'all') return topics;
        if (filter === 'viral') return topics.filter(t => t.count >= 800);
        if (filter === 'high') return topics.filter(t => t.count >= 600 && t.count < 800);
        if (filter === 'medium') return topics.filter(t => t.count >= 400 && t.count < 600);
        return topics;
    };

    return (
        <Container fluid style={{ padding: '20px' }}>
            {/* Header Section */}
            <Segment raised style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white', marginBottom: '20px' }}>
                <Header as="h1" textAlign="center" style={{ color: 'white', marginBottom: '10px' }}>
                    <Icon name="magic" />
                    AI Trend Predictions
                    <Header.Subheader style={{ color: 'rgba(255,255,255,0.9)' }}>
                        Predicting viral topics from GDELT global news analysis (65+ languages, 100K+ sources daily)
                    </Header.Subheader>
                </Header>
            </Segment>

            {loading && !trending ? (
                <Segment raised>
                    <Dimmer active>
                        <Loader size="large">Analyzing global news patterns...</Loader>
                    </Dimmer>
                </Segment>
            ) : error ? (
                <Segment raised color="red">
                    <Header as="h3">
                        <Icon name="warning sign" />
                        Error Loading Predictions
                    </Header>
                    <p>{error}</p>
                    <Button onClick={fetchTrending} color="purple" icon="refresh" content="Retry" />
                </Segment>
            ) : trending?.trending_topics && trending.trending_topics.length > 0 ? (
                <>
                    {/* Stats Overview */}
                    <Grid columns={4} divided stackable style={{ marginBottom: '20px' }}>
                        <Grid.Row>
                            <Grid.Column>
                                <Segment raised textAlign="center">
                                    <Statistic color="red">
                                        <Statistic.Value>{trending.trending_topics.filter(t => t.count >= 800).length}</Statistic.Value>
                                        <Statistic.Label>Viral Trends</Statistic.Label>
                                    </Statistic>
                                </Segment>
                            </Grid.Column>
                            <Grid.Column>
                                <Segment raised textAlign="center">
                                    <Statistic color="blue">
                                        <Statistic.Value>{trending.trending_topics.length}</Statistic.Value>
                                        <Statistic.Label>Topics Analyzed</Statistic.Label>
                                    </Statistic>
                                </Segment>
                            </Grid.Column>
                            <Grid.Column>
                                <Segment raised textAlign="center">
                                    <Statistic color="green">
                                        <Statistic.Value>{Math.round(trending.trending_topics.reduce((sum, t) => sum + t.count, 0) / trending.trending_topics.length)}</Statistic.Value>
                                        <Statistic.Label>Avg Mentions</Statistic.Label>
                                    </Statistic>
                                </Segment>
                            </Grid.Column>
                            <Grid.Column>
                                <Segment raised textAlign="center">
                                    <Statistic color="purple">
                                        <Statistic.Value>24h</Statistic.Value>
                                        <Statistic.Label>Analysis Period</Statistic.Label>
                                    </Statistic>
                                </Segment>
                            </Grid.Column>
                        </Grid.Row>
                    </Grid>

                    {/* Filter Buttons */}
                    <Segment raised style={{ marginBottom: '20px' }}>
                        <Button.Group fluid widths={4}>
                            <Button 
                                active={filter === 'all'} 
                                onClick={() => setFilter('all')}
                                color="purple"
                                icon="globe"
                                content="All Trends"
                            />
                            <Button 
                                active={filter === 'viral'} 
                                onClick={() => setFilter('viral')}
                                color="red"
                                icon="fire"
                                content="Viral"
                            />
                            <Button 
                                active={filter === 'high'} 
                                onClick={() => setFilter('high')}
                                color="orange"
                                icon="arrow up"
                                content="High"
                            />
                            <Button 
                                active={filter === 'medium'} 
                                onClick={() => setFilter('medium')}
                                color="yellow"
                                icon="chart line"
                                content="Medium"
                            />
                        </Button.Group>
                    </Segment>

                    {/* Trending Topics */}
                    <Grid columns={2} divided stackable>
                        <Grid.Row>
                            {filterTopics(trending.trending_topics).map((topic, index) => {
                                const intensity = getIntensityLevel(topic.count);
                                const trendColor = getTrendColor(index);
                                
                                return (
                                    <Grid.Column key={index}>
                                        <Card fluid className={`trend-card ${intensity.color}`}>
                                            <Card.Content>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                                        <Icon name={getTrendIcon(index)} size="large" color={trendColor} />
                                                        <Header as="h4" style={{ margin: 0 }}>{topic.topic}</Header>
                                                    </div>
                                                    <Label color={intensity.color} ribbon size="small">
                                                        {intensity.label}
                                                    </Label>
                                                </div>
                                                
                                                <Divider />
                                                
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                    <div>
                                                        <Icon name="newspaper" />
                                                        <strong>{topic.count}</strong> mentions
                                                    </div>
                                                    <div>
                                                        <Icon name="clock outline" />
                                                        Predicted: <strong>{getPredictionTime(topic.count)}</strong>
                                                    </div>
                                                </div>
                                            </Card.Content>
                                            
                                            {index < 3 && (
                                                <Card.Content extra>
                                                    <Label color={index === 0 ? 'red' : index === 1 ? 'orange' : 'yellow'}>
                                                        <Icon name="trophy" />
                                                        Top {index + 1} Trend
                                                    </Label>
                                                </Card.Content>
                                            )}
                                        </Card>
                                    </Grid.Column>
                                );
                            })}
                        </Grid.Row>
                    </Grid>

                    {/* Refresh Button */}
                    <div style={{ textAlign: 'center', marginTop: '20px' }}>
                        <Button onClick={fetchTrending} color="purple" size="large" icon="refresh" content="Refresh Predictions" />
                    </div>

                    {/* Info Message */}
                    <Segment info style={{ marginTop: '20px' }}>
                        <Icon name="info circle" />
                        <strong>How it works:</strong> GDELT monitors global news in 65+ languages from 100K+ sources. 
                        Our AI analyzes mention velocity, acceleration, and cross-source validation to predict which topics will trend in the next 6-48 hours.
                    </Segment>
                </>
            ) : (
                <Segment raised placeholder>
                    <Header icon>
                        <Icon name="magic" />
                        No Trending Predictions Available
                    </Header>
                    <p>Check back later or click Refresh to fetch latest predictions.</p>
                    <Button onClick={fetchTrending} color="purple" icon="refresh" content="Refresh" />
                </Segment>
            )}
        </Container>
    );
};

export default TrendingPredictions;
