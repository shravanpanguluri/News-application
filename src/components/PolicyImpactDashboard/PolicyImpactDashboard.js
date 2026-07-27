import React, { useState, useEffect } from 'react';
import { Container, Segment, Header, Card, Grid, Label, Icon, Button, Loader, Message, Divider, Statistic, Accordion, List, Table, Tab } from 'semantic-ui-react';
import governmentAPI, { BACKEND_URL } from '../../API/governmentApi';

// Companies to monitor for regulatory risk
const REGULATORY_WATCH = [
  { ticker: 'PFE', name: 'Pfizer', sector: 'Healthcare' },
  { ticker: 'JNJ', name: 'Johnson & Johnson', sector: 'Healthcare' },
  { ticker: 'AAPL', name: 'Apple', sector: 'Technology' },
  { ticker: 'GOOGL', name: 'Google', sector: 'Technology' },
  { ticker: 'TSLA', name: 'Tesla', sector: 'Automotive' },
];

const PolicyImpactDashboard = () => {
  const [recentPolicies, setRecentPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [testAnalysis, setTestAnalysis] = useState(null);
  
  // New state for regulatory and FOIA data
  const [regulatoryRisks, setRegulatoryRisks] = useState([]);
  const [foiaSignals, setFoaSignals] = useState([]);
  const [intelLoading, setIntelLoading] = useState(false);

  useEffect(() => {
    loadRecentPolicies();
    fetchRegulatoryIntelligence();
  }, []);

  // Fetch regulatory risk scores and FOIA signals
  const fetchRegulatoryIntelligence = async () => {
    try {
      setIntelLoading(true);
      
      // Fetch regulatory risks
      const riskPromises = REGULATORY_WATCH.map(async (company) => {
        try {
          const response = await fetch(`${BACKEND_URL}/api/regulatory/risk/${company.ticker}`);
          if (response.ok) {
            const data = await response.json();
            return { ...company, ...data };
          }
        } catch (err) {
          console.error(`Error fetching regulatory risk for ${company.ticker}:`, err);
        }
        return null;
      });

      const riskResults = await Promise.all(riskPromises);
      const validRisks = riskResults.filter(r => r !== null);
      setRegulatoryRisks(validRisks);

      // Fetch FOIA signals for healthcare companies
      const foiaPromises = REGULATORY_WATCH.filter(c => c.sector === 'Healthcare').map(async (company) => {
        try {
          const response = await fetch(`${BACKEND_URL}/api/foia/signals/${company.ticker}`);
          if (response.ok) {
            const data = await response.json();
            return { ticker: company.ticker, name: company.name, ...data };
          }
        } catch (err) {
          console.error(`Error fetching FOIA signals for ${company.ticker}:`, err);
        }
        return null;
      });

      const foiaResults = await Promise.all(foiaPromises);
      const validFoa = foiaResults.filter(f => f !== null);
      setFoaSignals(validFoa);

    } catch (error) {
      console.error('Error fetching regulatory intelligence:', error);
    } finally {
      setIntelLoading(false);
    }
  };

  const loadRecentPolicies = async () => {
    try {
      const response = await governmentAPI.get('/policy/recent');
      setRecentPolicies(response.policies || []);
    } catch (error) {
      console.error('Error loading policies:', error);
    } finally {
      setLoading(false);
    }
  };

  const testPolicyAnalysis = async () => {
    const testTitle = "FDA approves new mRNA vaccine fast-track approval process";
    try {
      const response = await governmentAPI.get(`/policy/analyze?title=${encodeURIComponent(testTitle)}`);
      setTestAnalysis(response);
    } catch (error) {
      console.error('Error analyzing policy:', error);
    }
  };

  const getImpactColor = (score) => {
    if (score >= 70) return 'red';
    if (score >= 40) return 'orange';
    return 'yellow';
  };

  const getSeverityLabel = (score) => {
    if (score >= 70) return { text: 'HIGH IMPACT', color: 'red' };
    if (score >= 40) return { text: 'MEDIUM IMPACT', color: 'orange' };
    return { text: 'LOW IMPACT', color: 'yellow' };
  };

  if (loading) {
    return (
      <Segment textAlign="center" padded>
        <Loader active inline="centered" size="large">Analyzing policies...</Loader>
      </Segment>
    );
  }

  return (
    <Container fluid style={{ padding: '20px' }}>
      <Header as="h1" icon textAlign="center">
        <Icon name="line graph" color="blue" />
        <Header.Content>
          🏛️ Policy Impact Predictor
          <Header.Subheader>
            AI-powered analysis of government policies & market impact
          </Header.Subheader>
        </Header.Content>
      </Header>

      {/* Test Analysis Demo */}
      <Segment raised color="blue" style={{ marginTop: '20px' }}>
        <Header as="h3">
          <Icon name="flask" />
          Try Demo Analysis
        </Header>
        <Button 
          color="green" 
          onClick={testPolicyAnalysis}
          icon="play"
          content="Analyze Sample Policy"
        />
        {testAnalysis && (
          <Message info style={{ marginTop: '15px' }}>
            <Message.Header>Analysis Result</Message.Header>
            <p><strong>Impact Score:</strong> {testAnalysis.impact_score}/100</p>
            <p><strong>Confidence:</strong> {testAnalysis.confidence}%</p>
            <p><strong>Sectors:</strong> {testAnalysis.affected_sectors.map(s => s.sector).join(', ')}</p>
          </Message>
        )}
      </Segment>

      {/* Regulatory Enforcement Early Warning System */}
      <Segment raised color="red" style={{ marginTop: '20px' }}>
        <Header as="h3">
          <Icon name="warning sign" />
          Regulatory Enforcement Early Warning System
          <Header.Subheader>
            Real-time monitoring of SEC, FDA, and other agency enforcement actions
          </Header.Subheader>
        </Header>

        {intelLoading ? (
          <Loader active inline />
        ) : (
          <Table compact selectable striped>
            <Table.Header>
              <Table.Row>
                <Table.HeaderCell>Company</Table.HeaderCell>
                <Table.HeaderCell>Sector</Table.HeaderCell>
                <Table.HeaderCell>Risk Score</Table.HeaderCell>
                <Table.HeaderCell>Risk Level</Table.HeaderCell>
                <Table.HeaderCell>SEC Actions</Table.HeaderCell>
                <Table.HeaderCell>FDA Actions</Table.HeaderCell>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {regulatoryRisks.map((risk, idx) => (
                <Table.Row key={idx}>
                  <Table.Cell>
                    <strong>{risk.name}</strong>
                    <Label size="mini" color="blue" style={{ marginLeft: '5px' }}>{risk.ticker}</Label>
                  </Table.Cell>
                  <Table.Cell>{risk.sector}</Table.Cell>
                  <Table.Cell>
                    <Statistic size="tiny">
                      <Statistic.Value color={risk.risk_score >= 70 ? 'red' : risk.risk_score >= 40 ? 'orange' : 'green'}>
                        {risk.risk_score}
                      </Statistic.Value>
                      <Statistic.Label>/100</Statistic.Label>
                    </Statistic>
                  </Table.Cell>
                  <Table.Cell>
                    <Label 
                      size="small" 
                      color={risk.risk_level === 'HIGH' ? 'red' : risk.risk_level === 'MEDIUM' ? 'orange' : 'green'}
                    >
                      {risk.risk_level}
                    </Label>
                  </Table.Cell>
                  <Table.Cell textAlign="center">
                    {risk.breakdown?.sec_risk_score > 0 ? (
                      <Label size="mini" color="orange">{risk.breakdown.sec_risk_score}</Label>
                    ) : (
                      <Label size="mini" color="green">0</Label>
                    )}
                  </Table.Cell>
                  <Table.Cell textAlign="center">
                    {risk.breakdown?.fda_risk_score > 0 ? (
                      <Label size="mini" color="orange">{risk.breakdown.fda_risk_score}</Label>
                    ) : (
                      <Label size="mini" color="green">0</Label>
                    )}
                  </Table.Cell>
                </Table.Row>
              ))}
            </Table.Body>
          </Table>
        )}
      </Segment>

      {/* FOIA Intelligence */}
      {foiaSignals.length > 0 && (
        <Segment raised color="purple" style={{ marginTop: '20px' }}>
          <Header as="h3">
            <Icon name="file text" />
            FOIA Intelligence Signals
            <Header.Subheader>
              Trading signals extracted from Freedom of Information Act document releases
            </Header.Subheader>
          </Header>

          <Grid columns={2} divided>
            <Grid.Row>
              {foiaSignals.map((foia, idx) => (
                <Grid.Column key={idx}>
                  <Card>
                    <Card.Content>
                      <Card.Header>{foia.name} ({foia.ticker})</Card.Header>
                      <Card.Meta>
                        {foia.total_documents} FOIA documents analyzed
                      </Card.Meta>
                      
                      <Divider />
                      
                      <Grid columns={3} textAlign="center">
                        <Grid.Column>
                          <Label color="red" size="small">
                            {foia.high_strength_signals} High
                          </Label>
                        </Grid.Column>
                        <Grid.Column>
                          <Label color="orange" size="small">
                            {foia.medium_strength_signals} Medium
                          </Label>
                        </Grid.Column>
                        <Grid.Column>
                          <Label color="yellow" size="small">
                            {foia.low_strength_signals} Low
                          </Label>
                        </Grid.Column>
                      </Grid>
                    </Card.Content>
                  </Card>
                </Grid.Column>
              ))}
            </Grid.Row>
          </Grid>
        </Segment>
      )}

      {/* Recent Policy Analyses */}
      <Header as="h2" style={{ marginTop: '30px' }}>
        <Icon name="clock outline" />
        Recent Policy Analyses
      </Header>

      {recentPolicies.length === 0 ? (
        <Message info>
          <Message.Header>No recent high-impact policies</Message.Header>
          <p>Policy analyses will appear here as government announcements are made.</p>
        </Message>
      ) : (
        <Grid stackable columns={2}>
          {recentPolicies.map((policy, index) => (
            <Grid.Column key={index}>
              <Card raised style={{ width: '100%' }}>
                <Card.Content>
                  <Card.Header>
                    {policy.article.title}
                  </Card.Header>
                  <Card.Meta>
                    <span>{policy.article.source}</span> • {new Date(policy.article.published_at).toLocaleDateString()}
                  </Card.Meta>
                  
                  <Divider />
                  
                  {/* Impact Score */}
                  <Statistic size="small" horizontal>
                    <Statistic.Value color={getImpactColor(policy.analysis.impact_score)}>
                      {policy.analysis.impact_score}
                    </Statistic.Value>
                    <Statistic.Label>Impact Score</Statistic.Label>
                  </Statistic>

                  <Label 
                    color={getSeverityLabel(policy.analysis.impact_score).color}
                    ribbon
                    style={{ marginTop: '10px' }}
                  >
                    {getSeverityLabel(policy.analysis.impact_score).text}
                  </Label>
                </Card.Content>

                <Card.Content extra>
                  {/* Affected Sectors */}
                  <Header as="h4">
                    <Icon name="industry" />
                    Affected Sectors
                  </Header>
                  <List>
                    {policy.analysis.affected_sectors.slice(0, 3).map((sector, idx) => (
                      <List.Item key={idx}>
                        <Icon name="checkmark" color="green" />
                        <List.Content>
                          {sector.sector} ({sector.match_count} matches)
                        </List.Content>
                      </List.Item>
                    ))}
                  </List>

                  <Divider />

                  {/* Affected Stocks */}
                  <Header as="h4">
                    <Icon name="dollar" />
                    Stocks to Watch
                  </Header>
                  <List horizontal link>
                    {policy.analysis.affected_stocks.slice(0, 5).map((stock, idx) => (
                      <List.Item key={idx}>
                        <Label size="small" color="blue">
                          {stock.symbol}
                        </Label>
                      </List.Item>
                    ))}
                  </List>

                  <Divider />

                  {/* Historical Patterns */}
                  {policy.analysis.matched_patterns.length > 0 && (
                    <>
                      <Header as="h4">
                        <Icon name="history" />
                        Historical Pattern
                      </Header>
                      <Message success>
                        <Message.Header>
                          {policy.analysis.matched_patterns[0].example}
                        </Message.Header>
                        <p>
                          Expected: {policy.analysis.matched_patterns[0].historical_impact}
                        </p>
                      </Message>
                    </>
                  )}

                  {/* Prediction */}
                  <Segment secondary style={{ marginTop: '15px' }}>
                    <Header as="h5">
                      <Icon name="lightbulb" />
                      AI Prediction
                    </Header>
                    <p><strong>Severity:</strong> {policy.analysis.prediction.severity}</p>
                    <p><strong>Timeframe:</strong> {policy.analysis.prediction.timeframe}</p>
                    <p><strong>Action:</strong> {policy.analysis.prediction.action}</p>
                    <p><strong>Confidence:</strong> {policy.analysis.confidence}%</p>
                  </Segment>

                  <Button 
                    fluid 
                    color="blue" 
                    icon="external"
                    content="Read Full Article"
                    onClick={() => window.open(policy.article.url, '_blank')}
                  />
                </Card.Content>
              </Card>
            </Grid.Column>
          ))}
        </Grid>
      )}

      {/* Sector Mappings Info */}
      <Segment secondary style={{ marginTop: '30px' }}>
        <Header as="h3">
          <Icon name="info circle" />
          How It Works
        </Header>
        <Grid columns={3} divided>
          <Grid.Column>
            <Header as="h4" textAlign="center">
              <Icon name="search" color="blue" />
              1. Policy Detection
            </Header>
            <p textAlign="center">
              AI scans government announcements and news for policy changes
            </p>
          </Grid.Column>
          <Grid.Column>
            <Header as="h4" textAlign="center">
              <Icon name="exchange" color="green" />
              2. Pattern Matching
            </Header>
            <p textAlign="center">
              Matches current policy to historical patterns & market reactions
            </p>
          </Grid.Column>
          <Grid.Column>
            <Header as="h4" textAlign="center">
              <Icon name="line graph" color="red" />
              3. Impact Prediction
            </Header>
            <p textAlign="center">
              Predicts which stocks/sectors will be affected and by how much
            </p>
          </Grid.Column>
        </Grid>
      </Segment>
    </Container>
  );
};

export default PolicyImpactDashboard;
