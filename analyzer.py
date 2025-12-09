import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import linregress
import json
import concurrent.futures
import datetime
import os

# Configuración
TICKER_LIMIT = 500 # Analizar todos los del S&P 500
PERIOD = "5y"
MIN_R_SQUARED = 0.5 # Tendencia consistente
MIN_SLOPE = 0.0005 # Pendiente positiva mínima (ajustable)

def get_sp500_tickers():
    """Obtiene la lista de tickers del S&P 500 de Wikipedia."""
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }
        # Usar requests para evitar 403
        import requests
        from io import StringIO
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # StringIO para pandas
        table = pd.read_html(StringIO(response.text))
        df = table[0]
        tickers = df['Symbol'].tolist()
        return [t.replace('.', '-') for t in tickers] # Corregir BRK.B -> BRK-B
    except Exception as e:
        print(f"Error obteniendo tickers: {e}")
        return []

def analyze_ticker(ticker):
    """Analiza un solo ticker: tendencia y dividendos."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=PERIOD)
        
        if hist.empty or len(hist) < 200:
            return None
        
        # Análisis de Tendencia (Regresión Lineal sobre precio de cierre)
        closes = hist['Close'].values
        x = np.arange(len(closes))
        slope, intercept, r_value, p_value, std_err = linregress(x, closes)
        
        # Filtrar solo tendencia alcista fuerte
        if slope <= 0 or (r_value**2) < MIN_R_SQUARED:
            return None
            
        # Obtener datos de dividendos
        info = stock.info
        dividend_yield = info.get('dividendYield', 0)
        ex_div_date = info.get('exDividendDate', None)
        
        # Si no paga dividendos, ¿lo queremos? El usuario dijo "reparto de dividendos".
        if not dividend_yield:
             return None

        # Formatear fecha ex-div
        ex_div_str = "N/A"
        if ex_div_date:
            ex_div_str = datetime.datetime.fromtimestamp(ex_div_date).strftime('%Y-%m-%d')
            
        # Calcular crecimiento total
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
            'dividend_yield_pct': round(dividend_yield * 100, 2) if dividend_yield else 0,
            'ex_div_date': ex_div_str,
            'sector': info.get('sector', 'Unknown'),
            'score': round((r_value**2 * 100) + (dividend_yield * 1000 if dividend_yield else 0), 2) # Puntuación simple AI
        }
        
    except Exception as e:
        # print(f"Error analizando {ticker}: {e}")
        return None

def main():
    print("Iniciando análisis AI DIVIDENDS...")
    tickers = get_sp500_tickers()
    if not tickers:
        print("No se encontraron tickers. Usando lista de respaldo pequeña para prueba.")
        tickers = ['AAPL', 'MSFT', 'JNJ', 'KO', 'PEP', 'O', 'MAIN', 'XOM', 'CVX']
    else:
        print(f"Analizando {len(tickers)} empresas del S&P 500...")
        
    results = []
    
    # Ejecución paralela
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_ticker = {executor.submit(analyze_ticker, t): t for t in tickers}
        completed = 0
        for future in concurrent.futures.as_completed(future_to_ticker):
            data = future.result()
            if data:
                results.append(data)
            completed += 1
            if completed % 50 == 0:
                print(f"Procesado {completed}/{len(tickers)}...")

    # Ordenar por puntuación (AI Score)
    results.sort(key=lambda x: x['score'], reverse=True)
    
    # Limpiar NaN
    def clean_nan(obj):
        if isinstance(obj, float):
            return None if np.isnan(obj) else obj
        if isinstance(obj, dict):
            return {k: clean_nan(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [clean_nan(i) for i in obj]
        return obj

    cleaned_data = clean_nan(results)
    
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
