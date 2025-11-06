#!/usr/bin/env python3
"""
Flask API Server for System Resource Monitor
Provides real-time system metrics via REST API
"""

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import psutil
import platform
import time
import os
from datetime import datetime

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Store last network I/O for rate calculation
last_net_io = psutil.net_io_counters()
last_net_time = time.time()


@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_file('index.html')


@app.route('/api/system-info')
def get_system_info():
    """Get static system information"""
    try:
        boot_time = psutil.boot_time()
        uptime_hours = (time.time() - boot_time) / 3600

        info = {
            'platform': f"{platform.system()} {platform.release()}",
            'cpu_cores': psutil.cpu_count(logical=True),
            'cpu_cores_physical': psutil.cpu_count(logical=False),
            'total_memory_gb': psutil.virtual_memory().total / (1024 ** 3),
            'uptime_hours': uptime_hours,
            'hostname': platform.node(),
            'python_version': platform.python_version()
        }

        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/monitor')
def get_monitoring_data():
    """Get current system resource usage"""
    global last_net_io, last_net_time

    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_freq = psutil.cpu_freq()

        # Memory
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Disk
        disk = psutil.disk_usage('/')

        # Network - Calculate rates
        current_net_io = psutil.net_io_counters()
        current_time = time.time()
        time_delta = current_time - last_net_time

        bytes_sent_delta = current_net_io.bytes_sent - last_net_io.bytes_sent
        bytes_recv_delta = current_net_io.bytes_recv - last_net_io.bytes_recv

        upload_rate = (bytes_sent_delta / time_delta) / (1024 ** 2)  # MB/s
        download_rate = (bytes_recv_delta / time_delta) / (1024 ** 2)  # MB/s

        # Update last values
        last_net_io = current_net_io
        last_net_time = current_time

        # Temperature (if available)
        cpu_temp = 0
        try:
            temps = psutil.sensors_temperatures()
            if 'coretemp' in temps:
                cpu_temp = temps['coretemp'][0].current
            elif 'cpu_thermal' in temps:
                cpu_temp = temps['cpu_thermal'][0].current
        except (AttributeError, KeyError):
            pass

        data = {
            # CPU
            'cpu_percent': round(cpu_percent, 2),
            'cpu_freq_current': cpu_freq.current if cpu_freq else 0,
            'cpu_temp': round(cpu_temp, 2),

            # Memory
            'mem_percent': round(mem.percent, 2),
            'mem_used_gb': round(mem.used / (1024 ** 3), 2),
            'mem_total_gb': round(mem.total / (1024 ** 3), 2),
            'swap_percent': round(swap.percent, 2),

            # Disk
            'disk_percent': round(disk.percent, 2),
            'disk_used_gb': round(disk.used / (1024 ** 3), 2),
            'disk_total_gb': round(disk.total / (1024 ** 3), 2),

            # Network
            'net_upload_mbps': round(upload_rate, 4),
            'net_download_mbps': round(download_rate, 4),
            'net_total_sent_gb': round(current_net_io.bytes_sent / (1024 ** 3), 3),
            'net_total_recv_gb': round(current_net_io.bytes_recv / (1024 ** 3), 3),

            # Timestamp
            'timestamp': datetime.now().isoformat()
        }

        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export-pdf', methods=['POST'])
def export_pdf():
    """Generate PDF report from collected data"""
    try:
        data = request.json
        collected_data = data.get('data', [])
        stats = data.get('stats', {})

        if not collected_data:
            return jsonify({'error': 'No data provided'}), 400

        # Import the PDF generator from system_monitor.py
        # For now, we'll return a simple message
        # In production, you would use the PDFReportGenerator class

        return jsonify({
            'message': 'PDF generation endpoint',
            'data_points': len(collected_data),
            'note': 'Full PDF generation requires integration with system_monitor.py'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0'
    })


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500


def main():
    """Main entry point"""
    print("=" * 60)
    print("🚀 System Resource Monitor - Web Server")
    print("=" * 60)
    print(f"📍 Server: http://localhost:5000")
    print(f"📊 Dashboard: http://localhost:5000/")
    print(f"🔌 API: http://localhost:5000/api/monitor")
    print(f"💡 System Info: http://localhost:5000/api/system-info")
    print("=" * 60)
    print("\n⌨️  Press Ctrl+C to stop the server\n")

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )


if __name__ == '__main__':
    main()
