# -*- coding: utf-8 -*-
import os
import sys
import asyncio
import aiohttp
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

env_stocks = os.getenv('STOCKS')
if env_stocks:
    STOCKS = [s.strip() for s in env_stocks.split(',')]
else:
    STOCKS = ['MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'V', 'JPM']

CURRENCY_SYMBOLS = {
    'USD': '$',
    'EUR': '\u20ac',
    'GBP': '\u00a3',
    'GBp': 'p'
}

async def send_telegram_message(session, message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing Telegram bot token or Chat ID.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    async with session.post(url, json=payload) as resp:
        if resp.status != 200:
            print(f"Error sending message: {await resp.text()}")

def calculate_indicators(df):
    if len(df) < 200:
        return None, None
    
    ema200 = df['Close'].ewm(span=200, adjust=False).mean().iloc[-1]
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    rsi_val = rsi.iloc[-1]
    
    return ema200, rsi_val

async def main():
    async with aiohttp.ClientSession() as session:
        messages = [" <b>CURRENT MARKET STATUS (STOCKS - GLOBAL)</b>\n"]
        
        for ticker in STOCKS:
            try:
                stock = yf.Ticker(ticker)
                df = stock.history(period="1y")
                if df.empty:
                    continue
                
                price = df['Close'].iloc[-1]
                currency = stock.info.get('currency', 'USD')
                symbol = CURRENCY_SYMBOLS.get(currency, currency)
                
                ema200, rsi = calculate_indicators(df)
                if ema200 is None or pd.isna(rsi):
                    continue
                
                ema_status = " Above 200 EMA" if price > ema200 else " Below 200 EMA"
                
                # Interactive TradingView HTML hyperlink
                clean_ticker = ticker.replace('.', '')
                tv_url = f"https://www.tradingview.com/symbols/{clean_ticker}"
                clickable_ticker = f'<a href="{tv_url}"><b>{ticker}</b></a>'
                
                msg = (
                    f" {clickable_ticker} \u2022 {symbol}{price:.2f}\n"
                    f" RSI (1D): {rsi:.2f} | {ema_status}\n"
                    f" Status:  Neutral"
                )
                messages.append(msg)
            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}")
        
        if len(messages) > 1:
            full_message = "\n\n".join(messages)
            await send_telegram_message(session, full_message)

if __name__ == "__main__":
    asyncio.run(main())
