import React, { useState } from 'react';
import { Modal, Button, Form, Message, Icon, Label } from 'semantic-ui-react';
import { authAPI } from '../../API/governmentApi';

const LoginModal = ({ open, onClose, onLoginSuccess }) => {
	const [isLogin, setIsLogin] = useState(true);
	const [email, setEmail] = useState('');
	const [password, setPassword] = useState('');
	const [error, setError] = useState('');
	const [loading, setLoading] = useState(false);

	const handleSubmit = async () => {
		setLoading(true);
		setError('');

		try {
			let result;
			if (isLogin) {
				result = await authAPI.login(email, password);
				if (result.success) {
					onLoginSuccess();
					onClose();
				} else {
					setError(result.error);
				}
			} else {
				result = await authAPI.register(email, password, 'free');
				if (result) {
					// Auto-login after register
					const loginResult = await authAPI.login(email, password);
					if (loginResult.success) {
						onLoginSuccess();
						onClose();
					}
				}
			}
		} catch (err) {
			setError('Something went wrong. Please try again.');
		} finally {
			setLoading(false);
		}
	};

	return (
		<Modal open={open} onClose={onClose} size="small">
			<Modal.Header>{isLogin ? 'Login' : 'Register'}</Modal.Header>
			<Modal.Content>
				<Form onSubmit={handleSubmit}>
					<Form.Input
						label="Email"
						type="email"
						placeholder="your@email.com"
						value={email}
						onChange={(e) => setEmail(e.target.value)}
						required
					/>
					<Form.Input
						label="Password"
						type="password"
						placeholder="********"
						value={password}
						onChange={(e) => setPassword(e.target.value)}
						required
						minLength={6}
					/>
					{error && (
						<Message negative>
							<Message.Header>Error</Message.Header>
							<p>{error}</p>
						</Message>
					)}
					<Message info>
						<Message.Header>Test Accounts (Pass: password123)</Message.Header>
						<div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginTop: '5px' }}>
							<Label size="small" color="blue">admin@govpulse.com (Enterprise)</Label>
							<Label size="small" color="green">user@govpulse.com (Pro)</Label>
							<Label size="small">free@govpulse.com (Free)</Label>
						</div>
					</Message>
				</Form>
			</Modal.Content>
			<Modal.Actions>
				<Button onClick={onClose} disabled={loading}>
					Cancel
				</Button>
				<Button
					color="blue"
					onClick={handleSubmit}
					loading={loading}
					disabled={!email || !password}
				>
					<Icon name={isLogin ? 'sign in' : 'user plus'} />
					{isLogin ? 'Login' : 'Register'}
				</Button>
				<Button
					basic
					color="blue"
					onClick={() => {
						setIsLogin(!isLogin);
						setError('');
					}}
				>
					{isLogin
						? "Don't have an account? Register"
						: 'Already have an account? Login'}
				</Button>
			</Modal.Actions>
		</Modal>
	);
};

export default LoginModal;
