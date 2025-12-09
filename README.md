# AI DIVIDENDS

Proyecto de análisis financiero con IA para identificar empresas de dividendos con tendencia alcista.

## Cómo usar (Local)
1. Asegúrate de tener Python 3 instalado.
2. Ejecuta el análisis de datos (tarda unos minutos):
   ```bash
   ./venv/bin/python3 analyzer.py
   ```
   Esto generará `stocks_data.json`.
3. Abre `index.html` en tu navegador.
   - O usa un servidor local para mejor experiencia: `python3 -m http.server` y ve a `localhost:8000`.

## Cómo desplegar en Netlify
1. Ve a [Netlify Drop](https://app.netlify.com/drop).
2. Arrastra y suelta la carpeta `AI_DIVIDENDS`.
3. **Importante**: Para que los datos se actualicen, necesitarías configurar un "Build Command" que ejecute el script de Python, pero Netlify estático básico no corre Python fácilmente sin configuración extra.
   - **Opción Pro**: Usa Github. Sube este código a un repo. Conecta Netlify al repo.
   - **Configuración de Build en Netlify**:
     - Command: `pip install -r requirements.txt && python analyzer.py`
     - Publish directory: `.` (directorio raíz)

## Estructura
- `analyzer.py`: Motor de inteligencia. Descarga datos de S&P 500, calcula regresión lineal a 5 años, y filtra dividendos.
- `index.html`: Dashboard Premium.
- `app.js`: Lógica de visualización.
