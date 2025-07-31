import os
import requests
import pandas as pd
import time
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


SYMBOLS = ["SOLUSDT", "ETHUSDT", "BTCUSDT", "ADAUSDT"]
INTERVAL = "1h"
LIMIT = 100

# Diccionario para guardar última señal enviada
last_signals = {}


def get_klines(symbol, interval, limit):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame(
        data,
        columns=["t", "o", "h", "l", "c", "v", "_", "_", "_", "_", "_", "_"])
    df["close"] = df["c"].astype(float)
    return df


def analyze(df):
    if len(df) < 20:
        return "No hay suficientes datos para analizar."

    rsi_series = RSIIndicator(df["close"], window=14).rsi()
    if len(rsi_series) < 1:
        return "RSI no disponible."
    rsi = rsi_series.iloc[-1]

    macd_ind = MACD(df["close"])
    macd_line_series = macd_ind.macd()
    signal_line_series = macd_ind.macd_signal()
    if len(macd_line_series) < 2 or len(signal_line_series) < 2:
        return "MACD no disponible."

    macd_line = macd_line_series.iloc[-1]
    signal_line = signal_line_series.iloc[-1]

    macd_cross_up = macd_line > signal_line and macd_line_series.iloc[
        -2] < signal_line_series.iloc[-2]
    macd_cross_down = macd_line < signal_line and macd_line_series.iloc[
        -2] > signal_line_series.iloc[-2]

    ema_9_series = EMAIndicator(df["close"], window=9).ema_indicator()
    ema_21_series = EMAIndicator(df["close"], window=21).ema_indicator()
    if len(ema_9_series) < 1 or len(ema_21_series) < 1:
        return "EMA no disponible."

    ema_9 = ema_9_series.iloc[-1]
    ema_21 = ema_21_series.iloc[-1]

    crossover_up = ema_9 > ema_21
    crossover_down = ema_9 < ema_21

    if rsi < 30 and macd_cross_up and crossover_up:
        return f"📈 COMPRA: RSI={rsi:.2f}, MACD cruzó ↑, EMA9>EMA21"
    elif rsi > 70 and macd_cross_down and crossover_down:
        return f"📉 VENTA: RSI={rsi:.2f}, MACD cruzó ↓, EMA9<EMA21"
    else:
        return f"⏳ No hay señal clara. RSI={rsi:.2f}"


def send_telegram_message(token, chat_id, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}
    requests.post(url, data=data)


def main():
    try:
        for symbol in SYMBOLS:
            df = get_klines(symbol, INTERVAL, LIMIT)
            signal = analyze(df)

            # Comparar con última señal enviada
            if last_signals.get(symbol) != signal:
                last_signals[symbol] = signal
                msg = f"🪙 {symbol} [{INTERVAL}]\n{signal}"
                send_telegram_message(TOKEN, CHAT_ID, msg)
                print(f"🔔 Señal enviada para {symbol}: {signal}")
            else:
                print(f"➖ Señal repetida para {symbol}, no se envía mensaje.")
    except Exception as e:
        print("❌ Error:", e)


if __name__ == "__main__":
    while True:
        main()
        time.sleep(3600)
