# Polymarket Position Monitor 🦅

A lightweight Python bot that monitors a specific Polymarket wallet's positions and sends real-time alerts to Telegram when changes are detected (new positions, increases, or decreases).

## Features

- **Real-time Monitoring**: Tracks the `/positions` endpoint of the Polymarket Data API.
- **State Tracking**: Compares current positions with the last known state to detect changes.
- **Telegram Alerts**: Sends detailed notifications with emojis for:
  - 🆕 New Positions
  - 📈 Position Increases (Buying more shares)
  - 📉 Position Decreases (Selling shares)
- **Smart Filtering**: Ignores negligible changes (dust) to avoid spam.

## Prerequisites

- Python 3.10+
- A Telegram Bot Token and Chat ID.
- The Wallet Address you want to monitor.

## Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd polymarket-api
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the root directory:
   ```env
   TELEGRAM_TOKEN=your_telegram_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   TARGET_WALLET=0x...  # The wallet address to monitor
   ```

## Usage

Run the bot manually:
```bash
python src/bot.py
```

On the first run, it will detect all current positions and send alerts for them (to establish a baseline). Subsequent runs will only alert on changes.

## Deployment (GitHub Actions)

This repository includes a GitHub Actions workflow (`.github/workflows/monitor.yml`) configured to run the bot every 5 minutes.

To enable it:
1. Go to your repository **Settings** > **Secrets and variables** > **Actions**.
2. Add the following repository secrets:
   - `TELEGRAM_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `TARGET_WALLET`

## Project Structure

- `src/bot.py`: Main logic for fetching positions and sending alerts.
- `last_positions.json`: Local cache file to store the last known state of positions (created automatically).
- `requirements.txt`: Python dependencies.
