# -*- coding: utf-8 -*-
import os
import sys
import asyncio
import aiohttp
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from datetime import datetime
import json
import pytz

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

env_pairs = os.getenv('CRYPTO_PAIRS')
if env_pairs:
    PAIRS = [p.strip() for p in env_pairs.split(',')]
else:
    PAIRS = [
        'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT',
        'AVAX/USDT', 'DOT/USDT', 'LINK/USDT'
    ]

CACHE_FILE = 'crypto_cache.json'

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except Exception as e:
        print(f"Error saving cache: {e}")

async def send_telegram_alert_async(session, text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing Telegram bot token or Chat ID. Skipping notification.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                print(f"Telegram API Error: status {response.status}")
    except Exception as e:
        print(f"Error sending message to Telegram: {e}")

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def check_pinbar_4h(df_4h):
    if len(df_4h) < 1:
        return False, 0
    latest = df_4h.iloc[-1]
    open_p = latest['open']
    close_p = latest['close']
    high_p = latest['high']
    low_p = latest['low']
    
    total_range = high_p - low_p
    if total_range == 0:
        return False, 0
        
    body = abs(close_p - open_p)
    lower_wick = min(open_p, close_p) - low_p
    wick_percentage = (lower_wick / total_range) * 100
    
    is_pinbar = (wick_percentage >= 50) and (body / total_range <= 0.35)
    return is_pinbar, wick_percentage

async def analyze_crypto(exchange, symbol, session, cache, digest_lines):
    try:
        ohlcv_4h = await exchange.fetch_ohlcv(symbol, timeframe='4h', limit=100)
        ohlcv_1d = await exchange.fetch_ohlcv(symbol, timeframe='1d', limit=200)
        
        if not ohlcv_4h or not ohlcv_1d:
            return

        df_4h = pd.DataFrame(ohlcv_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_1d = pd.DataFrame(ohlcv_1d, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        df_4h['RSI'] = calculate_rsi(df_4h['close'], 14)
        latest_4h = df_4h.iloc[-1]
        rsi_4h = latest_4h['RSI']
        
        df_1d['SMA200'] = df_1d['close'].rolling(200).mean()
        latest_1d = df_1d.iloc[-1]
        
        is_above_sma = pd.notna(latest_1d['SMA200']) and latest_1d['close'] > latest_1d['SMA200']
        trend_1d_status = "Above 200 SMA" if is_above_sma else "Below 200 SMA"
        
        is_pinbar, wick_pct = check_pinbar_4h(df_4h)
        avg_vol = df_4h['volume'].tail(20).mean()
        vol_pct = (latest_4h['volume'] / avg_vol * 100) if avg_vol > 0 else 0
        vol_label = "High" if vol_pct >= 150 else "Standard"

        price = latest_4h['close']
        
        clean_symbol = symbol.replace('/', '')
        tv_url = f"https://www.tradingview.com/symbols/{clean_symbol}"
        clickable_symbol = f'<a href="{tv_url}"><b>{symbol}</b></a>'

        is_oversold = rsi_4h <= 35 and (pd.isna(latest_1d['SMA200']) or is_above_sma)
        
        if is_oversold:
            status_str = "Buy Signal"
        elif is_pinbar:
            status_str = f"Bullish Pinbar ({wick_pct:.0f}%)"
        else:
            status_str = "Neutral"

        # Unicode-safe formatting for bullet separator
        digest_item = (
            f"{clickable_symbol} \u2022 ${price:,.2f}\n"
            f"RSI (4H): {rsi_4h:.1f} | {trend_1d_status}\n"
            f"Status: {status_str}"
        )
        digest_lines.append(digest_item)

        if is_oversold:
            last_alert = cache.get(f"ALERT_{symbol}")
            today_str = datetime.now().strftime('%Y-%m-%d')
            
            if last_alert != today_str:
                pinbar_text = f"Pinbar (>= 50%)" if is_pinbar else "No Pinbar"
                
                msg = (
                    f"🚀 <b>BULLISH CRYPTO BUY</b>\n\n"
                    f"🪙 <b>Pair:</b> {clickable_symbol}\n"
                    f"💵 <b>Price:</b> ${price:,.2f}\n"
                    f"📊 <b>RSI (4H):</b> {rsi_4h:.2f}\n"
                    f"📈 <b>Trend (1D):</b> {trend_1d_status}\n"
                    f"🎯 <b>Demand Candle:</b> {pinbar_text}\n"
                    f"🔊 <b>Volume:</b> {vol_pct:.0f}% of Avg ({vol_label})\n\n"
                    f"📈 Check Chart:\n"
                    f"🔗 <a href=\"{tv_url}\">View Chart on TradingView</a>"
                )
                await send_telegram_alert_async(session, msg)
                cache[f"ALERT_{symbol}"] = today_str

    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")

async def main():
    cache = load_cache()
    digest_lines = []
    
    exchange = ccxt.kraken({'enableRateLimit': True})
    
    async with aiohttp.ClientSession() as session:
        tasks = [analyze_crypto(exchange, pair, session, cache, digest_lines) for pair in PAIRS]
        await asyncio.gather(*tasks)
        await exchange.close()
        
        tz = pytz.timezone('Europe/London')
        local_now = datetime.now(tz)
        today_str = local_now.strftime('%Y-%m-%d')
        
        github_event = os.getenv('GITHUB_EVENT_NAME', '')
        
        if github_event == 'schedule':
            should_send_digest = (local_now.hour >= 21 and cache.get('DIGEST_DATE') != today_str)
            is_scheduled_run = True
        else:
            should_send_digest = True
            is_scheduled_run = False

        if should_send_digest and digest_lines:
            digest_msg = '📋 <b>DAILY MARKET DIGEST (CRYPTO)</b>\n\n' + '\n\n'.join(digest_lines)
            await send_telegram_alert_async(session, digest_msg)
            
            if is_scheduled_run and local_now.hour >= 21:
                cache['DIGEST_DATE'] = today_str

    save_cache(cache)

if __name__ == '__main__':
    asyncio.run(main())
