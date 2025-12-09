import requests
import json
import datetime
import pandas as pd
import numpy as np
import time

# Configuración
TICKER_LIMIT = 600
MIN_MARKET_CAP = 5_000_000_000

def get_sp500_tickers():
    """Obtiene la lista oficial de tickers del S&P 500."""
    try:
        print("Obteniendo tickers del S&P 500...")
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        table = pd.read_html(response.text)
        return [t.replace('.', '-') for t in table[0]['Symbol'].tolist()]
    except Exception as e:
        print(f"Error obteniendo S&P 500: {e}")
        return ['AAPL', 'MSFT', 'GOOG', 'JNJ', 'KO', 'PEP', 'O', 'XOM', 'CVX']

def fetch_tv_data_batch(tickers):
    """Obtiene datos fundamentales y técnicos de TradingView para una lista de tickers."""
    url = "https://scanner.tradingview.com/america/scan"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # Columnas solicitadas (Mapped to TV Scanner fields)
    columns = [
        "name", "close", "market_cap_basic", "dividend_yield_recent", 
        "Recommend.All", "Perf.5Y", "Volatility.M", "average_volume_10d_calc",
        "description", "sector", "dividend_ex_date_recent"
    ]

    all_data = []
    
    # Generate candidates with both NASDAQ and NYSE prefixes to ensure we find the stock
    # S&P 500 mix is approx 70% NYSE, 30% NASDAQ.
    candidates = []
    for t in tickers:
        candidates.append(f"NASDAQ:{t}")
        candidates.append(f"NYSE:{t}")
        # AMEX is rare in S&P 500 but if missing we could add AMEX:{t} too
    
    # Procesar en lotes de 200 (100 pairs)
    chunk_size = 200 
    for i in range(0, len(candidates), chunk_size):
        chunk = candidates[i:i + chunk_size]
        
        payload = {
            "symbols": {"tickers": chunk},
            "columns": columns
        }
        
        try:
            # print(f"Solicitando lote {i // chunk_size + 1} ({len(chunk)} candidatos)...") 
            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data:
                    all_data.extend(data['data'])
            else:
                print(f"Error batch {i}: {resp.status_code}")
            
            time.sleep(0.5) 
            
        except Exception as e:
            print(f"Excepción en lote {i}: {e}")

    return all_data

def process_results(tv_results):
    processed_map = {} # Deduplicate by symbol
    
    for item in tv_results:
        try:
            d = item['d']
            full_symbol = d[0] # "NASDAQ:AAPL"
            clean_symbol = full_symbol.split(':')[1] if ':' in full_symbol else full_symbol
            
            # If we already have this symbol processed, skip (or overwrite if this exchange is preferred?)
            # Usually only one works. If both return data, it's a dual listing.
            if clean_symbol in processed_map:
                continue
                
            price = d[1]
            market_cap = d[2]
            div_yield = d[3] if d[3] is not None else 0
            rec_score = d[4] if d[4] is not None else 0
            perf_5y = d[5] if d[5] is not None else 0
            volatility_m = d[6] if d[6] is not None else 0
            # volume = d[7]
            name = d[8]
            sector = d[9]
            ex_div_ts = d[10]

            # Filters
            if not market_cap or market_cap < MIN_MARKET_CAP: continue
            if not div_yield or div_yield <= 0: continue # Must pay dividend

            # Normalizations
            # Div Yield from TV is often percentage (0-100) or decimal? 
            # In debug: AAPL 0.37. AAPL yield is ~0.5%. Usually TV returns percentage. 0.37 means 0.37%.
            
            # Recommendation
            tv_signal = "NEUTRAL"
            if rec_score > 0.5: tv_signal = "STRONG_BUY"
            elif rec_score > 0.1: tv_signal = "BUY"
            elif rec_score < -0.5: tv_signal = "STRONG_SELL"
            elif rec_score < -0.1: tv_signal = "SELL"
            
            # AI Score Calculation
            score_growth = min(max(perf_5y, 0), 100) * 0.4 
            
            score_stability = 0
            if volatility_m > 0:
                score_stability = max(0, 40 - (volatility_m * 4)) 
            
            score_yield = min(div_yield * 5, 20)
            
            score_signal = 0
            if "BUY" in tv_signal: score_signal = 10
            if "STRONG_BUY" in tv_signal: score_signal = 20
            
            raw_score = score_growth + score_stability + score_yield + score_signal
            final_score = min(round(raw_score), 100)

            # Dates
            ex_div_str = "N/A"
            if ex_div_ts:
                try:
                    # TV might return seconds
                    dt = datetime.datetime.fromtimestamp(ex_div_ts)
                    ex_div_str = dt.strftime('%Y-%m-%d')
                except:
                    pass

            processed_map[clean_symbol] = {
                'symbol': clean_symbol,
                'name': name,
                'price': float(price),
                'slope': round(perf_5y / 100, 4), # Proxy for slope
                'r_squared': round(1.0 / (volatility_m if volatility_m > 0 else 1), 2), # Proxy
                'growth_5y_pct': round(perf_5y, 2),
                'dividend_yield_pct': round(div_yield, 2),
                'start_price': 0, # Legacy
                'end_price': price,
                'ex_div_date': ex_div_str,
                'est_next_payment': round(div_yield / 100 * price / 4, 3), # Approx quarterly
                'annual_dividend': round(div_yield / 100 * price, 2),
                'sector': sector,
                'tv_signal': tv_signal,
                'score': final_score
            }
            
        except Exception as e:
            continue
            
    return list(processed_map.values())

def main():
    print("Iniciando análisis AI DIVIDENDS (TradingView Native)...")
    tickers = get_sp500_tickers()
    
    if not tickers:
        print("Error crítico: No se pudieron obtener tickers.")
        return

    print(f"Ticker count: {len(tickers)}")
    
    # Batch processing
    raw_data = fetch_tv_data_batch(tickers)
    
    # Process
    results = process_results(raw_data)
    
    # Sort by Score
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Output structure
    final_output = {
        "metadata": {
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_analyzed": len(raw_data)
        },
        "data": results
    }

    # Save
    with open('stocks_data.json', 'w') as f:
        json.dump(final_output, f, indent=2)
        
    print(f"Análisis completado. {len(results)} empresas seleccionadas.")
    print("Datos guardados en stocks_data.json.")

if __name__ == "__main__":
    main()
