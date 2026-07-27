import React, { useState, useEffect } from 'react';
import { Segment, Header, Grid, Statistic, Loader, Message, Icon } from 'semantic-ui-react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  AreaChart, Area, BarChart, Bar
} from 'recharts';
import axios from 'axios';
import { BACKEND_URL } from '../../API/governmentApi';

const ImpactTrends = ({ articles = [] }) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get(BACKEND_URL + '/api/analytics/trends');
        setData(response.data);
      } catch (err) {
        console.error('Failed to fetch analytics:', err);
        setError('Could not load intelligence trends. Ensure the backend is running.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) return <Loader active inline="centered" size="large">Analyzing intelligence trends...</Loader>;
  if (error) return <Message error icon="warning" header="Intelligence Error" content={error} />;
  // Keep the intelligence view useful even when analytics storage is empty by
  // deriving the same metrics from the articles already loaded in the app.
  const fallbackCountries = Array.from(new Set(articles.map(a => a.country).filter(Boolean)));
  const fallbackDates = Array.from({ length: 7 }, (_, index) => {
    const date = new Date();
    date.setDate(date.getDate() - (6 - index));
    return date.toISOString().slice(0, 10);
  });
  const fallbackChart = fallbackDates.map(date => {
    const dayArticles = articles.filter(article => String(article.publishedAt || article.published_at || '').slice(0, 10) === date);
    return { date, ...(fallbackCountries.length ? fallbackCountries.reduce((acc, country) => ({ ...acc, [country]: dayArticles.filter(a => a.country === country).length }), {}) : { Intelligence: dayArticles.length }) };
  });
  const fallbackImpact = fallbackDates.map(date => {
    const dayArticles = articles.filter(article => String(article.publishedAt || article.published_at || '').slice(0, 10) === date);
    const score = dayArticles.length ? dayArticles.reduce((sum, article) => sum + (Number(article.impact_score || article.impactScore || 50)), 0) / dayArticles.length : 0;
    return { date, Intelligence: Math.round(score) };
  });
  const resolvedData = data && data.chart_data && data.chart_data.length > 0 ? data : {
    summary: { total_articles: articles.length, avg_impact: articles.length ? articles.reduce((sum, article) => sum + Number(article.impact_score || article.impactScore || 50), 0) / articles.length : 0, countries: fallbackCountries },
    chart_data: fallbackChart,
    impact_chart_data: fallbackImpact,
  };
  const countries = resolvedData.summary.countries || [];
  const colors = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#0088fe'];

  return (
    <div style={{ padding: '20px' }}>
      <Header as="h2" dividing>
        <Icon name="dashboard" />
        <Header.Content>
          Intelligence Dashboard
          <Header.Subheader>Impact trends and geopolitical activity monitoring</Header.Subheader>
        </Header.Content>
      </Header>

      <Grid stackable columns={3} style={{ marginBottom: '20px' }}>
        <Grid.Column>
          <Segment textAlign="center" color="blue">
            <Statistic size="tiny">
          <Statistic.Value>{resolvedData.summary.total_articles}</Statistic.Value>
              <Statistic.Label>Intelligence Assets</Statistic.Label>
            </Statistic>
          </Segment>
        </Grid.Column>
        <Grid.Column>
          <Segment textAlign="center" color="green">
            <Statistic size="tiny">
              <Statistic.Value>{Number(resolvedData.summary.avg_impact || 0).toFixed(1)}</Statistic.Value>
              <Statistic.Label>Avg. Impact Score</Statistic.Label>
            </Statistic>
          </Segment>
        </Grid.Column>
        <Grid.Column>
          <Segment textAlign="center" color="orange">
            <Statistic size="tiny">
              <Statistic.Value>{countries.length}</Statistic.Value>
              <Statistic.Label>Active Regions</Statistic.Label>
            </Statistic>
          </Segment>
        </Grid.Column>
      </Grid>

      <Grid stackable columns={2}>
        <Grid.Column width={10}>
          <Segment>
            <Header as="h3">Geopolitical Activity Volume</Header>
            <p className="text-muted">Daily volume of government and policy updates by country</p>
            <div style={{ width: '100%', height: 400 }}>
              <ResponsiveContainer>
                <AreaChart data={resolvedData.chart_data}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  {countries.map((country, index) => (
                    <Area 
                      key={country}
                      type="monotone" 
                      dataKey={country} 
                      stackId="1"
                      stroke={colors[index % colors.length]} 
                      fill={colors[index % colors.length]} 
                    />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Segment>
        </Grid.Column>

        <Grid.Column width={6}>
          <Segment>
            <Header as="h3">Policy Impact Scores</Header>
            <p className="text-muted">Average impact level of recent government actions</p>
            <div style={{ width: '100%', height: 400 }}>
              <ResponsiveContainer>
                <BarChart data={resolvedData.impact_chart_data}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Legend />
                  {countries.map((country, index) => (
                    <Bar 
                      key={country}
                      dataKey={country} 
                      fill={colors[index % colors.length]} 
                    />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Segment>
        </Grid.Column>
      </Grid>
      
      <Message info icon>
        <Icon name="info circle" />
        <Message.Content>
          <Message.Header>Geopolitical Insight</Message.Header>
          Currently monitoring intelligence from: <strong>{countries.join(', ')}</strong>.
          The impact score is calculated based on market sensitivity and historical policy significance.
        </Message.Content>
      </Message>
    </div>
  );
};

export default ImpactTrends;
