import yfinance as yf
import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import linregress
import json
import concurrent.futures
import datetime
import os
import math
from tradingview_ta import TA_Handler, Interval, Exchange

# Configuración
TICKER_LIMIT = 600 
PERIOD = "5y"
MIN_R_SQUARED = 0.5 # Volvemos a un valor equilibrado para S&P 500
MIN_SLOPE = 0.0005 
# Filtros de Calidad (Opcionales para S&P 500 ya que son grandes, pero mantenemos limpieza)
MIN_MARKET_CAP = 5_000_000_000 # 5B (S&P 500 suele ser >13B, bajamos un poco por si acaso)
MAX_BETA = 2.0 # Más tolerante con la volatilidad dentro del índice

def get_sp500_tickers():
    """Obtiene la lista oficial de tickers del S&P 500."""
    try:
        print("Obteniendo tickers del S&P 500...")
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        headers = {"User-Agent": "Mozilla/5.0"}
        import requests
        from io import StringIO
        response = requests.get(url, headers=headers)
        table = pd.read_html(StringIO(response.text))
        return [t.replace('.', '-') for t in table[0]['Symbol'].tolist()]
    except Exception as e:
        print(f"Error obteniendo S&P 500: {e}")
        return ['AAPL', 'MSFT', 'GOOG', 'JNJ', 'KO'] # Fallback mínimo

# (Deleted get_all_us_tickers to avoid confusion/timeout)

def analyze_ticker(ticker):
    """Analiza un solo ticker: TradingView TA + Yahoo Finance Dividends."""
    try:
        # 1. TradingView Technical Analysis (REAL TIME FROM TRADINGVIEW)
        try:
            handler = TA_Handler(
                symbol=ticker,
                exchange="NASDAQ", # Default, might need dynamic adjustment for NYSE
                screener="america",
                interval=Interval.INTERVAL_1_WEEK # Long term view
            )
            analysis = handler.get_analysis()
            tv_recommendation = analysis.summary.get('RECOMMENDATION', 'NEUTRAL')
            tv_buy_score = analysis.summary.get('BUY', 0)
            tv_sell_score = analysis.summary.get('SELL', 0)
        except:
            # Fallback if TV fails (or symbol is on NYSE/AMEX and mapped wrongly)
            tv_recommendation = "UNKNOWN"
            tv_buy_score = 0
        
        # 2. Yahoo Finance Data (Dividends & Fundamentals)
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Filtros Básicos
        market_cap = info.get('marketCap', 0)
        if market_cap and market_cap < MIN_MARKET_CAP: return None
        
        # Obtener Histórico para Tendencia
        hist = stock.history(period=PERIOD)
        if len(hist) < 200: return None
        
        closes = hist['Close'].values
        x = np.arange(len(closes))
        slope, intercept, r_value, p_value, std_err = linregress(x, closes)
        
        if slope <= MIN_SLOPE or (r_value**2) < MIN_R_SQUARED:
            return None
            
        # Dividendos
        dividend_yield = info.get('dividendYield', 0)
        ex_div_timestamp = info.get('exDividendDate', None)
        dividend_rate_annual = info.get('dividendRate', 0)
        
        last_div_amount = 0
        try:
            divs = stock.dividends
            if not divs.empty: last_div_amount = divs.iloc[-1]
        except: pass
            
        est_payment_amt = last_div_amount
        if dividend_rate_annual and dividend_rate_annual > 0:
            if abs((last_div_amount * 4) - dividend_rate_annual) < 0.1:
                 est_payment_amt = last_div_amount
            else:
                 est_payment_amt = round(dividend_rate_annual / 4, 2)

        if (not dividend_yield and last_div_amount == 0): return None

        ex_div_str = "N/A"
        if ex_div_timestamp:
            ex_div_str = datetime.datetime.fromtimestamp(ex_div_timestamp).strftime('%Y-%m-%d')
            
        start_price = closes[0]
        end_price = closes[-1]
        growth_pct = ((end_price - start_price) / start_price) * 100
        
        # SCORING FORMULA (0-100)
        # Base: Trend (50 pts) + Dividend (20 pts)
        # Bonus: TradingView Signal (Strong Buy = +30 pts, Buy = +15 pts)
        
        base_score = (r_value**2 * 50) + (min(dividend_yield or 0, 0.10) * 200)
        tv_bonus = 0
        if 'STRONG_BUY' in tv_recommendation: tv_bonus = 30
        elif 'BUY' in tv_recommendation: tv_bonus = 15
        elif 'SELL' in tv_recommendation: tv_bonus = -10
        
        final_score = base_score + tv_bonus
        final_score = max(0, min(100, final_score)) # Clamp 0-100

        return {
            'symbol': ticker,
            'name': info.get('shortName', ticker),
            'price': round(end_price, 2),
            'slope': round(slope, 4),
            'r_squared': round(r_value**2, 4),
            'growth_5y_pct': round(growth_pct, 2),
            'dividend_yield_pct': round((dividend_yield or 0) * 100, 2),
            'ex_div_date': ex_div_str,
            'est_next_payment': round(est_payment_amt, 3),
            'annual_dividend': dividend_rate_annual,
            'sector': info.get('sector', 'Unknown'),
            'tv_signal': tv_recommendation, # NEW FIELD
            'score': round(final_score, 1)
        }
    except Exception as e:
        return None

def main():
    print("Iniciando análisis AI DIVIDENDS (S&P 500)...")
    tickers = get_sp500_tickers()
    
    if not tickers:
        print("No se encontraron tickers. Usando lista de respaldo.")
        tickers = ['AAPL', 'MSFT', 'JNJ', 'KO', 'PEP', 'O', 'XOM', 'CVX']
    else:
        print(f"Analizando {len(tickers)} empresas del S&P 500...")
        
    results = []
    
    # Ejecución paralela
    # 20 workers es seguro y rápido para 500 items
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ticker = {executor.submit(analyze_ticker, t): t for t in tickers}
        completed = 0
        for future in concurrent.futures.as_completed(future_to_ticker):
            completed += 1
            if completed % 50 == 0:
                print(f"Procesado {completed}/{len(tickers)}...")
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception as e:
                pass 

    # Ordenar por puntuación (AI Score)
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Limpiar NaN e Infinity (JSON standard no soporta Infinity)
    def clean_data(obj):
        if isinstance(obj, float):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return obj
        if isinstance(obj, dict):
            return {k: clean_data(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [clean_data(i) for i in obj]
        return obj

    cleaned_data = clean_data(results)
    
    # Estructura Final
    final_output = {
        "metadata": {
            "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_analyzed": len(tickers)
        },
        "data": cleaned_data
    }

    # Guardar JSON
    with open('stocks_data.json', 'w') as f:
        json.dump(final_output, f, indent=2)
        
    print(f"Análisis completado. {len(results)} empresas seleccionadas.")
    print(f"Datos guardados en stocks_data.json con timestamp.")

if __name__ == "__main__":
    main()
