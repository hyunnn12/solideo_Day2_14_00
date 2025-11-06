// ============================================
// System Resource Monitor - Web Application
// ============================================

class SystemMonitor {
    constructor() {
        this.isMonitoring = false;
        this.monitoringInterval = null;
        this.startTime = null;
        this.elapsedTimer = null;
        this.dataLog = [];

        // Statistics
        this.stats = {
            cpu: { values: [], avg: 0, max: 0 },
            memory: { values: [], avg: 0, max: 0 },
            disk: { values: [], avg: 0, max: 0 },
            network: { upload: [], download: [] }
        };

        // Chart instances
        this.cpuMemoryChart = null;
        this.networkChart = null;

        // Initialize
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupCharts();
        this.updateCurrentTime();
        this.loadTheme();

        // Check API connection
        this.checkAPIConnection();
    }

    // ============================================
    // Event Listeners
    // ============================================
    setupEventListeners() {
        // Theme toggle
        document.getElementById('themeToggle').addEventListener('click', () => {
            this.toggleTheme();
        });

        // Control buttons
        document.getElementById('startBtn').addEventListener('click', () => {
            this.startMonitoring();
        });

        document.getElementById('stopBtn').addEventListener('click', () => {
            this.stopMonitoring();
        });

        document.getElementById('exportBtn').addEventListener('click', () => {
            this.exportToPDF();
        });

        document.getElementById('clearLogBtn').addEventListener('click', () => {
            this.clearDataLog();
        });

        // Update time every second
        setInterval(() => this.updateCurrentTime(), 1000);
    }

    // ============================================
    // Theme Management
    // ============================================
    toggleTheme() {
        const html = document.documentElement;
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        html.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);

        const icon = document.querySelector('#themeToggle i');
        icon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';

        // Update charts
        this.updateChartTheme();
    }

    loadTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);

        const icon = document.querySelector('#themeToggle i');
        icon.className = savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }

    updateChartTheme() {
        const textColor = getComputedStyle(document.documentElement)
            .getPropertyValue('--text-primary').trim();

        const gridColor = getComputedStyle(document.documentElement)
            .getPropertyValue('--border-color').trim();

        [this.cpuMemoryChart, this.networkChart].forEach(chart => {
            if (chart) {
                chart.options.scales.x.ticks.color = textColor;
                chart.options.scales.y.ticks.color = textColor;
                chart.options.scales.x.grid.color = gridColor;
                chart.options.scales.y.grid.color = gridColor;
                chart.update();
            }
        });
    }

    // ============================================
    // Chart Setup
    // ============================================
    setupCharts() {
        const textColor = getComputedStyle(document.documentElement)
            .getPropertyValue('--text-primary').trim();

        const gridColor = getComputedStyle(document.documentElement)
            .getPropertyValue('--border-color').trim();

        const commonOptions = {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    ticks: { color: textColor },
                    grid: { color: gridColor }
                },
                y: {
                    ticks: { color: textColor },
                    grid: { color: gridColor },
                    beginAtZero: true
                }
            },
            animation: {
                duration: 750,
                easing: 'easeInOutQuart'
            }
        };

        // CPU & Memory Chart
        const cpuMemoryCtx = document.getElementById('cpuMemoryChart').getContext('2d');
        this.cpuMemoryChart = new Chart(cpuMemoryCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'CPU (%)',
                        data: [],
                        borderColor: 'rgba(102, 126, 234, 1)',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Memory (%)',
                        data: [],
                        borderColor: 'rgba(245, 87, 108, 1)',
                        backgroundColor: 'rgba(245, 87, 108, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                ...commonOptions,
                scales: {
                    ...commonOptions.scales,
                    y: {
                        ...commonOptions.scales.y,
                        max: 100
                    }
                }
            }
        });

        // Network Chart
        const networkCtx = document.getElementById('networkChart').getContext('2d');
        this.networkChart = new Chart(networkCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Upload (MB/s)',
                        data: [],
                        borderColor: 'rgba(67, 233, 123, 1)',
                        backgroundColor: 'rgba(67, 233, 123, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Download (MB/s)',
                        data: [],
                        borderColor: 'rgba(56, 249, 215, 1)',
                        backgroundColor: 'rgba(56, 249, 215, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: commonOptions
        });
    }

    // ============================================
    // API Communication
    // ============================================
    async checkAPIConnection() {
        try {
            const response = await fetch('/api/system-info');
            if (response.ok) {
                const data = await response.json();
                this.updateSystemInfo(data);
                this.updateStatus('연결됨', true);
                this.addAlert('API 서버에 성공적으로 연결되었습니다.', 'success');
            }
        } catch (error) {
            this.updateStatus('연결 실패', false);
            this.addAlert('API 서버에 연결할 수 없습니다. 시뮬레이션 모드로 실행됩니다.', 'warning');
            console.warn('API connection failed, using simulation mode');
        }
    }

    async fetchMonitoringData() {
        try {
            const response = await fetch('/api/monitor');
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            // Fallback to simulation data
            return this.generateSimulationData();
        }
        return this.generateSimulationData();
    }

    // ============================================
    // Monitoring Control
    // ============================================
    async startMonitoring() {
        if (this.isMonitoring) return;

        const duration = parseInt(document.getElementById('duration').value);
        const interval = parseFloat(document.getElementById('interval').value);

        // Validation
        if (duration < 10 || duration > 3600) {
            this.addAlert('모니터링 시간은 10초에서 3600초 사이여야 합니다.', 'warning');
            return;
        }

        if (interval < 0.5 || interval > 10) {
            this.addAlert('업데이트 간격은 0.5초에서 10초 사이여야 합니다.', 'warning');
            return;
        }

        this.isMonitoring = true;
        this.startTime = Date.now();
        this.dataLog = [];

        // Reset stats
        this.stats = {
            cpu: { values: [], avg: 0, max: 0 },
            memory: { values: [], avg: 0, max: 0 },
            disk: { values: [], avg: 0, max: 0 },
            network: { upload: [], download: [] }
        };

        // Clear charts
        this.cpuMemoryChart.data.labels = [];
        this.cpuMemoryChart.data.datasets[0].data = [];
        this.cpuMemoryChart.data.datasets[1].data = [];
        this.cpuMemoryChart.update();

        this.networkChart.data.labels = [];
        this.networkChart.data.datasets[0].data = [];
        this.networkChart.data.datasets[1].data = [];
        this.networkChart.update();

        // Update UI
        document.getElementById('startBtn').disabled = true;
        document.getElementById('stopBtn').disabled = false;
        this.updateStatus('모니터링 중', true);
        this.addAlert(`${duration}초 동안 모니터링을 시작합니다.`, 'info');

        // Start monitoring loop
        this.monitoringInterval = setInterval(async () => {
            const elapsed = Math.floor((Date.now() - this.startTime) / 1000);

            if (elapsed >= duration) {
                this.stopMonitoring();
                this.addAlert('모니터링이 완료되었습니다!', 'success');
                return;
            }

            const data = await this.fetchMonitoringData();
            this.updateDashboard(data);
        }, interval * 1000);

        // Start elapsed time timer
        this.elapsedTimer = setInterval(() => {
            this.updateElapsedTime();
        }, 1000);

        // Initial data fetch
        const initialData = await this.fetchMonitoringData();
        this.updateDashboard(initialData);
    }

    stopMonitoring() {
        if (!this.isMonitoring) return;

        this.isMonitoring = false;

        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = null;
        }

        if (this.elapsedTimer) {
            clearInterval(this.elapsedTimer);
            this.elapsedTimer = null;
        }

        // Update UI
        document.getElementById('startBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
        this.updateStatus('정지됨', false);
        this.addAlert('모니터링이 정지되었습니다.', 'info');
    }

    // ============================================
    // Data Update
    // ============================================
    updateDashboard(data) {
        // Update current values
        document.getElementById('cpuValue').textContent = data.cpu_percent.toFixed(1) + '%';
        document.getElementById('memValue').textContent = data.mem_percent.toFixed(1) + '%';
        document.getElementById('diskValue').textContent = data.disk_percent.toFixed(1) + '%';
        document.getElementById('netUpload').textContent = data.net_upload_mbps.toFixed(3) + ' MB/s';
        document.getElementById('netDownload').textContent = data.net_download_mbps.toFixed(3) + ' MB/s';

        // Update disk info
        document.getElementById('diskFree').textContent = (data.disk_total_gb - data.disk_used_gb).toFixed(2) + ' GB';
        document.getElementById('diskTotal').textContent = data.disk_total_gb.toFixed(2) + ' GB';

        // Update network totals
        document.getElementById('netTotalUp').textContent = data.net_total_sent_gb.toFixed(3) + ' GB';
        document.getElementById('netTotalDown').textContent = data.net_total_recv_gb.toFixed(3) + ' GB';

        // Update progress bars
        document.getElementById('cpuProgress').style.width = data.cpu_percent + '%';
        document.getElementById('memProgress').style.width = data.mem_percent + '%';
        document.getElementById('diskProgress').style.width = data.disk_percent + '%';

        // Update statistics
        this.updateStatistics(data);

        // Update charts
        this.updateCharts(data);

        // Add to data log
        this.addToDataLog(data);

        // Check for alerts
        this.checkThresholds(data);
    }

    updateStatistics(data) {
        // CPU
        this.stats.cpu.values.push(data.cpu_percent);
        this.stats.cpu.avg = this.calculateAverage(this.stats.cpu.values);
        this.stats.cpu.max = Math.max(...this.stats.cpu.values);

        document.getElementById('cpuAvg').textContent = this.stats.cpu.avg.toFixed(1) + '%';
        document.getElementById('cpuMax').textContent = this.stats.cpu.max.toFixed(1) + '%';

        // Memory
        this.stats.memory.values.push(data.mem_percent);
        this.stats.memory.avg = this.calculateAverage(this.stats.memory.values);
        this.stats.memory.max = Math.max(...this.stats.memory.values);

        document.getElementById('memAvg').textContent = this.stats.memory.avg.toFixed(1) + '%';
        document.getElementById('memMax').textContent = this.stats.memory.max.toFixed(1) + '%';
    }

    updateCharts(data) {
        const timeLabel = new Date().toLocaleTimeString();
        const maxDataPoints = 50;

        // CPU & Memory Chart
        this.cpuMemoryChart.data.labels.push(timeLabel);
        this.cpuMemoryChart.data.datasets[0].data.push(data.cpu_percent);
        this.cpuMemoryChart.data.datasets[1].data.push(data.mem_percent);

        // Keep only last N data points
        if (this.cpuMemoryChart.data.labels.length > maxDataPoints) {
            this.cpuMemoryChart.data.labels.shift();
            this.cpuMemoryChart.data.datasets[0].data.shift();
            this.cpuMemoryChart.data.datasets[1].data.shift();
        }

        this.cpuMemoryChart.update('none'); // Update without animation for smoother real-time

        // Network Chart
        this.networkChart.data.labels.push(timeLabel);
        this.networkChart.data.datasets[0].data.push(data.net_upload_mbps);
        this.networkChart.data.datasets[1].data.push(data.net_download_mbps);

        if (this.networkChart.data.labels.length > maxDataPoints) {
            this.networkChart.data.labels.shift();
            this.networkChart.data.datasets[0].data.shift();
            this.networkChart.data.datasets[1].data.shift();
        }

        this.networkChart.update('none');
    }

    addToDataLog(data) {
        const time = new Date().toLocaleTimeString();
        this.dataLog.push({ time, ...data });

        const tbody = document.getElementById('dataTableBody');
        const row = tbody.insertRow(0); // Insert at top

        row.insertCell(0).textContent = time;
        row.insertCell(1).textContent = data.cpu_percent.toFixed(1);
        row.insertCell(2).textContent = data.mem_percent.toFixed(1);
        row.insertCell(3).textContent = data.disk_percent.toFixed(1);
        row.insertCell(4).textContent = data.net_upload_mbps.toFixed(3);
        row.insertCell(5).textContent = data.net_download_mbps.toFixed(3);

        // Keep only last 100 rows
        while (tbody.rows.length > 100) {
            tbody.deleteRow(tbody.rows.length - 1);
        }
    }

    clearDataLog() {
        document.getElementById('dataTableBody').innerHTML = '';
        this.dataLog = [];
        this.addAlert('데이터 로그가 삭제되었습니다.', 'info');
    }

    // ============================================
    // System Info Update
    // ============================================
    updateSystemInfo(info) {
        document.getElementById('platform').textContent = info.platform || '-';
        document.getElementById('cpuCores').textContent = info.cpu_cores || '-';
        document.getElementById('totalMemory').textContent = info.total_memory_gb ?
            info.total_memory_gb.toFixed(2) + ' GB' : '-';

        if (info.uptime_hours !== undefined) {
            const hours = Math.floor(info.uptime_hours);
            const minutes = Math.floor((info.uptime_hours - hours) * 60);
            document.getElementById('uptime').textContent = `${hours}h ${minutes}m`;
        }
    }

    // ============================================
    // Alerts & Notifications
    // ============================================
    checkThresholds(data) {
        // CPU threshold
        if (data.cpu_percent > 80) {
            this.addAlert(`높은 CPU 사용률: ${data.cpu_percent.toFixed(1)}%`, 'danger');
        }

        // Memory threshold
        if (data.mem_percent > 80) {
            this.addAlert(`높은 메모리 사용률: ${data.mem_percent.toFixed(1)}%`, 'danger');
        }

        // Disk threshold
        if (data.disk_percent > 90) {
            this.addAlert(`디스크 공간 부족: ${data.disk_percent.toFixed(1)}%`, 'danger');
        } else if (data.disk_percent > 75) {
            this.addAlert(`디스크 공간 경고: ${data.disk_percent.toFixed(1)}%`, 'warning');
        }
    }

    addAlert(message, type = 'info') {
        const alertsList = document.getElementById('alertsList');
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;

        const icons = {
            info: 'fa-info-circle',
            success: 'fa-check-circle',
            warning: 'fa-exclamation-triangle',
            danger: 'fa-exclamation-circle'
        };

        alert.innerHTML = `
            <i class="fas ${icons[type]}"></i>
            <span>${message}</span>
        `;

        alertsList.insertBefore(alert, alertsList.firstChild);

        // Keep only last 5 alerts
        while (alertsList.children.length > 5) {
            alertsList.removeChild(alertsList.lastChild);
        }

        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (alert.parentElement) {
                alert.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => alert.remove(), 300);
            }
        }, 10000);
    }

    // ============================================
    // UI Helpers
    // ============================================
    updateStatus(text, isActive) {
        document.getElementById('statusText').textContent = text;
        const statusDot = document.getElementById('statusDot');

        if (isActive) {
            statusDot.classList.add('active');
        } else {
            statusDot.classList.remove('active');
        }
    }

    updateElapsedTime() {
        if (!this.startTime) return;

        const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
        const minutes = Math.floor(elapsed / 60);
        const seconds = elapsed % 60;

        document.getElementById('elapsedTime').textContent =
            `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }

    updateCurrentTime() {
        const now = new Date();
        document.getElementById('currentTime').textContent = now.toLocaleString('ko-KR');
    }

    // ============================================
    // Data Export
    // ============================================
    async exportToPDF() {
        if (this.dataLog.length === 0) {
            this.addAlert('내보낼 데이터가 없습니다.', 'warning');
            return;
        }

        const loading = document.getElementById('loadingOverlay');
        loading.classList.add('active');

        try {
            const response = await fetch('/api/export-pdf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    data: this.dataLog,
                    stats: this.stats
                })
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `system_monitor_${Date.now()}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();

                this.addAlert('PDF가 성공적으로 생성되었습니다!', 'success');
            } else {
                throw new Error('PDF generation failed');
            }
        } catch (error) {
            console.error('Export error:', error);
            this.addAlert('PDF 생성에 실패했습니다. 콘솔을 확인하세요.', 'danger');
        } finally {
            loading.classList.remove('active');
        }
    }

    // ============================================
    // Simulation Data (Fallback)
    // ============================================
    generateSimulationData() {
        return {
            cpu_percent: Math.random() * 100,
            mem_percent: 40 + Math.random() * 40,
            disk_percent: 45 + Math.random() * 10,
            disk_used_gb: 200 + Math.random() * 50,
            disk_total_gb: 500,
            net_upload_mbps: Math.random() * 5,
            net_download_mbps: Math.random() * 10,
            net_total_sent_gb: Math.random() * 100,
            net_total_recv_gb: Math.random() * 200
        };
    }

    // ============================================
    // Utility Functions
    // ============================================
    calculateAverage(arr) {
        if (arr.length === 0) return 0;
        return arr.reduce((a, b) => a + b, 0) / arr.length;
    }
}

// ============================================
// Initialize Application
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    const monitor = new SystemMonitor();

    // Make it globally accessible for debugging
    window.systemMonitor = monitor;

    console.log('%c System Monitor Initialized ', 'background: #667eea; color: white; font-size: 16px; padding: 5px 10px; border-radius: 5px;');
    console.log('Version: 2.0');
    console.log('Features: Real-time monitoring, Interactive charts, PDF export');
});

// Add slide out animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(-20px);
        }
    }
`;
document.head.appendChild(style);
