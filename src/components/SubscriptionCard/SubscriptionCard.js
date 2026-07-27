import React from 'react';
import { Card, Button, Icon, List } from 'semantic-ui-react';

const SubscriptionCard = ({ plan, currentTier, onUpgrade }) => {
	const isCurrentTier = currentTier === plan.name.toLowerCase();
	const isPopular = plan.name === 'Pro';

	return (
		<Card
			fluid
			style={{
				border: isCurrentTier ? '2px solid #2185d0' : '1px solid #ddd',
				position: 'relative',
				boxShadow: isPopular ? '0 4px 12px rgba(0,0,0,0.15)' : '0 2px 8px rgba(0,0,0,0.1)',
			}}
		>
			<Card.Content>
				{isPopular && (
					<div
						style={{
							position: 'absolute',
							top: '-10px',
							right: '20px',
							background: '#2185d0',
							color: 'white',
							padding: '5px 10px',
							borderRadius: '3px',
							fontSize: '12px',
							fontWeight: 'bold',
						}}
					>
						MOST POPULAR
					</div>
				)}

				<Card.Header
					style={{ fontSize: '24px', fontWeight: 'bold', textAlign: 'center' }}
				>
					{plan.name}
				</Card.Header>

				<Card.Meta style={{ textAlign: 'center', marginTop: '10px' }}>
					{plan.price === 0 ? (
						<span style={{ fontSize: '32px', fontWeight: 'bold' }}>Free</span>
					) : (
						<>
							<span style={{ fontSize: '32px', fontWeight: 'bold' }}>
								₹{plan.price}
							</span>
							<span style={{ color: '#666' }}>/month</span>
						</>
					)}
				</Card.Meta>

				<Card.Description style={{ marginTop: '20px' }}>
					<List bulleted verticalAlign="middle">
						{plan.features.map((feature, index) => (
							<List.Item key={index} style={{ padding: '8px 0' }}>
								<Icon name="check" color="green" />
								{feature}
							</List.Item>
						))}
					</List>
				</Card.Description>
			</Card.Content>

			<Card.Content extra>
				<Button
					fluid
					color={isCurrentTier ? 'green' : isPopular ? 'blue' : 'grey'}
					disabled={isCurrentTier}
					onClick={() => onUpgrade(plan.name.toLowerCase())}
				>
					{isCurrentTier ? 'Current Plan' : 'Upgrade'}
				</Button>
			</Card.Content>
		</Card>
	);
};

export default SubscriptionCard;
