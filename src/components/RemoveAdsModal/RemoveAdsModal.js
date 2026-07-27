import React, { useState } from 'react';
import { Modal, Button, Header, Segment, Icon, Message } from 'semantic-ui-react';
import './RemoveAdsModal.css';

const RemoveAdsModal = ({ open, onClose, onSubscribe }) => {
	const [loading, setLoading] = useState(false);

	const handleSubscribe = async () => {
		setLoading(true);
		// Simulate payment processing and grant premium access
		setTimeout(() => {
			localStorage.setItem('tier', 'pro');
			localStorage.setItem('hasPremium', 'true');
			onSubscribe();
			setLoading(false);
			onClose();
		}, 1000);
	};

	return (
		<Modal open={open} onClose={onClose} size="small" className="remove-ads-modal">
			<Modal.Header>
				<Icon name="check circle" color="green" />
				Remove All Ads
			</Modal.Header>
			<Modal.Content>
				<Segment className="pricing-segment">
					<div className="pricing-header">
						<Icon name="star" size="huge" color="yellow" />
						<h2>Premium</h2>
					</div>
					<div className="pricing-amount">
						<span className="currency">$</span>
						<span className="amount">1.99</span>
						<span className="period">/month</span>
					</div>
					<div className="pricing-features">
						<div className="feature">
							<Icon name="check" color="green" />
							No banner ads
						</div>
						<div className="feature">
							<Icon name="check" color="green" />
							No interstitial ads
							</div>
						<div className="feature">
							<Icon name="check" color="green" />
							No native ads
						</div>
						<div className="feature">
							<Icon name="check" color="green" />
							Faster page loads
						</div>
						<div className="feature">
							<Icon name="check" color="green" />
							Premium support
						</div>
					</div>
				</Segment>

				<Message info>
					<Message.Header>Secure Payment</Message.Header>
					<p>
						Payment will be processed securely. Cancel anytime.
						This is a demo - no actual payment will be charged.
					</p>
				</Message>
			</Modal.Content>
			<Modal.Actions>
				<Button onClick={onClose} disabled={loading}>
					Cancel
				</Button>
				<Button
					color="green"
					onClick={handleSubscribe}
					loading={loading}
					className="subscribe-button"
				>
					<Icon name="credit card" />
					Subscribe Now - $1.99/month
				</Button>
			</Modal.Actions>
		</Modal>
	);
};

export default RemoveAdsModal;
