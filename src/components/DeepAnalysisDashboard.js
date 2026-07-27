import React, { useState, useEffect } from 'react';
import {
  Container,
  Header,
  Segment,
  Grid,
  Card,
  Statistic,
  Table,
  Label,
  Icon,
  Loader,
  Message,
  Tab,
  Button,
  Input,
  Divider,
  Progress,
  Accordion,
  List,
  Flag
} from 'semantic-ui-react';
import axios from 'axios';
import moment from 'moment';

import { BACKEND_URL } from '../API/governmentApi';

const API_BASE_URL = BACKEND_URL;

const DeepAnalysisDashboard = ({ initialTicker = '' }) => {
  const [ticker, setTicker] = useState(initialTicker || 'AAPL');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [activeAccordion, setActiveAccordion] = useState(null);

  useEffect(() => {
    if (initialTicker) {
      fetchAnalysis(initialTicker);
    }
  }, [initialTicker]);

  const fetchAnalysis = async (tickerSymbol) => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/analysis/deep/${tickerSymbol.toUpperCase()}`);
      console.log('Deep analysis response:', response.data);
      setAnalysis(response.data);
    } catch (err) {
      console.error('Analysis fetch error:', err);
      setError(err.response?.data?.detail || 'Failed to fetch analysis');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    if (ticker.trim()) {
      fetchAnalysis(ticker.trim().toUpperCase());
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const getRatingColor = (score) => {
    if (score >= 80) return 'green';
    if (score >= 65) return 'olive';
    if (score >= 50) return 'yellow';
    if (score >= 35) return 'orange';
    return 'red';
  };

  const getRatingLabel = (score) => {
    if (score >= 80) return 'Strong Buy';
    if (score >= 65) return 'Buy';
    if (score >= 50) return 'Hold';
    if (score >= 35) return 'Sell';
    return 'Strong Sell';
  };

  const renderOverallRating = () => {
    console.log('renderOverallRating called, analysis:', analysis);
    console.log('overall_rating exists:', !!analysis?.overall_rating);
    
    // Handle case where overall_rating might be missing or incomplete
    if (!analysis?.overall_rating) {
      console.log('overall_rating is null/undefined, returning fallback');
      // Create a fallback rating based on available data
      const financialScore = analysis?.financial_breakdown?.health_score || 50;
      const moatScore = (analysis?.moat_analysis?.overall_moat_rating || 5) * 10;
      const growthScore = analysis?.growth_potential?.overall_growth_potential || 50;
      const riskScore = analysis?.risk_analysis?.overall_risk_score 
        ? 100 - analysis.risk_analysis.overall_risk_score 
        : 50;
      
      const overallScore = Math.round(
        financialScore * 0.25 + 
        50 * 0.25 + 
        riskScore * 0.20 + 
        moatScore * 0.15 + 
        growthScore * 0.15
      );
      
      return (
        <Segment color={getRatingColor(overallScore)} raised>
          <Grid columns={2} divided>
            <Grid.Column>
              <Header as="h2" textAlign="center">
                <Icon name="info circle" />
                {getRatingLabel(overallScore)}
              </Header>
              <Statistic centered>
                <Statistic.Value>{overallScore}</Statistic.Value>
                <Statistic.Label>Overall Score (Estimated)</Statistic.Label>
              </Statistic>
            </Grid.Column>
            <Grid.Column>
              <Header as="h3">Component Scores</Header>
              <Progress percent={financialScore} color="blue" label="Financial Health" />
              <Progress percent={50} color="green" label="Valuation" />
              <Progress percent={riskScore} color="orange" label="Risk-Adjusted" />
              <Progress percent={moatScore} color="purple" label="Moat Strength" />
              <Progress percent={growthScore} color="teal" label="Growth Potential" />
            </Grid.Column>
          </Grid>
        </Segment>
      );
    }
    
    const { overall_score, rating, component_scores } = analysis.overall_rating;
    console.log('Rendering rating:', overall_score, rating, component_scores);

    return (
      <Segment color={getRatingColor(overall_score)} raised>
        <Grid columns={2} divided>
          <Grid.Column>
            <Header as="h2" textAlign="center">
              <Icon name={rating.includes('Buy') ? 'arrow up' : rating.includes('Sell') ? 'arrow down' : 'minus'} />
              {rating}
            </Header>
            <Statistic centered>
              <Statistic.Value>{overall_score}</Statistic.Value>
              <Statistic.Label>Overall Score</Statistic.Label>
            </Statistic>
          </Grid.Column>
          <Grid.Column>
            <Header as="h3">Component Scores</Header>
            {component_scores && (
              <>
                <Progress percent={component_scores.financial_health || 50} color="blue" label="Financial Health" />
                <Progress percent={component_scores.valuation || 50} color="green" label="Valuation" />
                <Progress percent={component_scores.risk_adjusted || 50} color="orange" label="Risk-Adjusted" />
                <Progress percent={component_scores.moat_strength || 50} color="purple" label="Moat Strength" />
                <Progress percent={component_scores.growth_potential || 50} color="teal" label="Growth Potential" />
              </>
            )}
          </Grid.Column>
        </Grid>
      </Segment>
    );
  };

  const renderFinancialBreakdown = () => {
    console.log('renderFinancialBreakdown called, financial_breakdown:', analysis?.financial_breakdown);
    
    // Handle missing financial data
    if (!analysis?.financial_breakdown) {
      return (
        <Segment>
          <Header as="h2">
            <Icon name="line graph" />
            Financial Breakdown (5-Year Analysis)
          </Header>
          <Message warning>
            <Message.Header>Financial Data Unavailable</Message.Header>
            <p>Unable to retrieve financial data for {ticker}. This may be due to API limitations or missing data from the source.</p>
          </Message>
        </Segment>
      );
    }
    
    const { financial_data, health_score, health_rating, summary } = analysis.financial_breakdown;
    console.log('financial_data keys:', financial_data ? Object.keys(financial_data) : 'null');

    return (
      <Segment>
        <Header as="h2">
          <Icon name="line graph" />
          Financial Breakdown (5-Year Analysis)
        </Header>
        <Message info>
          <Message.Header>Financial Health: {health_rating || 'N/A'}</Message.Header>
          <p>Score: {health_score || 'N/A'}/100</p>
          <p>{summary || 'Financial analysis based on available data'}</p>
        </Message>

        <Grid columns={2} stackable>
          {financial_data?.revenue && (
            <Grid.Column>
              <Card fluid>
                <Card.Content>
                  <Card.Header>Revenue Growth</Card.Header>
                  <Card.Meta>Trend: {financial_data.revenue.trend || 'N/A'}</Card.Meta>
                  <Card.Description>
                    <Statistic size="small">
                      <Statistic.Value>{financial_data.revenue.latest || 'N/A'}</Statistic.Value>
                      <Statistic.Label>Latest Revenue</Statistic.Label>
                    </Statistic>
                    <p>Avg Growth Rate: {financial_data.revenue.avg_growth_rate || 'N/A'}%</p>
                    <p>CAGR: {financial_data.revenue.cagr || 'N/A'}%</p>
                  </Card.Description>
                </Card.Content>
              </Card>
            </Grid.Column>
          )}

          {financial_data?.net_income && (
            <Grid.Column>
              <Card fluid>
                <Card.Content>
                  <Card.Header>Net Income</Card.Header>
                  <Card.Meta>Trend: {financial_data.net_income.trend || 'N/A'}</Card.Meta>
                  <Card.Description>
                    <Statistic size="small">
                      <Statistic.Value>{financial_data.net_income.latest || 'N/A'}</Statistic.Value>
                      <Statistic.Label>Latest Net Income</Statistic.Label>
                    </Statistic>
                    <p>Avg Growth Rate: {financial_data.net_income.avg_growth_rate || 'N/A'}%</p>
                  </Card.Description>
                </Card.Content>
              </Card>
            </Grid.Column>
          )}

          {financial_data?.free_cash_flow && (
            <Grid.Column>
              <Card fluid>
                <Card.Content>
                  <Card.Header>Free Cash Flow</Card.Header>
                  <Card.Meta>Trend: {financial_data.free_cash_flow.trend || 'N/A'}</Card.Meta>
                  <Card.Description>
                    <p>Latest: {financial_data.free_cash_flow.latest || 'N/A'}</p>
                    <p>Average: {financial_data.free_cash_flow.average || 'N/A'}</p>
                  </Card.Description>
                </Card.Content>
              </Card>
            </Grid.Column>
          )}

          {financial_data?.profit_margins && (
            <Grid.Column>
              <Card fluid>
                <Card.Content>
                  <Card.Header>Profit Margins</Card.Header>
                  <Card.Meta>Trend: {financial_data.profit_margins.trend || 'N/A'}</Card.Meta>
                  <Card.Description>
                    <p>Latest Margin: {financial_data.profit_margins.latest_margin || 'N/A'}%</p>
                    <p>Avg Margin: {financial_data.profit_margins.avg_margin || 'N/A'}%</p>
                  </Card.Description>
                </Card.Content>
              </Card>
            </Grid.Column>
          )}

          {financial_data?.debt && (
            <Grid.Column>
              <Card fluid>
                <Card.Content>
                  <Card.Header>Debt Levels</Card.Header>
                  <Card.Meta>Trend: {financial_data.debt.trend || 'N/A'}</Card.Meta>
                  <Card.Description>
                    <p>Latest Debt: {financial_data.debt.latest_debt || 'N/A'}</p>
                    <p>Debt-to-Assets: {financial_data.debt.debt_to_assets || 'N/A'}%</p>
                  </Card.Description>
                </Card.Content>
              </Card>
            </Grid.Column>
          )}

          {financial_data?.return_on_equity && (
            <Grid.Column>
              <Card fluid>
                <Card.Content>
                  <Card.Header>Return on Equity</Card.Header>
                  <Card.Meta>Rating: {financial_data.return_on_equity.rating || 'N/A'}</Card.Meta>
                  <Card.Description>
                    <p>Latest ROE: {financial_data.return_on_equity.latest_roe || 'N/A'}%</p>
                    <p>Avg ROE: {financial_data.return_on_equity.avg_roe || 'N/A'}%</p>
                  </Card.Description>
                </Card.Content>
              </Card>
            </Grid.Column>
          )}
        </Grid>
      </Segment>
    );
  };

  const renderValuationAnalysis = () => {
    if (!analysis?.valuation_analysis) {
      return (
        <Segment>
          <Header as="h2">
            <Icon name="money bill alternate" />
            Valuation Analysis
          </Header>
          <Message warning>
            <Message.Header>Valuation Data Unavailable</Message.Header>
            <p>Unable to retrieve valuation data for {ticker}.</p>
          </Message>
        </Segment>
      );
    }
    
    const { current_price, valuation_metrics, conclusion, summary } = analysis.valuation_analysis;

    return (
      <Segment>
        <Header as="h2">
          <Icon name="money bill alternate" />
          Valuation Analysis
        </Header>
        <Message success>
          <Message.Header>Current Price: ${current_price || 'N/A'}</Message.Header>
          <p>{summary || 'Valuation analysis based on available data'}</p>
        </Message>

        <Grid columns={2} stackable>
          {valuation_metrics?.pe_analysis && (
            <Grid.Column>
              <Card fluid>
                <Card.Content>
                  <Card.Header>P/E Ratio Analysis</Card.Header>
                  <Card.Description>
                    <Table compact>
                      <Table.Body>
                        <Table.Row>
                          <Table.Cell><strong>Trailing P/E</strong></Table.Cell>
                          <Table.Cell>{valuation_metrics.pe_analysis.trailing_pe || 'N/A'}</Table.Cell>
                        </Table.Row>
                        <Table.Row>
                          <Table.Cell><strong>Forward P/E</strong></Table.Cell>
                          <Table.Cell>{valuation_metrics.pe_analysis.forward_pe || 'N/A'}</Table.Cell>
                        </Table.Row>
                        <Table.Row>
                          <Table.Cell><strong>Industry Avg</strong></Table.Cell>
                          <Table.Cell>{valuation_metrics.pe_analysis.industry_avg_pe || 'N/A'}</Table.Cell>
                        </Table.Row>
                        <Table.Row>
                          <Table.Cell><strong>vs Industry</strong></Table.Cell>
                          <Table.Cell>
                            <Label color={valuation_metrics.pe_analysis.vs_industry === 'Undervalued' ? 'green' : 'red'}>
                              {valuation_metrics.pe_analysis.vs_industry || 'N/A'}
                            </Label>
                          </Table.Cell>
                        </Table.Row>
                      </Table.Body>
                    </Table>
                  </Card.Description>
                </Card.Content>
              </Card>
            </Grid.Column>
          )}

          {valuation_metrics?.dcf_valuation && (
            <Grid.Column>
              <Card fluid>
                <Card.Content>
                  <Card.Header>DCF Valuation</Card.Header>
                  <Card.Description>
                    <Statistic size="small">
                      <Statistic.Value>${valuation_metrics.dcf_valuation.dcf_value_per_share || 'N/A'}</Statistic.Value>
                      <Statistic.Label>DCF Value per Share</Statistic.Label>
                    </Statistic>
                    <p>
                      Upside/Downside:
                      <Label color={valuation_metrics.dcf_valuation.upside_downside > 0 ? 'green' : 'red'}>
                        {valuation_metrics.dcf_valuation.upside_downside || 0}%
                      </Label>
                    </p>
                    <p>
                      Verdict:
                      <Label color={valuation_metrics.dcf_valuation.verdict === 'Undervalued' ? 'green' : valuation_metrics.dcf_valuation.verdict === 'Overvalued' ? 'red' : 'yellow'}>
                        {valuation_metrics.dcf_valuation.verdict || 'N/A'}
                      </Label>
                    </p>
                    {valuation_metrics.dcf_valuation.assumptions && (
                      <>
                        <p><strong>Assumptions:</strong></p>
                        <ul>
                          <li>Growth Rate: {valuation_metrics.dcf_valuation.assumptions.growth_rate || 'N/A'}</li>
                          <li>Terminal Growth: {valuation_metrics.dcf_valuation.assumptions.terminal_growth || 'N/A'}</li>
                          <li>Discount Rate: {valuation_metrics.dcf_valuation.assumptions.discount_rate || 'N/A'}</li>
                        </ul>
                      </>
                    )}
                  </Card.Description>
                </Card.Content>
              </Card>
            </Grid.Column>
          )}
        </Grid>
      </Segment>
    );
  };

  const renderRiskAnalysis = () => {
    if (!analysis?.risk_analysis) {
      return (
        <Segment>
          <Header as="h2">
            <Icon name="warning sign" />
            Risk Analysis
          </Header>
          <Message warning>
            <Message.Header>Risk Data Unavailable</Message.Header>
            <p>Unable to retrieve risk analysis data for {ticker}.</p>
          </Message>
        </Segment>
      );
    }
    
    const { risks, overall_risk_score, risk_level, summary } = analysis.risk_analysis;

    return (
      <Segment>
        <Header as="h2">
          <Icon name="warning sign" />
          Risk Analysis
        </Header>
        <Message warning>
          <Message.Header>Overall Risk: {risk_level || 'N/A'}</Message.Header>
          <p>Score: {overall_risk_score || 'N/A'}/100</p>
          <p>{summary || 'Risk analysis based on available data'}</p>
        </Message>

        {risks && risks.length > 0 ? (
          <Table celled>
            <Table.Header>
              <Table.Row>
                <Table.HeaderCell>Rank</Table.HeaderCell>
                <Table.HeaderCell>Risk Type</Table.HeaderCell>
                <Table.HeaderCell>Description</Table.HeaderCell>
                <Table.HeaderCell>Severity</Table.HeaderCell>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {risks.map((risk, index) => (
                <Table.Row key={index}>
                  <Table.Cell><strong>#{risk.rank || index + 1}</strong></Table.Cell>
                  <Table.Cell>{risk.risk_type || 'N/A'}</Table.Cell>
                  <Table.Cell>{risk.description || 'N/A'}</Table.Cell>
                  <Table.Cell>
                    <Label color={risk.severity === 'High' ? 'red' : risk.severity === 'Medium' ? 'orange' : 'green'}>
                      {risk.severity || 'N/A'} ({risk.severity_score || 'N/A'})
                    </Label>
                  </Table.Cell>
                </Table.Row>
              ))}
            </Table.Body>
          </Table>
        ) : (
          <Message info>
            <p>No specific risk data available for {ticker}.</p>
          </Message>
        )}
      </Segment>
    );
  };

  const renderEarningsBreakdown = () => {
    if (!analysis?.earnings_breakdown) {
      return (
        <Segment>
          <Header as="h2">
            <Icon name="calendar check" />
            Earnings Breakdown
          </Header>
          <Message warning>
            <Message.Header>Earnings Data Unavailable</Message.Header>
            <p>Unable to retrieve earnings data for {ticker}.</p>
          </Message>
        </Segment>
      );
    }
    
    const { report_date, earnings_data, summary } = analysis.earnings_breakdown;

    return (
      <Segment>
        <Header as="h2">
          <Icon name="calendar check" />
          Earnings Breakdown
        </Header>
        <Message info>
          <Message.Header>Report Date: {report_date ? moment(report_date).format('MMM DD, YYYY') : 'N/A'}</Message.Header>
          <p>{summary || 'Earnings analysis based on available data'}</p>
        </Message>

        <Grid columns={2} stackable>
          {earnings_data?.eps && (
            <Grid.Column>
              <Card fluid>
                <Card.Content>
                  <Card.Header>EPS Performance</Card.Header>
                  <Card.Description>
                    <Table compact>
                      <Table.Body>
                        <Table.Row>
                          <Table.Cell><strong>Estimate</strong></Table.Cell>
                          <Table.Cell>${earnings_data.eps.estimate || 'N/A'}</Table.Cell>
                        </Table.Row>
                        <Table.Row>
                          <Table.Cell><strong>Reported</strong></Table.Cell>
                          <Table.Cell>${earnings_data.eps.reported || 'N/A'}</Table.Cell>
                        </Table.Row>
                        <Table.Row>
                          <Table.Cell><strong>Surprise</strong></Table.Cell>
                          <Table.Cell>
                            <Label color={earnings_data.eps.surprise_pct > 0 ? 'green' : 'red'}>
                              {earnings_data.eps.surprise_pct || 0}%
                            </Label>
                          </Table.Cell>
                        </Table.Row>
                        <Table.Row>
                          <Table.Cell><strong>Result</strong></Table.Cell>
                          <Table.Cell>
                            <Label color={earnings_data.eps.beat_miss === 'Beat' ? 'green' : 'red'}>
                              {earnings_data.eps.beat_miss || 'N/A'}
                            </Label>
                          </Table.Cell>
                        </Table.Row>
                      </Table.Body>
                    </Table>
                  </Card.Description>
                </Card.Content>
              </Card>
            </Grid.Column>
          )}

          {earnings_data?.market_reaction && (
            <Grid.Column>
              <Card fluid>
                <Card.Content>
                  <Card.Header>Market Reaction</Card.Header>
                  <Card.Description>
                    <Statistic size="small">
                      <Statistic.Value color={earnings_data.market_reaction.direction === 'Positive' ? 'green' : 'red'}>
                        {earnings_data.market_reaction.price_reaction || 'N/A'}%
                      </Statistic.Value>
                      <Statistic.Label>Price Reaction</Statistic.Label>
                    </Statistic>
                    <p>Direction: {earnings_data.market_reaction.direction || 'N/A'}</p>
                  </Card.Description>
                </Card.Content>
              </Card>
            </Grid.Column>
          )}
        </Grid>
      </Segment>
    );
  };

  const renderMoatAnalysis = () => {
    if (!analysis?.moat_analysis) {
      return (
        <Segment>
          <Header as="h2">
            <Icon name="shield" />
            Competitive Moat Analysis
          </Header>
          <Message warning>
            <Message.Header>Moat Data Unavailable</Message.Header>
            <p>Unable to retrieve moat analysis data for {ticker}.</p>
          </Message>
        </Segment>
      );
    }
    
    const { moat_components, overall_moat_rating, moat_rating_label, summary } = analysis.moat_analysis;

    return (
      <Segment>
        <Header as="h2">
          <Icon name="shield" />
          Competitive Moat Analysis
        </Header>
        <Message success>
          <Message.Header>Moat Rating: {moat_rating_label || 'N/A'}</Message.Header>
          <p>Overall Score: {overall_moat_rating || 'N/A'}/10</p>
          <p>{summary || 'Moat analysis based on available data'}</p>
        </Message>

        {moat_components && Object.keys(moat_components).length > 0 ? (
          <Grid columns={2} stackable>
            {Object.entries(moat_components).map(([key, value]) => (
              <Grid.Column key={key}>
                <Card fluid>
                  <Card.Content>
                    <Card.Header>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</Card.Header>
                    <Card.Description>
                      <Progress
                        percent={(value?.score || 0) * 10}
                        color={(value?.score || 0) >= 7 ? 'green' : (value?.score || 0) >= 5 ? 'yellow' : 'red'}
                        label={`Score: ${value?.score || 'N/A'}/10`}
                      />
                      <p><strong>{value?.assessment || 'N/A'}</strong></p>
                      <p>{value?.evidence || 'No evidence available'}</p>
                    </Card.Description>
                  </Card.Content>
                </Card>
              </Grid.Column>
            ))}
          </Grid>
        ) : (
          <Message info>
            <p>No moat component data available for {ticker}.</p>
          </Message>
        )}
      </Segment>
    );
  };

  const renderGrowthPotential = () => {
    if (!analysis?.growth_potential) {
      return (
        <Segment>
          <Header as="h2">
            <Icon name="trend up" />
            Growth Potential Analysis
          </Header>
          <Message warning>
            <Message.Header>Growth Data Unavailable</Message.Header>
            <p>Unable to retrieve growth potential data for {ticker}.</p>
          </Message>
        </Segment>
      );
    }
    
    const { growth_factors, growth_estimates, overall_growth_potential, summary } = analysis.growth_potential;

    return (
      <Segment>
        <Header as="h2">
          <Icon name="trend up" />
          Growth Potential Analysis
        </Header>
        <Message info>
          <Message.Header>Growth Potential: {overall_growth_potential || 'N/A'}/100</Message.Header>
          <p>{summary || 'Growth analysis based on available data'}</p>
        </Message>

        <Grid columns={2} stackable>
          <Grid.Column>
            <Card fluid>
              <Card.Content>
                <Card.Header>Growth Estimates</Card.Header>
                <Card.Description>
                  {growth_estimates ? (
                    <Statistic.Group widths={2}>
                      <Statistic>
                        <Statistic.Value>{growth_estimates.five_year_growth || 'N/A'}%</Statistic.Value>
                        <Statistic.Label>5-Year Growth</Statistic.Label>
                      </Statistic>
                      <Statistic>
                        <Statistic.Value>{growth_estimates.ten_year_growth || 'N/A'}%</Statistic.Value>
                        <Statistic.Label>10-Year Growth</Statistic.Label>
                      </Statistic>
                    </Statistic.Group>
                  ) : (
                    <p>No growth estimates available</p>
                  )}
                  <p>Confidence: {growth_estimates?.confidence || 'N/A'}</p>
                </Card.Description>
              </Card.Content>
            </Card>
          </Grid.Column>

          <Grid.Column>
            <Card fluid>
              <Card.Content>
                <Card.Header>Growth Drivers</Card.Header>
                <Card.Description>
                  {growth_factors && Object.keys(growth_factors).length > 0 ? (
                    <List>
                      {Object.entries(growth_factors).map(([key, value]) => (
                        <List.Item key={key}>
                          <List.Icon name="check circle" color="green" />
                          <List.Content>
                            <List.Header>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</List.Header>
                            <List.Description>{value?.assessment || JSON.stringify(value) || 'No assessment available'}</List.Description>
                          </List.Content>
                        </List.Item>
                      ))}
                    </List>
                  ) : (
                    <p>No growth drivers available</p>
                  )}
                </Card.Description>
              </Card.Content>
            </Card>
          </Grid.Column>
        </Grid>
      </Segment>
    );
  };

  const renderInstitutionalPerspective = () => {
    if (!analysis?.institutional_perspective) {
      return (
        <Segment>
          <Header as="h2">
            <Icon name="building" />
            Institutional Investor Perspective
          </Header>
          <Message warning>
            <Message.Header>Institutional Data Unavailable</Message.Header>
            <p>Unable to retrieve institutional perspective for {ticker}.</p>
          </Message>
        </Segment>
      );
    }
    
    const { institutional_perspective, summary } = analysis.institutional_perspective;

    return (
      <Segment>
        <Header as="h2">
          <Icon name="building" />
          Institutional Investor Perspective
        </Header>
        <Message info>
          <p>{summary || 'Institutional perspective based on available data'}</p>
        </Message>

        <Grid columns={2} stackable>
          <Grid.Column>
            <Card fluid>
              <Card.Content>
                <Card.Header><Icon name="check" color="green" /> Why Institutions BUY</Card.Header>
                <Card.Description>
                  {institutional_perspective?.buy_reasons && institutional_perspective.buy_reasons.length > 0 ? (
                    <List bulleted>
                      {institutional_perspective.buy_reasons.map((reason, idx) => (
                        <List.Item key={idx}>{reason}</List.Item>
                      ))}
                    </List>
                  ) : (
                    <p>No buy reasons available</p>
                  )}
                </Card.Description>
              </Card.Content>
            </Card>
          </Grid.Column>

          <Grid.Column>
            <Card fluid>
              <Card.Content>
                <Card.Header><Icon name="times" color="red" /> Why Institutions AVOID</Card.Header>
                <Card.Description>
                  {institutional_perspective?.avoid_reasons && institutional_perspective.avoid_reasons.length > 0 ? (
                    <List bulleted>
                      {institutional_perspective.avoid_reasons.map((reason, idx) => (
                        <List.Item key={idx}>{reason}</List.Item>
                      ))}
                    </List>
                  ) : (
                    <p>No avoid reasons available</p>
                  )}
                </Card.Description>
              </Card.Content>
            </Card>
          </Grid.Column>

          <Grid.Column>
            <Card fluid>
              <Card.Content>
                <Card.Header>Key Catalysts</Card.Header>
                <Card.Description>
                  {institutional_perspective?.catalysts && institutional_perspective.catalysts.length > 0 ? (
                    <List bulleted>
                      {institutional_perspective.catalysts.map((catalyst, idx) => (
                        <List.Item key={idx}>{catalyst}</List.Item>
                      ))}
                    </List>
                  ) : (
                    <p>No catalysts available</p>
                  )}
                </Card.Description>
              </Card.Content>
            </Card>
          </Grid.Column>

          <Grid.Column>
            <Card fluid>
              <Card.Content>
                <Card.Header>Investment Thesis</Card.Header>
                <Card.Description>
                  <p>{institutional_perspective?.investment_thesis || 'No investment thesis available'}</p>
                </Card.Description>
              </Card.Content>
            </Card>
          </Grid.Column>
        </Grid>
      </Segment>
    );
  };

  const renderBullBearDebate = () => {
    if (!analysis?.bull_bear_debate) {
      return (
        <Segment>
          <Header as="h2">
            <Icon name="balance scale" />
            Bull vs Bear Debate
          </Header>
          <Message warning>
            <Message.Header>Debate Data Unavailable</Message.Header>
            <p>Unable to retrieve bull/bear debate data for {ticker}.</p>
          </Message>
        </Segment>
      );
    }
    
    const { bull_case, bear_case, conclusion, verdict } = analysis.bull_bear_debate;

    return (
      <Segment>
        <Header as="h2">
          <Icon name="balance scale" />
          Bull vs Bear Debate
        </Header>
        <Message color={verdict === 'Bullish' ? 'green' : verdict === 'Bearish' ? 'red' : 'yellow'}>
          <Message.Header>Verdict: {verdict || 'Neutral'}</Message.Header>
          <p>{conclusion || 'Debate analysis based on available data'}</p>
        </Message>

        <Grid columns={2} stackable>
          <Grid.Column>
            <Card fluid color="green">
              <Card.Content>
                <Card.Header>
                  <Icon name="arrow up" color="green" />
                  Bull Case (Strength: {bull_case?.strength_score || 'N/A'})
                </Card.Header>
                <Card.Description>
                  {bull_case?.arguments && bull_case.arguments.length > 0 ? (
                    bull_case.arguments.map((arg, idx) => (
                      <Segment key={idx} compact>
                        <p><strong>{arg.point || 'N/A'}</strong></p>
                        <p>{arg.evidence || 'No evidence available'}</p>
                      </Segment>
                    ))
                  ) : (
                    <p>No bull arguments available</p>
                  )}
                </Card.Description>
              </Card.Content>
            </Card>
          </Grid.Column>

          <Grid.Column>
            <Card fluid color="red">
              <Card.Content>
                <Card.Header>
                  <Icon name="arrow down" color="red" />
                  Bear Case (Strength: {bear_case?.strength_score || 'N/A'})
                </Card.Header>
                <Card.Description>
                  {bear_case?.arguments && bear_case.arguments.length > 0 ? (
                    bear_case.arguments.map((arg, idx) => (
                      <Segment key={idx} compact>
                        <p><strong>{arg.point || 'N/A'}</strong></p>
                        <p>{arg.evidence || 'No evidence available'}</p>
                      </Segment>
                    ))
                  ) : (
                    <p>No bear arguments available</p>
                  )}
                </Card.Description>
              </Card.Content>
            </Card>
          </Grid.Column>
        </Grid>
      </Segment>
    );
  };

  const panes = [
    {
      menuItem: 'Overview',
      render: () => {
        console.log('Overview tab rendering');
        return (
        <Tab.Pane>
          {renderOverallRating()}
          <Grid columns={2} stackable>
            <Grid.Column>
              {renderFinancialBreakdown()}
            </Grid.Column>
            <Grid.Column>
              {renderValuationAnalysis()}
            </Grid.Column>
          </Grid>
        </Tab.Pane>
      )}
    },
    {
      menuItem: 'Financials',
      render: () => <Tab.Pane>{renderFinancialBreakdown()}</Tab.Pane>
    },
    {
      menuItem: 'Valuation',
      render: () => <Tab.Pane>{renderValuationAnalysis()}</Tab.Pane>
    },
    {
      menuItem: 'Risks',
      render: () => <Tab.Pane>{renderRiskAnalysis()}</Tab.Pane>
    },
    {
      menuItem: 'Earnings',
      render: () => <Tab.Pane>{renderEarningsBreakdown()}</Tab.Pane>
    },
    {
      menuItem: 'Moat',
      render: () => <Tab.Pane>{renderMoatAnalysis()}</Tab.Pane>
    },
    {
      menuItem: 'Growth',
      render: () => <Tab.Pane>{renderGrowthPotential()}</Tab.Pane>
    },
    {
      menuItem: 'Institutional',
      render: () => <Tab.Pane>{renderInstitutionalPerspective()}</Tab.Pane>
    },
    {
      menuItem: 'Bull/Bear',
      render: () => <Tab.Pane>{renderBullBearDebate()}</Tab.Pane>
    }
  ];

  if (loading) {
    return (
      <Container text style={{ marginTop: '2em', textAlign: 'center' }}>
        <Loader active size="massive">Analyzing {ticker}...</Loader>
      </Container>
    );
  }

  if (error) {
    return (
      <Container text style={{ marginTop: '2em' }}>
        <Message error>
          <Message.Header>Error</Message.Header>
          <p>{error}</p>
        </Message>
      </Container>
    );
  }

  return (
    <Container style={{ marginTop: '2em' }}>
      <Header as="h1" dividing>
        <Icon name="chart line" />
        Wall Street-Style Stock Analysis
      </Header>

      <Segment>
        <Input
          fluid
          size="large"
          placeholder="Enter stock ticker (e.g., AAPL, TSLA, MSFT)"
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
          onKeyPress={handleKeyPress}
          action={
            <Button color="blue" onClick={handleSearch}>
              <Icon name="search" />
              Analyze
            </Button>
          }
        />
      </Segment>

      {analysis && (
        <>
          <Message info>
            <Message.Header>{analysis.ticker || ticker}</Message.Header>
            <p>Analysis Date: {analysis.analysis_date ? moment(analysis.analysis_date).format('MMM DD, YYYY') : 'N/A'}</p>
            {analysis.error && (
              <>
                <p><strong>Note:</strong> {analysis.error}</p>
                <p>Showing partial data where available.</p>
              </>
            )}
          </Message>

          {console.log('Rendering tabs, analysis keys:', Object.keys(analysis))}
          {console.log('Tab panes count:', panes.length)}

          <Tab
            panes={panes}
            activeIndex={activeTab}
            onTabChange={(e, { activeIndex }) => setActiveTab(activeIndex)}
            renderActiveOnly={true}
          />

          <Segment secondary>
            <Message warning>
              <Message.Header>Disclaimer</Message.Header>
              <p>{analysis.disclaimer || 'This is not financial advice. Analysis is based on publicly available data and AI-generated insights. Always conduct your own research before investing.'}</p>
            </Message>
          </Segment>
        </>
      )}
    </Container>
  );
};

export default DeepAnalysisDashboard;
