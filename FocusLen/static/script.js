let analysisInterval = null;
let pieChartInstance = null;
let barChartInstance = null;

// Initialization for charts
function initCharts() {
    const pieCtx = document.getElementById('pieChart');
    if (pieCtx && !pieChartInstance) {
        pieChartInstance = new Chart(pieCtx, {
            type: 'doughnut',
            data: {
                labels: ['Focus', 'Distraction', 'Absence'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: ['#10b981', '#ef4444', '#9ca3af'],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    }

    const barCtx = document.getElementById('barChart');
    if (barCtx && !barChartInstance) {
        barChartInstance = new Chart(barCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Seconds Active',
                    data: [],
                    backgroundColor: '#3b82f6',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, display: false },
                    x: { grid: { display: false } }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
}

function switchTab(tabId, event) {
    document.querySelectorAll('.nav-btn').forEach(btn => btn.classList.remove('active'));
    event.currentTarget.classList.add('active');

    document.querySelectorAll('.tab-content').forEach(tab => tab.style.display = 'none');
    document.getElementById(`${tabId}-tab`).style.display = 'block';

    if (tabId === 'history') {
        loadHistory();
    }
    
    if (tabId === 'analysis') {
        initCharts();
        fetchAnalysis();
        if (!analysisInterval) {
            analysisInterval = setInterval(fetchAnalysis, 1000);
        }
    } else {
        if (analysisInterval) {
            clearInterval(analysisInterval);
            analysisInterval = null;
        }
    }
}

function startTracking() {
    const btnStart = document.getElementById('start-btn');
    const btnStop = document.getElementById('stop-btn');
    const statusText = document.getElementById('status-text');
    const indicator = document.getElementById('status-indicator');

    btnStart.disabled = true;
    statusText.innerText = "Connecting process...";
    
    fetch('/start_tracking', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            btnStop.disabled = false;
            indicator.className = "indicator active";
            statusText.innerText = "Tracking Active";
        });
}

function stopTracking() {
    const btnStart = document.getElementById('start-btn');
    const btnStop = document.getElementById('stop-btn');
    const statusText = document.getElementById('status-text');
    const indicator = document.getElementById('status-indicator');

    btnStop.disabled = true;
    statusText.innerText = "Saving session...";

    fetch('/stop_tracking', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            btnStart.disabled = false;
            indicator.className = "indicator inactive";
            statusText.innerText = "Session successfully saved to History";
        });
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}m ${s}s`;
}

function fetchAnalysis() {
    fetch('/get_analysis')
        .then(res => res.json())
        .then(data => {
            document.getElementById('live-score').innerText = `${data.focus_score}%`;
            document.getElementById('live-focus').innerText = formatTime(data.focus_time);
            document.getElementById('live-distract').innerText = formatTime(data.distraction_time);
            document.getElementById('live-absent').innerText = formatTime(data.absence_time);
            
            if(pieChartInstance) {
                pieChartInstance.data.datasets[0].data = [data.focus_time, data.distraction_time, data.absence_time];
                pieChartInstance.update();
            }

            if(barChartInstance && data.app_usage) {
                barChartInstance.data.labels = data.app_usage.map(a => a.app);
                barChartInstance.data.datasets[0].data = data.app_usage.map(a => a.duration);
                barChartInstance.update();
            }
        });
}

function loadHistory() {
    fetch('/get_history')
        .then(res => res.json())
        .then(data => {
            const tbody = document.querySelector('#history-table tbody');
            tbody.innerHTML = '';
            
            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #6b7280; padding: 2rem;">No history records safely found. Complete a tracking session first.</td></tr>';
                return;
            }

            data.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${row.date}</td>
                    <td style="font-weight: 600; color: #111827;">${row.score}%</td>
                    <td>${formatTime(row.focus_time)}</td>
                    <td>${formatTime(row.distraction_time)}</td>
                    <td>${formatTime(row.absence_time)}</td>
                    <td><a href="/download_session_csv/${row.id}" style="color: #2563eb; text-decoration: none; font-size: 0.9rem; border: 1px solid #e5e7eb; padding: 0.25rem 0.75rem; border-radius: 4px; font-weight: 500;">Download CSV</a></td>
                `;
                tbody.appendChild(tr);
            });
        });
}
