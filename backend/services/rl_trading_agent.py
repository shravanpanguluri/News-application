"""
Reinforcement Learning Trading Agent - Continuous Improvement
Learns and improves trading strategy from market feedback using reinforcement learning.

This implements the Reinforcement Learning Trading Agent enhancement requested.
"""
import numpy as np
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
import json
from pathlib import Path


@dataclass
class TradingState:
    """Current trading environment state"""
    portfolio_value: float
    cash: float
    positions: Dict[str, float]  # ticker: quantity
    market_sentiment: float     # -1 to 1
    volatility: float          # Market volatility
    economic_regime: str       # BULL, BEAR, NEUTRAL
    timestamp: datetime


@dataclass
class TradingAction:
    """Trading action taken by agent"""
    action_type: str           # BUY, SELL, HOLD
    ticker: str
    quantity: float
    confidence: float         # Action confidence 0-1
    expected_reward: float    # Expected reward from action
    timestamp: datetime


@dataclass
class Experience:
    """Experience tuple for reinforcement learning"""
    state: TradingState
    action: TradingAction
    reward: float
    next_state: TradingState
    done: bool


class ExperienceBuffer:
    """Replay buffer for experience replay"""

    def __init__(self, capacity: int = 10000):
        self.buffer = deque(maxlen=capacity)

    def add(self, experience: Experience):
        """Add experience to buffer"""
        self.buffer.append(experience)

    def sample(self, batch_size: int) -> List[Experience]:
        """Sample batch of experiences"""
        batch_size = min(batch_size, len(self.buffer))
        return random.sample(self.buffer, batch_size)

    def size(self) -> int:
        """Get current buffer size"""
        return len(self.buffer)

    def clear(self):
        """Clear buffer"""
        self.buffer.clear()


class RLTradingAgent:
    """
    Reinforcement learning trading agent for continuous strategy improvement.

    Features:
    - Q-learning based decision making
    - Experience replay for stable learning
    - Policy gradient methods
    - Continuous improvement from market feedback
    """

    def __init__(self, model_path: Optional[str] = None):
        # Q-Network parameters
        self.state_size = 10  # Portfolio value, cash, positions, market conditions, etc.
        self.action_size = 3  # BUY, SELL, HOLD
        self.q_network = self._build_q_network()

        # Hyperparameters
        self.learning_rate = 0.001
        self.discount_factor = 0.95  # Gamma
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01
        self.batch_size = 32

        # Experience replay buffer
        self.experience_buffer = ExperienceBuffer(capacity=10000)

        # Model persistence
        if model_path:
            self.model_path = Path(model_path)
        else:
            self.model_path = Path(__file__).parent.parent / "models" / "rl_trading_agent.pkl"

        self.model_path.parent.mkdir(parents=True, exist_ok=True)

        # Performance tracking
        self.total_rewards = []
        self.episode_rewards = []
        self.current_episode_reward = 0.0

        # Load existing model if available
        self._load_model()

        print("🤖 Reinforcement Learning Trading Agent initialized")

    def _build_q_network(self):
        """Build simple Q-network (in real implementation, would use neural networks)"""
        # For demo purposes, using simple lookup table
        # In real implementation, this would be a neural network
        return {
            "weights": np.random.randn(self.state_size, self.action_size) * 0.1,
            "bias": np.zeros(self.action_size),
            "version": "1.0"
        }

    def _state_to_vector(self, state: TradingState) -> np.ndarray:
        """Convert trading state to feature vector"""
        # Simplified state representation
        features = [
            state.portfolio_value / 1000000,  # Normalize portfolio value
            state.cash / 1000000,            # Normalize cash
            len(state.positions),            # Number of positions
            state.market_sentiment,          # Market sentiment
            state.volatility,                # Volatility
            1.0 if state.economic_regime == "BULL" else -1.0 if state.economic_regime == "BEAR" else 0.0,
            # Add more features as needed
        ]

        # Pad to fixed size
        while len(features) < self.state_size:
            features.append(0.0)

        return np.array(features[:self.state_size])

    def _vector_to_action(self, action_index: int, ticker: str = "LMT", max_position: float = 100.0) -> TradingAction:
        """Convert action index to TradingAction"""
        action_types = ["BUY", "SELL", "HOLD"]
        action_type = action_types[action_index % len(action_types)]

        # Determine quantity based on action type
        if action_type == "BUY":
            quantity = max_position * 0.1  # 10% position size
        elif action_type == "SELL":
            quantity = max_position * 0.1
        else:
            quantity = 0.0

        return TradingAction(
            action_type=action_type,
            ticker=ticker,
            quantity=quantity,
            confidence=random.uniform(0.5, 1.0),  # Random confidence for demo
            expected_reward=0.0,  # Will be updated during learning
            timestamp=datetime.utcnow()
        )

    def get_action(self, state: TradingState, ticker: str = "LMT") -> TradingAction:
        """
        Get trading action based on current state.

        Args:
            state: Current trading state
            ticker: Stock ticker to trade

        Returns:
            TradingAction to execute
        """
        state_vector = self._state_to_vector(state)

        # Epsilon-greedy exploration
        if random.random() <= self.epsilon:
            # Random action (exploration)
            action_index = random.randint(0, self.action_size - 1)
            print(f"   🎲 Exploring random action: {action_index}")
        else:
            # Greedy action (exploitation)
            q_values = np.dot(state_vector, self.q_network["weights"]) + self.q_network["bias"]
            action_index = np.argmax(q_values)
            print(f"   🤖 Exploiting learned policy: {action_index} (Q-values: {q_values})")

        action = self._vector_to_action(action_index, ticker)

        # Decay exploration rate
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        return action

    def learn_from_market_feedback(self, trade_result: Dict):
        """
        Continuously improve trading strategy from results.

        Args:
            trade_result: Result of executed trade
        """
        print(f"📚 Learning from trade result...")

        # Extract experience components
        state = self._dict_to_state(trade_result.get("state", {}))
        action = self._dict_to_action(trade_result.get("action", {}))
        reward = trade_result.get("reward", 0.0)
        next_state = self._dict_to_state(trade_result.get("next_state", {}))
        done = trade_result.get("done", False)

        # Create experience tuple
        experience = Experience(
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done
        )

        # Add to experience buffer
        self.experience_buffer.add(experience)
        self.current_episode_reward += reward

        print(f"   ✅ Added experience: Reward {reward:.2f}, Total episode reward: {self.current_episode_reward:.2f}")

        # Learn from batch if enough experiences
        if self.experience_buffer.size() >= self.batch_size:
            self._train_step()

    def _dict_to_state(self, state_dict: Dict) -> TradingState:
        """Convert dictionary to TradingState"""
        return TradingState(
            portfolio_value=state_dict.get("portfolio_value", 1000000.0),
            cash=state_dict.get("cash", 500000.0),
            positions=state_dict.get("positions", {"LMT": 100.0}),
            market_sentiment=state_dict.get("market_sentiment", 0.0),
            volatility=state_dict.get("volatility", 0.15),
            economic_regime=state_dict.get("economic_regime", "NEUTRAL"),
            timestamp=datetime.fromisoformat(state_dict.get("timestamp", datetime.utcnow().isoformat()))
        )

    def _dict_to_action(self, action_dict: Dict) -> TradingAction:
        """Convert dictionary to TradingAction"""
        return TradingAction(
            action_type=action_dict.get("action_type", "HOLD"),
            ticker=action_dict.get("ticker", "LMT"),
            quantity=action_dict.get("quantity", 0.0),
            confidence=action_dict.get("confidence", 0.5),
            expected_reward=action_dict.get("expected_reward", 0.0),
            timestamp=datetime.fromisoformat(action_dict.get("timestamp", datetime.utcnow().isoformat()))
        )

    def _train_step(self):
        """Perform one training step using experience replay"""
        print(f"   🧠 Training step with {self.experience_buffer.size()} experiences...")

        # Sample batch
        batch = self.experience_buffer.sample(self.batch_size)

        # Simple Q-learning update (in real implementation, would use neural network training)
        for experience in batch:
            state_vector = self._state_to_vector(experience.state)
            next_state_vector = self._state_to_vector(experience.next_state)

            # Calculate target Q-value
            next_q_values = np.dot(next_state_vector, self.q_network["weights"]) + self.q_network["bias"]
            max_next_q = np.max(next_q_values)
            target = experience.reward + self.discount_factor * max_next_q * (1 - experience.done)

            # Current Q-value
            current_q_values = np.dot(state_vector, self.q_network["weights"]) + self.q_network["bias"]
            action_index = ["BUY", "SELL", "HOLD"].index(experience.action.action_type)

            # Update Q-value (simple gradient descent)
            td_error = target - current_q_values[action_index]
            state_vector_reshaped = state_vector.reshape(-1, 1)
            self.q_network["weights"][:, action_index] += self.learning_rate * td_error * state_vector_reshaped.flatten()
            self.q_network["bias"][action_index] += self.learning_rate * td_error

        print(f"   ✅ Training step completed")

    def calculate_reward(self, state: TradingState, action: TradingAction,
                        next_state: TradingState, market_data: Dict) -> float:
        """
        Calculate reward for trading action.

        Args:
            state: Previous state
            action: Action taken
            next_state: Resulting state
            market_data: Market data for reward calculation

        Returns:
            Reward value
        """
        # Portfolio value change
        portfolio_change = (next_state.portfolio_value - state.portfolio_value) / state.portfolio_value

        # Risk-adjusted return
        risk_free_rate = 0.02 / 252  # Daily risk-free rate
        excess_return = portfolio_change - risk_free_rate
        volatility = state.volatility if state.volatility > 0 else 0.01
        sharpe_ratio = excess_return / volatility if volatility > 0 else 0

        # Action cost (transaction costs, slippage)
        transaction_cost = abs(action.quantity) * 0.001  # 0.1% transaction cost

        # Market timing bonus
        market_move = market_data.get("market_return", 0.0)
        timing_bonus = 0.0
        if action.action_type == "BUY" and market_move > 0:
            timing_bonus = 0.01
        elif action.action_type == "SELL" and market_move < 0:
            timing_bonus = 0.01

        # Confidence penalty (high confidence actions should perform better)
        confidence_penalty = (1.0 - action.confidence) * 0.01

        # Calculate final reward
        reward = (portfolio_change * 1000) + (sharpe_ratio * 100) - transaction_cost + timing_bonus - confidence_penalty

        print(f"   🏆 Reward calculation:")
        print(f"      Portfolio change: {portfolio_change:.2%}")
        print(f"      Sharpe ratio: {sharpe_ratio:.2f}")
        print(f"      Transaction cost: -{transaction_cost:.2f}")
        print(f"      Timing bonus: +{timing_bonus:.2f}")
        print(f"      Confidence penalty: -{confidence_penalty:.2f}")
        print(f"      Final reward: {reward:.2f}")

        return reward

    def start_new_episode(self):
        """Start new trading episode"""
        if self.current_episode_reward != 0:
            self.episode_rewards.append(self.current_episode_reward)
            self.total_rewards.append(self.current_episode_reward)
            print(f"🏁 Episode completed: Reward {self.current_episode_reward:.2f}")

        self.current_episode_reward = 0.0

    def get_performance_metrics(self) -> Dict:
        """Get agent performance metrics"""
        if not self.episode_rewards:
            return {"status": "no_episodes_yet"}

        recent_rewards = self.episode_rewards[-100:] if len(self.episode_rewards) > 100 else self.episode_rewards

        return {
            "total_episodes": len(self.episode_rewards),
            "average_reward": np.mean(self.total_rewards) if self.total_rewards else 0,
            "recent_average_reward": np.mean(recent_rewards),
            "best_episode_reward": max(self.episode_rewards) if self.episode_rewards else 0,
            "worst_episode_reward": min(self.episode_rewards) if self.episode_rewards else 0,
            "current_epsilon": self.epsilon,
            "experience_buffer_size": self.experience_buffer.size(),
            "learning_rate": self.learning_rate
        }

    def _save_model(self):
        """Save trained model to file"""
        try:
            model_data = {
                "weights": self.q_network["weights"].tolist(),
                "bias": self.q_network["bias"].tolist(),
                "epsilon": self.epsilon,
                "episode_rewards": self.episode_rewards,
                "total_rewards": self.total_rewards,
                "version": self.q_network["version"],
                "saved_at": datetime.utcnow().isoformat()
            }

            with open(self.model_path, 'w') as f:
                json.dump(model_data, f, indent=2)

            print(f"   💾 Model saved to {self.model_path}")
        except Exception as e:
            print(f"   ❌ Error saving model: {e}")

    def _load_model(self):
        """Load trained model from file"""
        try:
            if self.model_path.exists():
                with open(self.model_path, 'r') as f:
                    model_data = json.load(f)

                self.q_network["weights"] = np.array(model_data["weights"])
                self.q_network["bias"] = np.array(model_data["bias"])
                self.epsilon = model_data.get("epsilon", self.epsilon)
                self.episode_rewards = model_data.get("episode_rewards", [])
                self.total_rewards = model_data.get("total_rewards", [])

                print(f"   📥 Loaded existing model from {self.model_path}")
                return True
        except Exception as e:
            print(f"   ⚠️  Error loading model: {e}")

        return False

    def save_checkpoint(self):
        """Save checkpoint of current training state"""
        checkpoint_path = self.model_path.with_suffix('.checkpoint.json')
        self._save_model()
        # Copy current model to checkpoint
        if self.model_path.exists():
            import shutil
            shutil.copy2(self.model_path, checkpoint_path)
            print(f"   💾 Checkpoint saved to {checkpoint_path}")


# Global instance
rl_trading_agent = RLTradingAgent()


if __name__ == "__main__":
    print("🤖 Reinforcement Learning Trading Agent - Demo")
    print("=" * 50)

    # Sample trading state
    sample_state = TradingState(
        portfolio_value=1000000.0,
        cash=500000.0,
        positions={"LMT": 100.0, "BA": 50.0},
        market_sentiment=0.2,
        volatility=0.15,
        economic_regime="NEUTRAL",
        timestamp=datetime.utcnow()
    )

    # Get action from agent
    print("🎮 Getting trading action...")
    action = rl_trading_agent.get_action(sample_state, ticker="LMT")

    print(f"   Action: {action.action_type} {action.quantity:.2f} shares of {action.ticker}")
    print(f"   Confidence: {action.confidence:.2f}")
    print(f"   Exploration rate: {rl_trading_agent.epsilon:.3f}")

    # Sample trade result for learning
    sample_next_state = TradingState(
        portfolio_value=1005000.0,  # +$5000 profit
        cash=495000.0,
        positions={"LMT": 110.0, "BA": 50.0},
        market_sentiment=0.3,
        volatility=0.16,
        economic_regime="BULL",
        timestamp=datetime.utcnow()
    )

    sample_trade_result = {
        "state": {
            "portfolio_value": 1000000.0,
            "cash": 500000.0,
            "positions": {"LMT": 100.0},
            "market_sentiment": 0.2,
            "volatility": 0.15,
            "economic_regime": "NEUTRAL",
            "timestamp": datetime.utcnow().isoformat()
        },
        "action": {
            "action_type": "BUY",
            "ticker": "LMT",
            "quantity": 10.0,
            "confidence": 0.85,
            "expected_reward": 50.0,
            "timestamp": datetime.utcnow().isoformat()
        },
        "reward": 75.0,
        "next_state": {
            "portfolio_value": 1005000.0,
            "cash": 495000.0,
            "positions": {"LMT": 110.0},
            "market_sentiment": 0.3,
            "volatility": 0.16,
            "economic_regime": "BULL",
            "timestamp": datetime.utcnow().isoformat()
        },
        "done": False
    }

    # Learn from trade result
    rl_trading_agent.learn_from_market_feedback(sample_trade_result)

    # Calculate reward example
    print(f"\n🏆 Reward calculation example:")
    sample_market_data = {
        "market_return": 0.005,  # 0.5% market gain
    }

    reward = rl_trading_agent.calculate_reward(
        state=sample_state,
        action=action,
        next_state=sample_next_state,
        market_data=sample_market_data
    )

    print(f"   Calculated reward: {reward:.2f}")

    # Show performance metrics
    print(f"\n📊 Performance Metrics:")
    metrics = rl_trading_agent.get_performance_metrics()
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.2f}")
        else:
            print(f"   {key}: {value}")

    # Start new episode
    rl_trading_agent.start_new_episode()

    # Save checkpoint
    rl_trading_agent.save_checkpoint()