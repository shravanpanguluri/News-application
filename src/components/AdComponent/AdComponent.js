import React, { useState } from 'react';
import { Segment, Icon, Button, Header, Image, Grid } from 'semantic-ui-react';
import './AdComponent.css';

const ADS_CONTENT = {
    banner: {
        title: "Master the Markets with Bloomberg Terminal",
        subtitle: "The ultimate tool for financial intelligence and real-time data.",
        cta: "Start Free Trial",
        icon: "chart line",
        color: "linear-gradient(135deg, #000 0%, #333 100%)"
    },
    native: {
        title: "AWS for Government: Scale Safely",
        subtitle: "Cloud infrastructure that meets compliance and security standards.",
        cta: "Learn More",
        icon: "cloud",
        color: "linear-gradient(135deg, #ff9900 0%, #232f3e 100%)"
    },
    interstitial: {
        title: "Unlock Predovex PRO",
        subtitle: "Get unlimited API access, real-time alerts, and deep-dive policy analytics.",
        cta: "Upgrade to Pro",
        icon: "star",
        color: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    }
};

const AdComponent = ({ type = 'banner', onClose }) => {
    const [isClosed, setIsClosed] = useState(false);
    const content = ADS_CONTENT[type] || ADS_CONTENT.banner;

    const handleClose = (e) => {
        if (e) e.stopPropagation();
        setIsClosed(true);
        if (onClose) onClose();
    };

    if (isClosed) return null;

    if (type === 'banner') {
        return (
            <Segment className="ad-banner">
                <div className="ad-label">
                    <Icon name="add square" /> Advertisement
                </div>
                <div className="ad-content">
                    <div className="ad-placeholder" style={{ background: content.color }}>
                        <Icon name={content.icon} size="huge" style={{ marginBottom: '10px' }} />
                        <div>
                            <Header as="h3" inverted style={{ margin: 0 }}>{content.title}</Header>
                            <p className="ad-note">{content.subtitle}</p>
                        </div>
                        <Button color="orange" size="small" style={{ marginLeft: '20px' }}>{content.cta}</Button>
                    </div>
                </div>
                <Button
                    icon="close"
                    size="tiny"
                    className="ad-close"
                    onClick={handleClose}
                />
            </Segment>
        );
    }

    if (type === 'native') {
        return (
            <Segment className="ad-native" onClick={() => window.open('https://aws.amazon.com/government/', '_blank')}>
                <div className="ad-label">
                    <Icon name="add square" /> Sponsored
                </div>
                <Grid columns={2} stackable verticalAlign="middle">
                    <Grid.Column width={12}>
                        <Header as="h3">
                            <Icon name={content.icon} color="orange" />
                            <Header.Content>
                                {content.title}
                                <Header.Subheader>{content.subtitle}</Header.Subheader>
                            </Header.Content>
                        </Header>
                    </Grid.Column>
                    <Grid.Column width={4} textAlign="right">
                        <Button basic color="blue" fluid>{content.cta}</Button>
                    </Grid.Column>
                </Grid>
            </Segment>
        );
    }

    if (type === 'interstitial') {
        return (
            <div className="ad-interstitial-overlay">
                <div className="ad-interstitial">
                    <div className="ad-label">
                        <Icon name="add square" /> Special Offer
                    </div>
                    <div className="ad-interstitial-placeholder" style={{ background: content.color }}>
                        <Icon name={content.icon} size="huge" style={{ fontSize: '5rem', marginBottom: '20px' }} />
                        <Header as="h1" inverted style={{ fontSize: '2.5rem' }}>{content.title}</Header>
                        <p style={{ fontSize: '1.2rem', opacity: 0.9 }}>{content.subtitle}</p>
                        <Button 
                            color="yellow" 
                            size="huge" 
                            style={{ marginTop: '30px' }}
                            onClick={() => window.open('/subscription', '_blank')}
                        >
                            <Icon name="rocket" /> {content.cta}
                        </Button>
                    </div>
                    <Button
                        basic
                        inverted
                        className="ad-close-interstitial"
                        onClick={handleClose}
                    >
                        Skip Ad in 3s... (or Close Now)
                    </Button>
                </div>
            </div>
        );
    }

    return null;
};

export default AdComponent;
