import React, { useState, useEffect } from 'react';
import { Container, Segment, Header, Card, Grid, Label, Icon, Button, Loader, Message, Divider, Statistic, Feed, List, Progress } from 'semantic-ui-react';
import governmentAPI from '../../API/governmentApi';

const IntelligentBreakingNews = () => {
    const [breakingNews, setBreakingNews] = useState([]);
    const [loading, setLoading] = useState(true);
    const [trendingTopics, setTrendingTopics] = useState([]);

    useEffect(() => {
        loadBreakingNews();
        loadTrendingTopics();
        
        // Auto-refresh every 2 minutes
        const interval = setInterval(() => {
            loadBreakingNews();
        }, 120000);
        
        return () => clearInterval(interval);
    }, []);

    const loadBreakingNews = async () => {
        try {
            const response = await governmentAPI.get('/breaking-news?limit=20');
            setBreakingNews(response.breaking_news || []);
            console.log('Breaking news loaded:', response);
        } catch (error) {
            console.error('Error loading breaking news:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadTrendingTopics = async () => {
        try {
            const response = await governmentAPI.get('/trending-topics');
            setTrendingTopics(response.trending_topics || []);
        } catch (error) {
            console.error('Error loading trending topics:', error);
        }
    };

    const getBreakingBadge = (score) => {
        if (score >= 80) return { color: 'red', text: '🔥 BREAKING', icon: 'fire' };
        if (score >= 70) return { color: 'orange', text: '⚡ URGENT', icon: 'bolt' };
        if (score >= 50) return { color: 'yellow', text: '📈 TRENDING', icon: 'chart line' };
        return { color: 'grey', text: '📰 NEWS', icon: 'newspaper' };
    };

    const getSignalIcon = (signalName, score) => {
        const icons = {
            'recency': 'clock',
            'cross_source': 'share alternate',
            'keywords': 'tags',
            'authority': 'shield',
            'reddit': 'reddit alien',
            'market_impact': 'dollar'
        };
        return icons[signalName] || 'circle';
    };

    if (loading) {
        return (
            <Segment textAlign="center" padded>
                <Loader active inline="centered" size="large">
                    Analyzing news signals...
                </Loader>
            </Segment>
        );
    }

    return (
        <Container fluid style={{ padding: '20px' }}>
            <Header as="h1" icon textAlign="center">
                <Icon name="bolt" color="yellow" />
                <Header.Content>
                    🔥 Intelligent Breaking News
                    <Header.Subheader>
                        AI-powered detection using 6 signal analysis
                    </Header.Subheader>
                </Header.Content>
            </Header>

            <Grid stackable columns={3}>
                {/* Main Breaking News Feed */}
                <Grid.Column width={10}>
                    <Header as="h2">
                        <Icon name="fire" color="red" />
                        Breaking News Feed
                        <Label color="red" floating>
                            {breakingNews.filter(n => n.breaking_score >= 70).length} Active
                        </Label>
                    </Header>

                    {breakingNews.length === 0 ? (
                        <Message info>
                            <Message.Header>No breaking news detected</Message.Header>
                            <p>Checking for developing stories across multiple sources...</p>
                        </Message>
                    ) : (
                        <Feed>
                            {breakingNews.map((article, index) => {
                                const badge = getBreakingBadge(article.breaking_score);
                                return (
                                    <Feed.Event key={index}>
                                        <Feed.Label>
                                            <Icon name={badge.icon} color={badge.color} size="large" />
                                        </Feed.Label>
                                        <Feed.Content>
                                            <Feed.Summary>
                                                <Label color={badge.color} size="tiny" ribbon>
                                                    {badge.text} - Score: {article.breaking_score}
                                                </Label>
                                                <a href={article.url} target="_blank" rel="noopener noreferrer">
                                                    {article.title}
                                                </a>
                                            </Feed.Summary>
                                            <Feed.Extra text>
                                                {article.description?.substring(0, 200)}...
                                            </Feed.Extra>
                                            <Feed.Meta>
                                                <Icon name="building" /> {article.source}
                                                <Icon name="clock" style={{ marginLeft: '10px' }} />
                                                {new Date(article.published_at).toLocaleString()}
                                                <Icon name="chart line" style={{ marginLeft: '10px' }} />
                                                {article.breaking_rank ? `#${article.breaking_rank} Breaking` : ''}
                                            </Feed.Meta>

                                            {/* Signal Breakdown */}
                                            {article.breaking_signals && (
                                                <Segment secondary style={{ marginTop: '10px' }}>
                                                    <Header as="h5">Detection Signals</Header>
                                                    <List horizontal divided size="small">
                                                        {Object.entries(article.breaking_signals).map(([signal, data]) => (
                                                            data.score > 0 && (
                                                                <List.Item key={signal}>
                                                                    <Icon name={getSignalIcon(signal, data.score)} color="blue" />
                                                                    <List.Content>
                                                                        {signal.replace('_', ' ')}: {data.score}pts
                                                                    </List.Content>
                                                                </List.Item>
                                                            )
                                                        ))}
                                                    </List>
                                                </Segment>
                                            )}

                                            <Divider />
                                        </Feed.Content>
                                    </Feed.Event>
                                );
                            })}
                        </Feed>
                    )}
                </Grid.Column>

                {/* Right Sidebar: Trending Topics & Stats */}
                <Grid.Column width={6}>
                    {/* Trending Topics */}
                    <Segment>
                        <Header as="h3">
                            <Icon name="trending up" color="green" />
                            Trending Topics
                        </Header>
                        <List>
                            {trendingTopics.slice(0, 10).map((topic, index) => (
                                <List.Item key={index}>
                                    <List.Content>
                                        <List.Header>
                                            #{index + 1} {topic.topic}
                                        </List.Header>
                                        <List.Description>
                                            <Label size="mini" color={topic.relevance === 'high' ? 'red' : 'orange'}>
                                                {topic.count} mentions
                                            </Label>
                                        </List.Description>
                                    </List.Content>
                                </List.Item>
                            ))}
                        </List>
                    </Segment>

                    {/* Analysis Stats */}
                    <Segment>
                        <Header as="h3">
                            <Icon name="chart bar" />
                            Analysis Statistics
                        </Header>
                        <Statistic.Group widths={2}>
                            <Statistic>
                                <Statistic.Value>{breakingNews.length}</Statistic.Value>
                                <Statistic.Label>Stories Analyzed</Statistic.Label>
                            </Statistic>
                            <Statistic>
                                <Statistic.Value color="red">
                                    {breakingNews.filter(n => n.breaking_score >= 70).length}
                                </Statistic.Value>
                                <Statistic.Label>Breaking</Statistic.Label>
                            </Statistic>
                            <Statistic>
                                <Statistic.Value color="orange">
                                    {breakingNews.filter(n => n.breaking_score >= 50 && n.breaking_score < 70).length}
                                </Statistic.Value>
                                <Statistic.Label>Trending</Statistic.Label>
                            </Statistic>
                            <Statistic>
                                <Statistic.Value>6</Statistic.Value>
                                <Statistic.Label>Signals Tracked</Statistic.Label>
                            </Statistic>
                        </Statistic.Group>
                    </Segment>

                    {/* How It Works */}
                    <Segment secondary>
                        <Header as="h4">
                            <Icon name="info circle" />
                            How Breaking Detection Works
                        </Header>
                        <List bulleted>
                            <List.Item>
                                <strong>Recency (20pts)</strong> - How recent the article is
                            </List.Item>
                            <List.Item>
                                <strong>Cross-Source (25pts)</strong> - Multiple sources reporting same story
                            </List.Item>
                            <List.Item>
                                <strong>Keywords (20pts)</strong> - Breaking news language detection
                            </List.Item>
                            <List.Item>
                                <strong>Authority (15pts)</strong> - Government/major news sources
                            </List.Item>
                            <List.Item>
                                <strong>Market Impact (10pts)</strong> - Stock/company mentions
                            </List.Item>
                        </List>
                    </Segment>
                </Grid.Column>
            </Grid>
        </Container>
    );
};

export default IntelligentBreakingNews;
