import React, { useState } from 'react';
import { Segment, Input, Button, Grid, Header, Loader, Message, Card, Label, Icon, Dropdown } from 'semantic-ui-react';
import governmentAPI from '../../API/governmentApi';

const SearchComponent = ({ onArticleClick }) => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [category, setCategory] = useState('all');
    const [country, setCountry] = useState('all');
    const [days, setDays] = useState(7);

    const handleSearch = async () => {
        if (!query.trim()) return;
        
        setLoading(true);
        try {
            const params = new URLSearchParams({
                q: query,
                category,
                country,
                days: days.toString(),
                limit: '20'
            });
            
            const response = await governmentAPI.get(`/search?${params}`);
            setResults(response.results || []);
        } catch (error) {
            console.error('Search error:', error);
            setResults([]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter') {
            handleSearch();
        }
    };

    return (
        <Segment padded>
            <Header as="h2" icon textAlign="center">
                <Icon name="search" color="blue" />
                Advanced Search
            </Header>

            <Input
                fluid
                size="large"
                placeholder="Search news articles..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                action={
                    <Button 
                        color="blue" 
                        onClick={handleSearch}
                        loading={loading}
                        disabled={!query.trim()}
                    >
                        <Icon name="search" /> Search
                    </Button>
                }
            />

            <Grid columns={3} style={{ marginTop: '15px' }}>
                <Grid.Column>
                    <Dropdown
                        fluid
                        selection
                        placeholder="All Categories"
                        options={[
                            { text: 'All Categories', value: 'all' },
                            { text: 'General', value: 'general' },
                            { text: 'Policy', value: 'policy' },
                            { text: 'Economy', value: 'economy' },
                            { text: 'Technology', value: 'technology' },
                            { text: 'Health', value: 'health' },
                            { text: 'Finance', value: 'finance' },
                        ]}
                        value={category}
                        onChange={(e, { value }) => setCategory(value)}
                    />
                </Grid.Column>
                <Grid.Column>
                    <Dropdown
                        fluid
                        selection
                        placeholder="All Countries"
                        options={[
                            { text: 'All Countries', value: 'all' },
                            { text: 'USA', value: 'us' },
                            { text: 'India', value: 'in' },
                            { text: 'Global', value: 'global' },
                        ]}
                        value={country}
                        onChange={(e, { value }) => setCountry(value)}
                    />
                </Grid.Column>
                <Grid.Column>
                    <Dropdown
                        fluid
                        selection
                        placeholder="Time Range"
                        options={[
                            { text: 'Last 7 days', value: 7 },
                            { text: 'Last 14 days', value: 14 },
                            { text: 'Last 30 days', value: 30 },
                        ]}
                        value={days}
                        onChange={(e, { value }) => setDays(value)}
                    />
                </Grid.Column>
            </Grid>

            {loading && (
                <Segment textAlign="center" padded>
                    <Loader active inline="centered">Searching articles...</Loader>
                </Segment>
            )}

            {!loading && results.length === 0 && query && (
                <Message info>
                    <Message.Header>No results found</Message.Header>
                    <p>Try different keywords or adjust your filters.</p>
                </Message>
            )}

            {!loading && results.length > 0 && (
                <>
                    <Header as="h3" style={{ marginTop: '20px' }}>
                        Found {results.length} articles
                    </Header>
                    <Card.Group itemsPerRow={1}>
                        {results.map((article, index) => (
                            <Card 
                                key={index} 
                                fluid
                                onClick={() => onArticleClick && onArticleClick(article)}
                                style={{ cursor: 'pointer' }}
                            >
                                <Card.Content>
                                    <Card.Header>{article.title}</Card.Header>
                                    <Card.Meta>
                                        <span>{article.source}</span>
                                        <Label size="tiny" color="blue" style={{ marginLeft: '10px' }}>
                                            Match: {article.match_score}
                                        </Label>
                                    </Card.Meta>
                                    <Card.Description>
                                        {article.description?.substring(0, 150)}...
                                    </Card.Description>
                                </Card.Content>
                                <Card.Content extra>
                                    <Label size="small">
                                        <Icon name="calendar" />
                                        {new Date(article.published_at).toLocaleDateString()}
                                    </Label>
                                    <Label size="small" color="green">
                                        <Icon name="tag" />
                                        {article.category}
                                    </Label>
                                    {article.impact_level && (
                                        <Label size="small" color={
                                            article.impact_level === 'High' ? 'red' :
                                            article.impact_level === 'Medium' ? 'orange' : 'grey'
                                        }>
                                            <Icon name="chart line" />
                                            {article.impact_level} Impact
                                        </Label>
                                    )}
                                </Card.Content>
                            </Card>
                        ))}
                    </Card.Group>
                </>
            )}
        </Segment>
    );
};

export default SearchComponent;
