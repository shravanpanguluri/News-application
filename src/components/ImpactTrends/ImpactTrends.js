import React, { useEffect, useState } from 'react';
import { Header, Icon, Loader, Message, Segment, Statistic, Table } from 'semantic-ui-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { BACKEND_URL } from '../../API/governmentApi';

const formatDate = value => {
  const date = new Date(value + 'T00:00:00');
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
};

const ImpactTrends = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    const loadTrends = async () => {
      try {
        setLoading(true);
        setError('');
        const response = await fetch(`${BACKEND_URL}/api/analytics/trends?days=30`);
        if (!response.ok) {
          throw new Error(`Trend endpoint returned ${response.status}`);
        }
        const payload = await response.json();
        if (!cancelled) setData(payload);
      } catch (err) {
        if (!cancelled) setError(err.message || 'Unable to load impact trends');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    loadTrends();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <Segment basic>
        <Loader active inline="centered" content="Loading impact trends" />
      </Segment>
    );
  }

  if (error) {
    return (
      <Message warning>
        <Message.Header>Impact Trends Unavailable</Message.Header>
        <p>{error}</p>
      </Message>
    );
  }

  const trends = data?.trends || [];
  const summary = data?.summary || {};
  const categories = data?.category_breakdown || [];

  return (
    <div className="gp-analysis-wrap impact-trends">
      <Header as="h2">
        <Icon name="chart line" />
        <Header.Content>
          Impact Trends
          <Header.Subheader>30-day intelligence impact and article volume</Header.Subheader>
        </Header.Content>
      </Header>

      <Statistic.Group widths="four" size="small">
        <Statistic>
          <Statistic.Value>{summary.total_articles || 0}</Statistic.Value>
          <Statistic.Label>Total Signals</Statistic.Label>
        </Statistic>
        <Statistic color="red">
          <Statistic.Value>{summary.high_impact_total || 0}</Statistic.Value>
          <Statistic.Label>High Impact</Statistic.Label>
        </Statistic>
        <Statistic color="blue">
          <Statistic.Value>{summary.current_avg_impact || 0}</Statistic.Value>
          <Statistic.Label>Avg Impact</Statistic.Label>
        </Statistic>
        <Statistic color={summary.direction === 'rising' ? 'green' : summary.direction === 'falling' ? 'orange' : 'grey'}>
          <Statistic.Value>{summary.avg_impact_delta_7d > 0 ? '+' : ''}{summary.avg_impact_delta_7d || 0}</Statistic.Value>
          <Statistic.Label>7D Change</Statistic.Label>
        </Statistic>
      </Statistic.Group>

      <Segment className="impact-trends-chart">
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={trends} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tickFormatter={formatDate} minTickGap={18} />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip labelFormatter={formatDate} />
            <Legend />
            <Area yAxisId="left" type="monotone" dataKey="article_count" name="Article Volume" fill="#4a7fa5" stroke="#4a7fa5" fillOpacity={0.18} />
            <Line yAxisId="right" type="monotone" dataKey="avg_impact" name="Average Impact" stroke="#c8553d" strokeWidth={2} dot={false} />
            <Line yAxisId="right" type="monotone" dataKey="high" name="High Impact Signals" stroke="#b84030" strokeWidth={2} dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </Segment>

      <Table celled compact="very" className="impact-trends-table">
        <Table.Header>
          <Table.Row>
            <Table.HeaderCell>Category</Table.HeaderCell>
            <Table.HeaderCell textAlign="right">Signals</Table.HeaderCell>
            <Table.HeaderCell textAlign="right">High Impact</Table.HeaderCell>
            <Table.HeaderCell textAlign="right">Avg Impact</Table.HeaderCell>
            <Table.HeaderCell>Trend</Table.HeaderCell>
          </Table.Row>
        </Table.Header>
        <Table.Body>
          {categories.map(item => (
            <Table.Row key={item.category}>
              <Table.Cell style={{ textTransform: 'capitalize' }}>{item.category}</Table.Cell>
              <Table.Cell textAlign="right">{item.total}</Table.Cell>
              <Table.Cell textAlign="right">{item.high_impact}</Table.Cell>
              <Table.Cell textAlign="right">{item.avg_impact}</Table.Cell>
              <Table.Cell>
                <Icon name={item.trend === 'up' ? 'arrow up' : 'minus'} color={item.trend === 'up' ? 'green' : 'grey'} />
                {item.trend}
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table>
    </div>
  );
};

export default ImpactTrends;
