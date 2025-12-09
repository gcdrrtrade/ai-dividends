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

# Configuración
TICKER_LIMIT = 10000 
PERIOD = "5y"
MIN_R_SQUARED = 0.6 
MIN_SLOPE = 0.0005 
MIN_MARKET_CAP = 10_000_000_000 # 10 Billones
MAX_BETA = 1.5 

def get_all_us_tickers():
    """Obtiene TODOS los tickers de EEUU (NASDAQ, NYSE, AMEX)."""
    try:
        print("Descargando lista completa de tickers de EEUU...")
        url = "http://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt"
        df = pd.read_csv(url, sep="|")
        
        clean_df = df[df['Test Issue'] == 'N']
        tickers = clean_df['Symbol'].tolist()
        
        final_tickers = []
        for t in tickers:
            if not isinstance(t, str): continue
            t = t.replace('.', '-')
            final_tickers.append(t)
            
        return final_tickers
    except Exception as e:
        print(f"Error obteniendo lista completa: {e}")
        return get_sp500_tickers_fallback()

def get_sp500_tickers_fallback():
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        headers = {"User-Agent": "Mozilla/5.0"}
        import requests
        from io import StringIO
        response = requests.get(url, headers=headers)
        table = pd.read_html(StringIO(response.text))
        return [t.replace('.', '-') for t in table[0]['Symbol'].tolist()]
    except:
        return ['AAPL', 'MSFT', 'GOOG']

def analyze_ticker(ticker):
    """Analiza un solo ticker: tendencia, dividendos, market cap y volatilidad."""
    try:
        stock = yf.Ticker(ticker)
        
        # 1. Filtro Rapido: Histórico
        hist = stock.history(period=PERIOD)
        if hist.empty or len(hist) < 200:
            return None
        
        # 2. Filtro de Calidad (Market Cap y Beta)
        info = stock.info
        market_cap = info.get('marketCap', 0)
        beta = info.get('beta', 0)
        
        if not market_cap or market_cap < MIN_MARKET_CAP:
            return None
        if beta and beta > MAX_BETA:
            return None

        # 3. Tendencia
        closes = hist['Close'].values
        x = np.arange(len(closes))
        slope, intercept, r_value, p_value, std_err = linregress(x, closes)
        
        if slope <= MIN_SLOPE or (r_value**2) < MIN_R_SQUARED:
            return None
            
        # 4. Dividendos
        dividend_yield = info.get('dividendYield', 0)
        ex_div_timestamp = info.get('exDividendDate', None)
        dividend_rate_annual = info.get('dividendRate', 0)
        
        # Logic for Payment Amount
        last_div_amount = 0
        try:
            divs = stock.dividends
            if not divs.empty:
                last_div_amount = divs.iloc[-1]
        except:
            pass
            
        est_payment_amt = last_div_amount
        if dividend_rate_annual and dividend_rate_annual > 0:
            if abs((last_div_amount * 4) - dividend_rate_annual) < 0.1:
                 est_payment_amt = last_div_amount
            else:
                 est_payment_amt = round(dividend_rate_annual / 4, 2)

        if (not dividend_yield and last_div_amount == 0):
             return None

        # Formatear
        ex_div_str = "N/A"
        if ex_div_timestamp:
            ex_div_str = datetime.datetime.fromtimestamp(ex_div_timestamp).strftime('%Y-%m-%d')
            
        start_price = closes[0]
        end_price = closes[-1]
        growth_pct = ((end_price - start_price) / start_price) * 100
        
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
            'score': round((r_value**2 * 70) + (min(dividend_yield or 0, 0.10) * 300), 1)
        }
        
    except Exception as e:
        return None

def main():
    print("Iniciando análisis AI DIVIDENDS (Universo Completo US)...")
    tickers = get_all_us_tickers()
    
    if not tickers:
        print("No se encontraron tickers. Usando lista de respaldo S&P 500.")
        tickers = get_sp500_tickers_fallback()
    else:
        print(f"Analizando {len(tickers)} empresas (Todo el mercado US)...")
        # Limitar si es necesario para pruebas rápidas, pero el usuario quiere "todo"
        # tickers = tickers[:100] 
        
    results = []
    
    # Ejecución paralela masiva
    # Aumentamos workers a 50 para manejar 7000+ tickers razonablemente rápido
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        future_to_ticker = {executor.submit(analyze_ticker, t): t for t in tickers}
        completed = 0
        for future in concurrent.futures.as_completed(future_to_ticker):
            completed += 1
            if completed % 100 == 0:
                print(f"Procesado {completed}/{len(tickers)}...")
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception as e:
                pass # Ignorar errores individuales en ejecución masiva

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
