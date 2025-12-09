// State
let stocksData = [];
let filteredData = [];
let currentLanguage = localStorage.getItem('ai_dividends_lang') || 'es'; // Default ES

// Translations
const translations = {
    en: {
        heroTitle: 'Data-Driven<br><span class="gradient-text">Dividend Growth</span>',
        heroSubtitle: 'Algorithmically selected US stocks with 5-year bullish trends and consistent yields.',
        statCompanies: 'Companies Analyzed',
        statPicks: 'AI Picks',
        statYield: 'Avg Yield',
        statLastScan: 'Last Scan',
        heroDisclaimer: 'Data Source: TradingView Scanner API. Validated against TradingView logic.',
        topPicksTitle: 'Top AI Opportunities',
        loading: 'Loading AI Analysis...',
        scannerTitle: 'Market Scanner',
        searchPlaceholder: 'Search Ticker or Company...',
        filterDateAll: 'Time: All Dates',
        filterDateToday: 'Time: Today',
        filterDateWeek: 'Time: This Week',
        filterDateMonth: 'Time: This Month',
        sortScore: 'Sort by: AI Score',
        sortYield: 'Sort by: Yield',
        sortGrowth: 'Sort by: 5y Growth',
        sortDate: 'Sort by: Ex-Div Date',
        colSymbol: 'Symbol',
        colPrice: 'Price',
        colGrowth: '5Y Growth',
        colYield: 'Yield',
        colExDate: 'Ex-Date',
        colSignal: 'Signal',
        colScore: 'AI Score',
        tooltipScore: '<strong>AI Score (0-100)</strong><br>Based on uptrend consistency (70%) and dividend yield (30%).',
        colDetails: 'Details',
        viewBtn: 'View',
        days: 'Days',
        passed: 'Passed',
        modalAnalysisDetails: 'Analysis Details',
        modalNextDividend: 'Next Dividend',
        modalSector: 'Sector',
        modalPrice: 'Price',
        modalYield: 'Dividend Yield',
        modalAnnual: 'Annual Dividend',
        modalEstPay: 'Est. Next Payment',
        modalExDate: 'Ex-Div Date',
        modalGrowth: '5Y Growth',
        modalTrend: 'Trend Consistency (R²)'
    },
    es: {
        heroTitle: 'Crecimiento de Dividendos<br><span class="gradient-text">Impulsado por Datos</span>',
        heroSubtitle: 'Acciones de EE.UU. seleccionadas algorítmicamente con tendencias alcistas de 5 años y rendimientos consistentes.',
        statCompanies: 'Empresas Analizadas',
        statPicks: 'Selección AI',
        statYield: 'Rentabilidad Media',
        statLastScan: 'Último Escaneo',
        heroDisclaimer: 'Fuente de datos: API de TradingView Scanner.',
        topPicksTitle: 'Mejores Oportunidades AI',
        loading: 'Cargando Análisis AI...',
        scannerTitle: 'Escáner de Mercado',
        searchPlaceholder: 'Buscar Ticker o Empresa...',
        filterDateAll: 'Tiempo: Todas',
        filterDateToday: 'Tiempo: Hoy',
        filterDateWeek: 'Tiempo: Esta Semana',
        filterDateMonth: 'Tiempo: Este Mes',
        sortScore: 'Ordenar: Puntuación AI',
        sortYield: 'Ordenar: Rentabilidad',
        sortGrowth: 'Ordenar: Crecimiento 5A',
        sortDate: 'Ordenar: Fecha Ex-Div',
        colSymbol: 'Símbolo',
        colPrice: 'Precio',
        colGrowth: 'Crecimiento 5A',
        colYield: 'Rentabilidad',
        colExDate: 'Fecha Ex',
        colSignal: 'Señal',
        colScore: 'Puntuación AI',
        tooltipScore: '<strong>Puntuación AI (0-100)</strong><br>Basada en la consistencia de la tendencia alcista (70%) y la rentabilidad del dividendo (30%).',
        colDetails: 'Detalles',
        viewBtn: 'Ver',
        days: 'Días',
        passed: 'Pasado',
        modalAnalysisDetails: 'Detalles del Análisis',
        modalNextDividend: 'Próximo Dividendo',
        modalSector: 'Sector',
        modalPrice: 'Precio',
        modalYield: 'Rentabilidad',
        modalAnnual: 'Dividendo Anual',
        modalEstPay: 'Est. Próximo Pago',
        modalExDate: 'Fecha Ex-Div',
        modalGrowth: 'Crecimiento 5A',
        modalTrend: 'Consistencia (R²)'
    }
};

// DOM Elements
const topPicksContainer = document.getElementById('topPicksContainer');
const tableBody = document.getElementById('stockTableBody');
const searchInput = document.getElementById('searchInput');
const sortSelect = document.getElementById('sortSelect');
const dateFilter = document.getElementById('dateFilter');
const marketTime = document.getElementById('marketTime');
const modal = document.getElementById('stockModal');
const closeModalBtn = document.querySelector('.close-modal');
const langEnBtn = document.getElementById('langEn');
const langEsBtn = document.getElementById('langEs');

// Stats Elements
const elTotalAnalyzed = document.getElementById('totalAnalyzed');
const elTotalPicks = document.getElementById('totalPicks');
const elAvgYield = document.getElementById('avgYield');

// Modal Elements
const modalTitle = document.getElementById('modalTitle');
const modalScore = document.getElementById('modalScore');
const modalDetailsList = document.getElementById('modalDetailsList');
const divTimer = document.getElementById('divTimer');

// Init
document.addEventListener('DOMContentLoaded', () => {
    updateLanguage(currentLanguage); // Apply lang first
    fetchData();
    setupEventListeners();
    startClock();
});

function setupEventListeners() {
    searchInput.addEventListener('input', applyFilters);
    dateFilter.addEventListener('change', applyFilters);
    sortSelect.addEventListener('change', handleSort);
    closeModalBtn.addEventListener('click', () => {
        modal.classList.add('hidden');
        document.getElementById('tvChartContainer').innerHTML = ''; // Clear chart to stop memory leaks
    });

    // Language Switcher
    langEnBtn.addEventListener('click', () => updateLanguage('en'));
    langEsBtn.addEventListener('click', () => updateLanguage('es'));

    // Close modal on click outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.add('hidden');
            document.getElementById('tvChartContainer').innerHTML = '';
        }
    });
}

function updateLanguage(lang) {
    currentLanguage = lang;
    localStorage.setItem('ai_dividends_lang', lang);
    const t = translations[lang];

    // Update Static Elements
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (t[key]) el.innerHTML = t[key];
    });

    // Update Placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (t[key]) el.placeholder = t[key];
    });

    // Update active state of buttons (optional styling)
    langEnBtn.style.opacity = lang === 'en' ? '1' : '0.5';
    langEsBtn.style.opacity = lang === 'es' ? '1' : '0.5';

    // Rerender Table/Modal if data loaded
    if (stocksData.length > 0) {
        renderTopPicks();
        renderTable();
    }
}

function startClock() {
    const elDate = document.getElementById('marketDate');
    const elTime = document.getElementById('marketTime');

    function updateTags() {
        const now = new Date();
        const optsDate = { timeZone: "America/New_York", weekday: 'short', day: '2-digit', month: 'short' };
        const optsTime = { timeZone: "America/New_York", hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false };

        // "Mon, 09 Dec"
        const dateStr = new Intl.DateTimeFormat('en-US', optsDate).format(now);
        // "14:30:05"
        const timeStr = new Intl.DateTimeFormat('en-US', optsTime).format(now);

        if (elDate) elDate.innerText = `NY: ${dateStr}`;
        if (elTime) elTime.innerText = timeStr;
    }
    updateTags();
    setInterval(updateTags, 1000);
}

async function fetchData() {
    try {
        const response = await fetch('stocks_data.json');
        if (!response.ok) throw new Error("Data not found");

        const json = await response.json();

        // Handle new structure { metadata, data }
        if (json.data) {
            stocksData = json.data;
            // Update last updated text
            if (json.metadata && json.metadata.last_updated) {
                const updatedTime = new Date(json.metadata.last_updated);
                const timeStr = updatedTime.toLocaleString();
                if (document.getElementById('dataLastUpdated'))
                    document.getElementById('dataLastUpdated').innerText = `Data Updated: ${timeStr}`;
            }
        } else {
            // Fallback for old Format (array)
            stocksData = json;
        }

        // Filter out bad data if any
        stocksData = stocksData.filter(s => s.price > 0 && s.score >= 0);

        filteredData = [...stocksData];

        updateStats();
        renderTopPicks();
        renderTable();

    } catch (e) {
        console.error(e);
        topPicksContainer.innerHTML = `<div style="text-align:center; color:white;">
            <p>Data not yet generated. Please wait for the analysis script to complete.</p>
        </div>`;
    }
}

function updateStats() {
    elTotalAnalyzed.innerText = "500+"; // Estimated
    elTotalPicks.innerText = stocksData.length;

    // Calculate avg yield
    const avg = stocksData.reduce((acc, curr) => acc + curr.dividend_yield_pct, 0) / stocksData.length;
    elAvgYield.innerText = avg.toFixed(2) + "%";
}

function renderTopPicks() {
    topPicksContainer.innerHTML = '';
    const top3 = stocksData.slice(0, 3);

    top3.forEach(stock => {
        const card = document.createElement('div');
        card.className = 'stock-card';
        card.onclick = () => openStockModal(stock);

        card.innerHTML = `
            <div class="card-header">
                <div>
                    <div class="card-ticker">${stock.symbol}</div>
                    <div class="card-name">${stock.name}</div>
                </div>
                <div class="card-score">AI ${stock.score}</div>
            </div>
            <div class="card-price">$${stock.price}</div>
            <div class="card-meta">
                <span><i class="ri-line-chart-line"></i> +${stock.growth_5y_pct}% (5Y)</span>
                <span><i class="ri-hand-coin-line"></i> ${stock.dividend_yield_pct}% Yield</span>
            </div>
        `;
        topPicksContainer.appendChild(card);
    });
}

function renderTable() {
    tableBody.innerHTML = '';

    // Limit to 50 for performance if list is huge
    const displayList = filteredData.slice(0, 50);

    displayList.forEach(stock => {
        const tr = document.createElement('tr');

        tr.innerHTML = `
            <td>
                <div style="display:flex; flex-direction:column;">
                    <span style="font-weight:700; color:var(--primary); font-size:1rem;">${stock.symbol}</span>
                    <span style="font-size:0.75rem; color:var(--text-muted);">${stock.name}</span>
                </div>
            </td>
            <td>$${stock.price}</td>
            <td style="color:${stock.growth_5y_pct >= 0 ? 'var(--success)' : '#ef4444'};">
                ${stock.growth_5y_pct >= 0 ? '+' : ''}${stock.growth_5y_pct}%
            </td>
            <td>${stock.dividend_yield_pct}%</td>
            <td style="font-size:0.85rem; color:var(--text-muted);">${stock.ex_div_date || 'N/A'}</td>
            <td>
                <span style="font-weight:600; font-size:0.75rem; color:${stock.tv_signal && stock.tv_signal.includes('BUY') ? 'var(--success)' : stock.tv_signal && stock.tv_signal.includes('SELL') ? '#ef4444' : '#9ca3af'};">
                    ${stock.tv_signal ? stock.tv_signal.replace(/_/g, ' ') : 'NEUTRAL'}
                </span>
            </td>
            <td>    
                <span class="modal-badge" 
                      style="font-size:0.8rem; background: ${stock.score >= 75 ? 'var(--success)' : stock.score >= 50 ? '#f59e0b' : '#ef4444'}; color: #fff;">
                    ${stock.score}
                </span>
            </td>
            <td>
                <button class="btn-view" onclick="openStockModalBySymbol('${stock.symbol}')">View</button>
            </td>
        `;
        tableBody.appendChild(tr);
    });
}

// Helpers for onClick event strings
window.openStockModalBySymbol = (symbol) => {
    const stock = stocksData.find(s => s.symbol === symbol);
    if (stock) openStockModal(stock);
};

function applyFilters() {
    const query = searchInput.value.toLowerCase();
    const dateVal = dateFilter.value;

    filteredData = stocksData.filter(s => {
        // Text Search
        const matchesSearch = s.symbol.toLowerCase().includes(query) ||
            s.name.toLowerCase().includes(query);

        if (!matchesSearch) return false;

        // Date Filter (Keep this for the dropdown filter logic)
        if (dateVal === 'all') return true;

        if (!s.ex_div_date || s.ex_div_date === 'N/A' || s.ex_div_date === 'Check TV') return false;

        const divDate = new Date(s.ex_div_date);
        const today = new Date();
        // Reset time for comparisons
        today.setHours(0, 0, 0, 0);

        if (dateVal === 'today') {
            return divDate.toDateString() === today.toDateString();
        }

        if (dateVal === 'week') {
            // Check if within next 7 days
            const nextWeek = new Date(today);
            nextWeek.setDate(today.getDate() + 7);
            return divDate >= today && divDate <= nextWeek;
        }

        if (dateVal === 'month') {
            return divDate.getMonth() === today.getMonth() &&
                divDate.getFullYear() === today.getFullYear();
        }

        return true;
    });

    // Re-sort if needed (keep current sort)
    handleSort({ target: sortSelect });
}

function handleSort(e) {
    const sortKey = sortSelect.value; // or e.target.value

    filteredData.sort((a, b) => {
        if (sortKey === 'score') return b.score - a.score;
        if (sortKey === 'yield') return b.dividend_yield_pct - a.dividend_yield_pct;
        if (sortKey === 'growth') return b.growth_5y_pct - a.growth_5y_pct;
        if (sortKey === 'date') {
            // Sort by Date (Nearest to Future first, or just Ascending?)
            // Usually ascending (soonest date first) is better for dividend calendar
            // BUT "N/A" or "Check TV" should be last.
            const dateA = new Date(a.ex_div_date || '2099-01-01');
            const dateB = new Date(b.ex_div_date || '2099-01-01');
            // If invalid date, treat as far future
            const valA = isNaN(dateA) ? 9999999999999 : dateA.getTime();
            const valB = isNaN(dateB) ? 9999999999999 : dateB.getTime();

            return valA - valB; // Ascending (Soonest first)
        }
        return 0;
    });
    renderTable();
}

function openStockModal(stock) {
    modalTitle.innerText = `${stock.symbol} - ${stock.name}`;
    modalScore.innerText = `AI Score: ${stock.score}`;

    // Fill Details
    modalDetailsList.innerHTML = `
        <li><span>Sector</span> <span>${stock.sector}</span></li>
        <li><span>Price</span> <span>$${stock.price}</span></li>
        <li><span>Dividend Yield</span> <span>${stock.dividend_yield_pct}%</span></li>
        <li><span>Annual Dividend</span> <span>$${stock.annual_dividend || '--'}</span></li>
        <li><span>Est. Next Payment</span> <span style="color:var(--success); font-weight:700;">$${stock.est_next_payment || '--'} / share</span></li>
        <li><span>Ex-Div Date</span> <span>${stock.ex_div_date}</span></li>
        <li><span>5Y Growth</span> <span style="color:var(--success);">+${stock.growth_5y_pct}%</span></li>
        <li><span>Trend Consistency (R²)</span> <span>${stock.r_squared}</span></li>
    `;

    // Countdown
    if (stock.ex_div_date && stock.ex_div_date !== 'N/A') {
        const today = new Date();
        const divDate = new Date(stock.ex_div_date);
        const diffTime = divDate - today;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays > 0) {
            divTimer.innerText = `${diffDays} Days`;
            divTimer.style.color = 'var(--text-main)';
        } else {
            divTimer.innerText = "Passed";
            divTimer.style.color = 'var(--text-muted)';
        }
    } else {
        divTimer.innerText = "--";
    }

    // Load TradingView Widget
    loadTradingViewWidget(stock.symbol);

    modal.classList.remove('hidden');
}

function loadTradingViewWidget(symbol) {
    // Basic TradingView Embedded Widget
    const container = document.getElementById('tvChartContainer');
    container.innerHTML = ''; // Clear

    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
    script.type = 'text/javascript';
    script.async = true;
    script.innerHTML = JSON.stringify({
        "autosize": true,
        "symbol": `${symbol}`,
        "interval": "D",
        "timezone": "Etc/UTC",
        "theme": "dark",
        "style": "1", // Line chart is 2, Candles is 1
        "locale": "en",
        "enable_publishing": false,
        "hide_top_toolbar": true,
        "hide_legend": true,
        "save_image": false,
        "hide_volume": true,
        "scalePosition": "right",
        "calendar": false,
        "support_host": "https://www.tradingview.com",
        "withdateranges": true, // Show bottom timeline ranges (1D 5D 1M etc)
        "range": "12M" // Default range
    });
    container.appendChild(script);
}
