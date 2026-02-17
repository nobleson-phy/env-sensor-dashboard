/* ── Dashboard client-side logic ───────────────────────────────── */

const POLL_LATEST_MS  = 5000;
const POLL_HISTORY_MS = 60000;

const chartColors = {
    temperature: '#f87171',
    humidity:    '#60a5fa',
    eco2:        '#fb923c',
    etvoc:       '#a78bfa',
    pressure:    '#34d399',
    noise:       '#fbbf24',
    light:       '#6c8cff',
};

const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 300 },
    interaction: { mode: 'index', intersect: false },
    plugins: {
        legend: { labels: { color: '#8b8fa3', boxWidth: 12, padding: 16 } },
        tooltip: { backgroundColor: '#1a1d27', borderColor: '#2a2e3a', borderWidth: 1 },
    },
    scales: {
        x: {
            type: 'time',
            ticks: { color: '#8b8fa3', maxTicksLimit: 10 },
            grid:  { color: 'rgba(42,46,58,0.5)' },
        },
    },
};

function makeYAxis(id, label, color, position = 'left') {
    return {
        [id]: {
            position,
            ticks: { color },
            grid:  { color: 'rgba(42,46,58,0.3)', drawOnChartArea: position === 'left' },
            title: { display: true, text: label, color },
        },
    };
}

/* ── Chart instances ──────────────────────────────────────────── */
let charts = {};

function initCharts() {
    // Temperature & Humidity (dual axis)
    charts.tempHum = new Chart(document.getElementById('chart-temp-hum'), {
        type: 'line',
        data: {
            datasets: [
                { label: 'Temperature (°C)', borderColor: chartColors.temperature, backgroundColor: 'rgba(248,113,113,0.1)', yAxisID: 'yTemp', tension: 0.3, pointRadius: 0, borderWidth: 2, data: [] },
                { label: 'Humidity (%)',      borderColor: chartColors.humidity,    backgroundColor: 'rgba(96,165,250,0.1)',  yAxisID: 'yHum',  tension: 0.3, pointRadius: 0, borderWidth: 2, data: [] },
            ],
        },
        options: {
            ...chartDefaults,
            scales: {
                ...chartDefaults.scales,
                ...makeYAxis('yTemp', '°C', chartColors.temperature, 'left'),
                ...makeYAxis('yHum',  '%',  chartColors.humidity,    'right'),
            },
        },
    });

    // Air quality (eCO2 + eTVOC, dual axis)
    charts.air = new Chart(document.getElementById('chart-air'), {
        type: 'line',
        data: {
            datasets: [
                { label: 'eCO2 (ppm)',   borderColor: chartColors.eco2,  backgroundColor: 'rgba(251,146,60,0.1)', yAxisID: 'yCO2',  tension: 0.3, pointRadius: 0, borderWidth: 2, data: [] },
                { label: 'eTVOC (ppb)',   borderColor: chartColors.etvoc, backgroundColor: 'rgba(167,139,250,0.1)', yAxisID: 'yTVOC', tension: 0.3, pointRadius: 0, borderWidth: 2, data: [] },
            ],
        },
        options: {
            ...chartDefaults,
            scales: {
                ...chartDefaults.scales,
                ...makeYAxis('yCO2',  'ppm', chartColors.eco2,  'left'),
                ...makeYAxis('yTVOC', 'ppb', chartColors.etvoc, 'right'),
            },
        },
    });

    // Pressure
    charts.pressure = new Chart(document.getElementById('chart-pressure'), {
        type: 'line',
        data: {
            datasets: [
                { label: 'Pressure (hPa)', borderColor: chartColors.pressure, backgroundColor: 'rgba(52,211,153,0.1)', tension: 0.3, pointRadius: 0, borderWidth: 2, fill: true, data: [] },
            ],
        },
        options: {
            ...chartDefaults,
            scales: {
                ...chartDefaults.scales,
                y: {
                    ticks: { color: '#8b8fa3' },
                    grid:  { color: 'rgba(42,46,58,0.5)' },
                    title: { display: true, text: 'hPa', color: chartColors.pressure },
                },
            },
        },
    });

    // Noise + Light (dual axis)
    charts.noiseLight = new Chart(document.getElementById('chart-noise-light'), {
        type: 'line',
        data: {
            datasets: [
                { label: 'Noise (dB)', borderColor: chartColors.noise, backgroundColor: 'rgba(251,191,36,0.1)', yAxisID: 'yNoise', tension: 0.3, pointRadius: 0, borderWidth: 2, data: [] },
                { label: 'Light (lx)', borderColor: chartColors.light, backgroundColor: 'rgba(108,140,255,0.1)', yAxisID: 'yLight', tension: 0.3, pointRadius: 0, borderWidth: 2, data: [] },
            ],
        },
        options: {
            ...chartDefaults,
            scales: {
                ...chartDefaults.scales,
                ...makeYAxis('yNoise', 'dB', chartColors.noise, 'left'),
                ...makeYAxis('yLight', 'lx', chartColors.light, 'right'),
            },
        },
    });
}

/* ── Update cards ─────────────────────────────────────────────── */
const thresholds = {
    temperature: [
        [35, 'danger'], [30, 'caution'], [28, 'warning'], [0, 'good'],
    ],
    humidity: [
        [80, 'danger'], [70, 'warning'], [0, 'good'],
    ],
    eco2: [
        [2500, 'danger'], [1500, 'caution'], [1000, 'warning'], [0, 'good'],
    ],
    etvoc: [
        [500, 'danger'], [300, 'caution'], [100, 'warning'], [0, 'good'],
    ],
    noise: [
        [70, 'danger'], [60, 'caution'], [50, 'warning'], [0, 'good'],
    ],
    heat_stroke: [
        [31, 'danger'], [28, 'caution'], [25, 'warning'], [0, 'good'],
    ],
    discomfort: [
        [85, 'danger'], [80, 'caution'], [75, 'warning'], [0, 'good'],
    ],
};

function getLevel(metric, value) {
    const t = thresholds[metric];
    if (!t) return 'info';
    for (const [min, level] of t) {
        if (value >= min) return level;
    }
    return 'good';
}

function updateCards(data) {
    const metrics = ['temperature', 'humidity', 'pressure', 'light', 'noise', 'eco2', 'etvoc', 'discomfort', 'heat_stroke'];
    for (const m of metrics) {
        const el = document.getElementById('val-' + m);
        if (!el || data[m] === undefined) continue;

        let display = data[m];
        if (typeof display === 'number') {
            if (m === 'pressure') display = display.toFixed(1);
            else if (Number.isInteger(display)) display = display;
            else display = display.toFixed(1);
        }
        el.textContent = display;

        const card = document.getElementById('card-' + m);
        card.className = 'card level-' + getLevel(m, data[m]);
    }
}

/* ── Update charts ────────────────────────────────────────────── */
function updateCharts(history) {
    const ts = history.map(r => r.timestamp);

    const toPoints = (key) => history.map((r, i) => ({ x: ts[i], y: r[key] }));

    charts.tempHum.data.datasets[0].data = toPoints('temperature');
    charts.tempHum.data.datasets[1].data = toPoints('humidity');
    charts.tempHum.update('none');

    charts.air.data.datasets[0].data = toPoints('eco2');
    charts.air.data.datasets[1].data = toPoints('etvoc');
    charts.air.update('none');

    charts.pressure.data.datasets[0].data = toPoints('pressure');
    charts.pressure.update('none');

    charts.noiseLight.data.datasets[0].data = toPoints('noise');
    charts.noiseLight.data.datasets[1].data = toPoints('light');
    charts.noiseLight.update('none');
}

/* ── Polling ──────────────────────────────────────────────────── */
async function fetchLatest() {
    try {
        const res = await fetch('/api/latest');
        if (!res.ok) throw new Error(res.status);
        const data = await res.json();
        updateCards(data);
        setStatus(true);
    } catch {
        setStatus(false);
    }
}

async function fetchHistory() {
    try {
        const hours = document.getElementById('history-range').value;
        const res = await fetch('/api/history?hours=' + hours);
        if (!res.ok) throw new Error(res.status);
        const data = await res.json();
        updateCharts(data);
    } catch (e) {
        console.error('Failed to fetch history:', e);
    }
}

function setStatus(online) {
    const dot  = document.getElementById('status-dot');
    const text = document.getElementById('status-text');
    if (online) {
        dot.className = 'dot online';
        text.textContent = 'Live';
    } else {
        dot.className = 'dot offline';
        text.textContent = 'Disconnected';
    }
}

/* ── Init ─────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    fetchLatest();
    fetchHistory();

    setInterval(fetchLatest,  POLL_LATEST_MS);
    setInterval(fetchHistory, POLL_HISTORY_MS);

    document.getElementById('history-range').addEventListener('change', fetchHistory);
});
