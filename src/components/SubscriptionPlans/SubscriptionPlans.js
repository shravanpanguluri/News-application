import React, { useState, useEffect } from 'react';
import { Container, Grid, Segment, Header, Dimmer, Loader, Icon } from 'semantic-ui-react';
import SubscriptionCard from '../SubscriptionCard/SubscriptionCard';
import { subscriptionAPI } from '../../API/governmentApi';
import './SubscriptionPlans.css';

const SubscriptionPlans = ({ currentTier = 'free', onUpgrade }) => {
	const [plans, setPlans] = useState([]);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		loadPlans();
	}, []);

	const loadPlans = async () => {
		try {
			const data = await subscriptionAPI.getPlans();
			setPlans(data);
		} catch (error) {
			console.error('Error loading plans:', error);
			setPlans([
				{
					name: 'Free',
					price: 0,
					currency: 'INR',
					features: [
						'Basic news feed',
						'Email alerts',
						'Mobile app access',
						'50 items/day limit',
					],
					daily_limit: 50,
				},
				{
					name: 'Pro',
					price: 199,
					currency: 'INR',
					features: [
						'Real-time alerts',
						'Advanced analytics',
						'API access',
						'Historical data',
						'5000 items/day',
					],
					daily_limit: 5000,
				},
				{
					name: 'Enterprise',
					price: 999,
					currency: 'INR',
					features: [
						'Custom alerts',
						'Webhook integrations',
						'Dedicated support',
						'Unlimited usage',
						'SLA guarantee',
					],
					daily_limit: -1,
				},
			]);
		}
		setLoading(false);
	};

	if (loading) {
		return (
			<Dimmer active inverted>
				<Loader inverted>Loading Plans</Loader>
			</Dimmer>
		);
	}

	return (
		<Container className="subscription-container">
			<Header
				as="h2"
				textAlign="center"
				className="subscription-title"
			>
				Choose Your Plan
			</Header>
			<Header
				as="h3"
				textAlign="center"
				color="grey"
				className="subscription-subtitle"
			>
				Access government intelligence from India & US
			</Header>

			<div className="subscription-grid">
				{plans.map((plan, index) => (
					<div key={index} className="subscription-card-item">
						<SubscriptionCard
							plan={plan}
							currentTier={currentTier}
							onUpgrade={onUpgrade}
						/>
					</div>
				))}
			</div>

			<Segment textAlign="center" className="subscription-features">
				<Header as="h4" color="grey">
					All plans include:
				</Header>
				<Grid columns={3} centered>
					<Grid.Column>
						<Icon name="newspaper" color="blue" size="big" />
						<p>Government News</p>
					</Grid.Column>
					<Grid.Column>
						<Icon name="chart line" color="green" size="big" />
						<p>Analytics</p>
					</Grid.Column>
					<Grid.Column>
						<Icon name="bell" color="red" size="big" />
						<p>Alerts</p>
					</Grid.Column>
				</Grid>
			</Segment>
		</Container>
	);
};

export default SubscriptionPlans;
