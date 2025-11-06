# 🖥️ Real-Time System Resource Monitoring Application

A comprehensive Python-based system monitoring tool that tracks CPU, memory, GPU, disk usage, and network traffic in real-time, then generates detailed PDF reports with visualizations and analytics.

## ✨ Features

- **Real-time Monitoring**: Live dashboard showing all system metrics updated every second
- **Comprehensive Metrics**:
  - 🔴 CPU usage and frequency
  - 💙 Memory (RAM) and swap usage
  - 💚 Disk space and I/O
  - 🟣 Network upload/download rates
  - 🟡 GPU usage and memory (NVIDIA GPUs)
  - 🌡️ Temperature sensors (CPU/GPU)

- **Professional PDF Reports**: Automatically generated reports including:
  - Executive summary with system information
  - Statistical tables (average, max, min, standard deviation)
  - Time-series charts for all metrics
  - Automated observations and recommendations

- **Cross-Platform**: Works on Windows and Linux
- **Configurable**: Customizable monitoring duration and sampling intervals
- **Clean Design**: Intuitive visualizations and well-structured reports

## 📋 Requirements

- Python 3.7 or higher
- pip (Python package manager)

## 🚀 Installation

1. **Clone or download this repository**

2. **Install dependencies**:

```bash
pip install -r requirements.txt
```

3. **Optional: Install GPU monitoring** (only for NVIDIA GPUs):

```bash
pip install GPUtil
```

Note: GPU monitoring requires NVIDIA GPU drivers and `nvidia-smi` to be installed on your system.

## 🎯 Usage

### Basic Usage

Monitor system for 5 minutes (default) and generate report:

```bash
python system_monitor.py
```

This will:
- Display a live dashboard window
- Track metrics for 5 minutes
- Save report as `system_monitor_report.pdf`

### Advanced Usage

#### Custom Duration

Monitor for 2 minutes:

```bash
python system_monitor.py --duration 120
```

#### Custom Output Path

Save report with custom filename:

```bash
python system_monitor.py --output my_custom_report.pdf
```

#### Custom Sampling Interval

Sample every 0.5 seconds:

```bash
python system_monitor.py --interval 0.5
```

#### Combined Options

```bash
python system_monitor.py --duration 600 --interval 2 --output detailed_report.pdf
```

### Testing (Quick Run)

For testing, run a short 10-second monitoring session:

```bash
python system_monitor.py --duration 10
```

## 📊 Sample Output

After successful execution, you'll see console output like this:

```
================================================================================
🖥️  SYSTEM RESOURCE MONITORING APPLICATION
================================================================================
⏱️  Duration: 300 seconds (5.0 minutes)
📊 Sampling interval: 1.0 seconds
📄 Output: system_monitor_report.pdf
💻 Platform: Linux 5.15.0
🔧 Python: 3.10.12
🎮 GPU monitoring: Enabled
================================================================================

🚀 Starting monitoring...

⏳ Progress: 100.0% | Samples: 300/300 | Time: 300/300s

✅ Monitoring complete! Collected 300 samples.

================================================================================
📊 MONITORING SUMMARY
================================================================================

📈 Key Metrics:
  CPU Usage:    Avg 45.3% | Max 89.2%
  Memory Usage: Avg 62.1% | Max 68.5%
  Disk Usage:   Avg 48.2% | Max 48.3%
  Network Up:   Avg 0.152 MB/s | Max 2.341 MB/s
  Network Down: Avg 0.428 MB/s | Max 5.123 MB/s
  GPU Usage:    Avg 12.4% | Max 56.7%

================================================================================

📊 Generating PDF report: system_monitor_report.pdf
✅ PDF report generated successfully!

================================================================================
✅ MONITORING COMPLETE
================================================================================
📄 Report saved to: /home/user/system_monitor_report.pdf
📊 Total samples collected: 300
⏱️  Total duration: 300 seconds
================================================================================
```

## 📄 PDF Report Structure

The generated PDF report contains:

### Page 1: Title and Overview
- Execution timestamp
- Monitoring duration
- System information (OS, CPU, memory)
- Configuration details

### Page 2: Summary Statistics Table
- Average, maximum, minimum, and standard deviation
- All tracked metrics in one comprehensive table

### Page 3-5: Detailed Charts
- CPU and Memory usage over time
- Disk and Network activity
- GPU usage and temperatures
- All charts include average lines and filled areas

### Page 6: Automated Observations
- Intelligent analysis of resource usage patterns
- Color-coded warnings for high usage
- Personalized recommendations
- Stability analysis

## 🛠️ Command-Line Options

```
usage: system_monitor.py [-h] [-d DURATION] [-i INTERVAL] [-o OUTPUT]

Real-time System Resource Monitoring Application

optional arguments:
  -h, --help            show this help message and exit
  -d DURATION, --duration DURATION
                        Monitoring duration in seconds (default: 300 = 5 minutes)
  -i INTERVAL, --interval INTERVAL
                        Sampling interval in seconds (default: 1.0)
  -o OUTPUT, --output OUTPUT
                        Output PDF file path (default: system_monitor_report.pdf)
```

## 🔧 Troubleshooting

### GPU Monitoring Not Working

If you see "GPU monitoring not available":
1. Check if you have an NVIDIA GPU
2. Install NVIDIA drivers
3. Install GPUtil: `pip install GPUtil`
4. Verify `nvidia-smi` command works in terminal

### Temperature Sensors Not Available

Temperature monitoring depends on system sensors:
- **Linux**: Usually works on most systems (uses `psutil.sensors_temperatures()`)
- **Windows**: May not be available on all systems
- The application works fine without temperature data

### Display Issues (Headless Servers)

If running on a server without display:
- The real-time visualization requires a display
- Consider using SSH with X11 forwarding
- Or modify the code to run in headless mode (remove matplotlib.pyplot.show())

## 📁 Project Structure

```
.
├── system_monitor.py       # Main application
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🧪 Testing Recommendations

1. **Quick Test** (10 seconds):
   ```bash
   python system_monitor.py --duration 10
   ```

2. **Normal Test** (1 minute):
   ```bash
   python system_monitor.py --duration 60
   ```

3. **Full Test** (5 minutes - default):
   ```bash
   python system_monitor.py
   ```

## 💡 Use Cases

- **System Performance Analysis**: Understand resource usage patterns
- **Benchmarking**: Monitor system during benchmark tests
- **Capacity Planning**: Identify resource bottlenecks
- **Troubleshooting**: Diagnose performance issues
- **Documentation**: Generate reports for system administrators
- **Development**: Monitor resource usage during application development

## 🌟 Key Features Explained

### Real-Time Dashboard
- Updates every second (configurable)
- Six panels showing different metrics
- Color-coded for easy interpretation
- Automatic scaling based on data range

### Intelligent Analysis
- Automatically identifies high usage patterns
- Generates recommendations based on thresholds
- Calculates stability metrics (standard deviation)
- Highlights potential issues

### Cross-Platform Compatibility
- Tested on Linux and Windows
- Graceful degradation (features work even if GPU/temp unavailable)
- Uses platform-appropriate sensor detection

## 📝 Code Quality

- **Well-Documented**: Every function has detailed docstrings
- **Type Hints**: Modern Python type annotations
- **Error Handling**: Graceful handling of missing sensors/features
- **Modular Design**: Clean separation of concerns (monitoring, visualization, reporting)
- **PEP 8 Compliant**: Follows Python style guidelines

## 🤝 Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## 📄 License

MIT License - feel free to use this in your projects!

## 👨‍💻 Author

Created by a System Monitoring Engineer with expertise in Python system programming.

## 🙏 Acknowledgments

- Built with [psutil](https://github.com/giampaolo/psutil) for system monitoring
- Uses [matplotlib](https://matplotlib.org/) for visualization
- [pandas](https://pandas.pydata.org/) for data manipulation
- [GPUtil](https://github.com/anderskm/gputil) for GPU monitoring

---

**Happy Monitoring! 🚀**
