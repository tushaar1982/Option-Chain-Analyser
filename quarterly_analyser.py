import requests
import json
import os
from datetime import datetime, timedelta
import time

# API Headers
HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Authorization': 'Basic bmlmdHlhcGl1c2VyOm5pZnR5YXBpdXNlckAyMTEwIw==',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36',
}

# API URL
BASE_URL = 'https://webapi.niftytrader.in/webapi/option/option-chain-data'

# Fetch option chain data for a symbol
def fetch_option_chain_data(symbol):
    params = {
        'symbol': symbol,
        'exchange': 'nse',
        'expiryDate': '',  # Default to nearest expiry
        'atmBelow': 12,
        'atmAbove': 12
    }
    try:
        response = requests.get(BASE_URL, headers=HEADERS, params=params)
        response.raise_for_status()  # Raise HTTPError for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

# Analyze stock and option data
def analyze_data(data, index_close):
    op_data = data.get("resultData", {}).get("opDatas", [])
    if not op_data:
        return {}

    stock_recommendation = None
    support_levels = []
    resistance_levels = []
    reversal_points = []
    institutional_activity = None
    option_recommendation = None
    dominant_trend = None

    max_oi = max(
        max(entry.get("calls_oi", 0), entry.get("puts_oi", 0)) for entry in op_data
    )

    total_call_oi = sum(entry.get("calls_oi", 0) for entry in op_data)
    total_put_oi = sum(entry.get("puts_oi", 0) for entry in op_data)

    # Determine dominant trend
    if total_call_oi > total_put_oi:
        dominant_trend = "Bearish"
    elif total_put_oi > total_call_oi:
        dominant_trend = "Bullish"
    else:
        dominant_trend = "Neutral"

    # Suggest stock trading strategy
    if dominant_trend == "Bullish":
        stock_recommendation = {
            "action": "Buy Stock",
            "entry_price": index_close,
            "target_price": index_close * 1.02,
            "stop_loss": index_close * 0.98,
            "confidence": "High",
            "reason": "Overall bullish sentiment based on high Put OI and increased volume at lower strikes."
        }
    elif dominant_trend == "Bearish":
        stock_recommendation = {
            "action": "Short Stock",
            "entry_price": index_close,
            "target_price": index_close * 0.98,
            "stop_loss": index_close * 1.02,
            "confidence": "High",
            "reason": "Overall bearish sentiment based on high Call OI and increased volume at higher strikes."
        }

    for entry in op_data:
        strike_price = entry.get("strike_price", 0)
        calls_oi = entry.get("calls_oi", 0)
        puts_oi = entry.get("puts_oi", 0)
        calls_change_oi = entry.get("calls_change_oi", 0)
        puts_change_oi = entry.get("puts_change_oi", 0)
        calls_volume = entry.get("calls_volume", 0)
        puts_volume = entry.get("puts_volume", 0)
        calls_ltp = entry.get("calls_ltp", 0)
        puts_ltp = entry.get("puts_ltp", 0)
        call_delta = entry.get("call_delta", 0)
        put_delta = entry.get("put_delta", 0)
        call_gamma = entry.get("call_gamma", 0)
        put_gamma = entry.get("put_gamma", 0)
        call_vega = entry.get("call_vega", 0)
        put_vega = entry.get("put_vega", 0)

        # Support and resistance levels
        if puts_oi > calls_oi and puts_oi > 1000:
            strength_percentage = (puts_oi / max_oi) * 100
            support_levels.append({
                "strike_price": strike_price,
                "strength_percentage": round(strength_percentage, 2),
                "probability_of_breakout": "Low" if puts_change_oi <= 0 else "High",
                "reason": f"Support at {strike_price} with {round(strength_percentage, 2)}% strength due to high Put OI."
            })
        if calls_oi > puts_oi and calls_oi > 1000:
            strength_percentage = (calls_oi / max_oi) * 100
            resistance_levels.append({
                "strike_price": strike_price,
                "strength_percentage": round(strength_percentage, 2),
                "probability_of_breakout": "Low" if calls_change_oi <= 0 else "High",
                "reason": f"Resistance at {strike_price} with {round(strength_percentage, 2)}% strength due to high Call OI."
            })

        # Reversal points
        if abs(call_delta) > 0.5 or abs(put_delta) > 0.5:
            direction = "Bullish" if call_delta > 0 else "Bearish"
            reversal_points.append({
                "strike_price": strike_price,
                "likely_reversal": direction,
                "reason": f"Reversal at {strike_price} with {direction} bias due to high Delta ({call_delta})."
            })

        # Institutional activity
        if calls_volume > 10000 or puts_volume > 10000:
            activity_type = "Call Buying" if calls_volume > puts_volume else "Put Selling"
            institutional_activity = {
                "strike_price": strike_price,
                "type": activity_type,
                "reason": f"High volume at {strike_price} suggests institutional {activity_type}."
            }

        # Option recommendation
        if dominant_trend == "Bullish" and not option_recommendation and call_delta > 0.3 and call_vega > 0.1:
            option_recommendation = {
                "action": "Buy Call",
                "strike_price": strike_price,
                "entry_price": calls_ltp,
                "target_premium": round(calls_ltp * 1.2, 2),
                "stop_loss_premium": round(calls_ltp * 0.8, 2),
                "confidence": "High",
                "reason": f"Buying Call at {strike_price} due to bullish sentiment with strong Delta ({call_delta}) and Vega ({call_vega})."
            }
        elif dominant_trend == "Bearish" and not option_recommendation and put_delta < -0.3 and put_vega > 0.1:
            option_recommendation = {
                "action": "Buy Put",
                "strike_price": strike_price,
                "entry_price": puts_ltp,
                "target_premium": round(puts_ltp * 1.2, 2),
                "stop_loss_premium": round(puts_ltp * 0.8, 2),
                "confidence": "High",
                "reason": f"Buying Put at {strike_price} due to bearish sentiment with strong Delta ({put_delta}) and Vega ({put_vega})."
            }

    return {
        "dominant_trend": dominant_trend,
        "stock_recommendation": stock_recommendation,
        "support_levels": sorted(support_levels, key=lambda x: x["strength_percentage"], reverse=True)[:3],
        "resistance_levels": sorted(resistance_levels, key=lambda x: x["strength_percentage"], reverse=True)[:3],
        "reversal_points": reversal_points[:2],
        "institutional_activity": institutional_activity,
        "option_recommendation": option_recommendation
    }

# Save raw and analyzed data
def save_data_with_history(symbol, raw_data, analysis):
    folder_path = f"{symbol}_data"
    os.makedirs(folder_path, exist_ok=True)

    current_date = datetime.now().strftime('%Y-%m-%d')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Save raw data with timestamp
    raw_history_file = os.path.join(folder_path, f"rawdata_{symbol}_{current_date}.json")
    with open(raw_history_file, 'a') as f:
        history_entry = {
            "timestamp": timestamp,
            "data": raw_data
        }
        json.dump(history_entry, f, indent=4)
        f.write("\n")

    # Save analyzed data with timestamp
    analyzed_history_file = os.path.join(folder_path, f"analysed_{symbol}_{current_date}.json")
    with open(analyzed_history_file, 'a') as f:
        history_entry = {
            "timestamp": timestamp,
            "analysis": analysis
        }
        json.dump(history_entry, f, indent=4)
        f.write("\n")

    # Save the latest analyzed data
    analyzed_file = os.path.join(folder_path, f"{symbol}.json")
    with open(analyzed_file, 'w') as f:
        json.dump(analysis, f, indent=4)

    print(f"Data and analysis saved for {symbol}.")


def calculate_next_quarter():
    now = datetime.now()
    next_minute = ((now.minute // 15) + 1) * 15
    next_hour = now.hour
    if next_minute == 60:
        next_minute = 0
        next_hour += 1
    next_run = now.replace(hour=next_hour, minute=next_minute, second=0, microsecond=0)
    if next_run < now:  # If the calculated time is in the past, move to the next quarter
        next_run += timedelta(minutes=15)
    return next_run


def schedule_task(symbols):
    print("Starting scheduled task...")

    next_run = calculate_next_quarter()
    print(f"First run scheduled at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

    while True:
        now = datetime.now()
        if now >= next_run:
            print(f"Running tasks at {now.strftime('%Y-%m-%d %H:%M:%S')}...")
            for symbol in symbols:
                time.sleep(15)
                print(f"Processing {symbol}...")
                raw_data = fetch_option_chain_data(symbol)
                if not raw_data:
                    print(f"Skipping {symbol} due to fetch failure.")
                    continue

                # Extract index close price
                index_close = raw_data.get("resultData", {}).get("opDatas", [{}])[0].get("index_close", None)
                if not index_close:
                    print(f"Skipping {symbol} due to missing index close price.")
                    continue

                # Analyze stock and option data
                analysis = analyze_data(raw_data, index_close)

                # Save data and analysis with history
                save_data_with_history(symbol, raw_data, analysis)

            # Calculate the next run time
            next_run = calculate_next_quarter()
            print(f"Next run scheduled at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

        time.sleep(10)

if __name__ == "__main__":
    symbols = ["banknifty", "nifty", "infy", "wipro","tatamotors",
                "axisbank","sbin","icicibank",
                "kotakbank","sunpharma"]
            
    schedule_task(symbols)