import React from 'react';
import { Segment, Header, Icon, List, Label, Button } from 'semantic-ui-react';

const TOOLS = [
    {
        name: "Interactive Brokers",
        description: "Lowest margin rates & global access.",
        icon: "chart bar",
        color: "blue",
        payout: "$100/signup",
        url: "https://www.interactivebrokers.com/"
    },
    {
        name: "Proton Mail",
        description: "Encrypted email for government work.",
        icon: "lock",
        color: "purple",
        payout: "$20/signup",
        url: "https://proton.me/"
    },
    {
        name: "TradingView Pro",
        description: "Advanced charting for policy impacts.",
        icon: "line graph",
        color: "black",
        payout: "$30/referral",
        url: "https://www.tradingview.com/"
    }
];

const MarketToolsWidget = () => {
    return (
        <Segment raised style={{ marginTop: '20px', borderTop: '4px solid #2185d0' }}>
            <Header as="h4">
                <Icon name="cog" color="grey" />
                <Header.Content>
                    Professional Bureau Tools
                    <Header.Subheader>Recommended by GovPulse Bureau</Header.Subheader>
                </Header.Content>
            </Header>
            <List divided relaxed>
                {TOOLS.map((tool, idx) => (
                    <List.Item key={idx} style={{ padding: '10px 0' }}>
                        <List.Content>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                <Header as="h5" style={{ margin: 0 }}>
                                    <Icon name={tool.icon} color={tool.color} />
                                    {tool.name}
                                </Header>
                                <Label size="mini" color="green" basic>OFFER</Label>
                            </div>
                            <List.Description style={{ fontSize: '0.85rem', marginTop: '5px' }}>
                                {tool.description}
                            </List.Description>
                            <Button 
                                fluid 
                                size="mini" 
                                color={tool.color} 
                                style={{ marginTop: '8px' }}
                                onClick={() => window.open(tool.url, '_blank')}
                            >
                                Activate Access
                            </Button>
                        </List.Content>
                    </List.Item>
                ))}
            </List>
            <p style={{ fontSize: '0.7rem', color: '#999', marginTop: '10px', textAlign: 'center' }}>
                <Icon name="info circle" /> Affiliate partners support our bureau.
            </p>
        </Segment>
    );
};

export default MarketToolsWidget;
