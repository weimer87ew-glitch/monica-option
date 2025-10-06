# train_worker.py
import os
import time
import json
import numpy as np
import pandas as pd
import requests
from tensorflow import keras
from tensorflow.keras import layers
import random

STATUS_FILE = "status.json"

def write_status(d):
    with open(STATUS_FILE, "w") as f:
        json.dump(d, f)

# --- Telegram helper (optional) ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print("Telegram send failed:", e)

# --- Simulate candles ---
def generate_candles(n=10000, start_price=1.1):
    prices = [start_price]
    for _ in range(n-1):
        change = np.random.normal(0, 0.0005)
        prices.append(prices[-1] + change)
    df = pd.DataFrame({
        "open": prices[:-1],
        "close": prices[1:],
        "high": [max(o,c)+abs(np.random.normal(0,0.0003)) for o,c in zip(prices[:-1], prices[1:])],
        "low":  [min(o,c)-abs(np.random.normal(0,0.0003)) for o,c in zip(prices[:-1], prices[1:])]
    })
    return df.reset_index(drop=True)

# --- Simple Market Env ---
class MarketEnv:
    def __init__(self, df):
        self.df = df
        self.index = 0

    def reset(self):
        self.index = 0
        return self._state()

    def _state(self):
        # small window of returns as state
        start = max(0, self.index - 9)
        window = self.df["close"].iloc[start:self.index+1].pct_change().fillna(0).values
        # pad to 10
        if len(window) < 10:
            window = np.concatenate([np.zeros(10 - len(window)), window])
        return window.astype(np.float32)

    def step(self, action):
        # action: 0 hold, 1 call, 2 put
        done = False
        if self.index >= len(self.df)-2:
            done = True
            return self._state(), 0, done
        price_now = self.df.loc[self.index, "close"]
        price_next = self.df.loc[self.index+1, "close"]
        if action == 1:  # call: profit if next > now
            reward = 1 if price_next > price_now else -1
        elif action == 2:  # put
            reward = 1 if price_next < price_now else -1
        else:
            reward = 0
        self.index += 1
        return self._state(), float(reward), done

# --- Simple DQN Agent ---
class DQNAgent:
    def __init__(self, state_size=10, action_size=3):
        self.state_size = state_size
        self.action_size = action_size
        self.model = self._build_model()
        self.gamma = 0.95
        self.epsilon = 1.0
        self.eps_min = 0.05
        self.eps_decay = 0.995

    def _build_model(self):
        model = keras.Sequential([
            layers.Input(shape=(self.state_size,)),
            layers.Dense(64, activation="relu"),
            layers.Dense(64, activation="relu"),
            layers.Dense(self.action_size, activation="linear")
        ])
        model.compile(optimizer=keras.optimizers.Adam(1e-3), loss="mse")
        return model

    def act(self, state):
        if random.random() < self.epsilon:
            return random.randrange(self.action_size)
        q = self.model.predict(state.reshape(1,-1), verbose=0)[0]
        return int(np.argmax(q))

    def train_step(self, state, action, reward, next_state):
        target = reward + self.gamma * np.max(self.model.predict(next_state.reshape(1,-1), verbose=0)[0])
        q_vals = self.model.predict(state.reshape(1,-1), verbose=0)
        q_vals[0][action] = target
        self.model.fit(state.reshape(1,-1), q_vals, verbose=0)
        if self.epsilon > self.eps_min:
            self.epsilon *= self.eps_decay

# --- Training loop ---
def run_training(episodes=300, candles=10000):
    df = generate_candles(n=candles)
    env = MarketEnv(df)
    agent = DQNAgent()
    rewards_log = []
    start_time = time.time()
    for ep in range(1, episodes+1):
        state = env.reset()
        total = 0
        done = False
        while not done:
            action = agent.act(state)
            next_state, reward, done = env.step(action)
            agent.train_step(state, action, reward, next_state)
            state = next_state
            total += reward
        rewards_log.append(total)

        # every N episodes: write status & optionally notify
        if ep % 10 == 0 or ep == 1 or ep == episodes:
            status = {
                "episode": ep,
                "last_reward": total,
                "avg_reward_10": float(np.mean(rewards_log[-10:])),
                "epsilon": float(agent.epsilon),
                "elapsed_s": int(time.time() - start_time)
            }
            write_status(status)
            msg = f"Episode {ep}: last={total}, avg10={status['avg_reward_10']:.2f}, eps={status['epsilon']:.3f}"
            print(msg)
            send_telegram(msg)

    # final save
    write_status({"finished": True, "episodes": episodes, "rewards": rewards_log[-50:]})
    send_telegram(f"Training finished: {episodes} episodes. last={rewards_log[-1] if rewards_log else 'na'}")

if __name__ == "__main__":
    # keep alive loop: restart training if terminated (simple)
    try:
        run_training(episodes=300, candles=10000)
    except Exception as e:
        write_status({"error": str(e)})
        send_telegram("Trainer crashed: " + str(e))
        raise
