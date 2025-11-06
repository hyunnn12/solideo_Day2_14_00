#!/usr/bin/env python3
"""
Real-time System Resource Monitoring Application

This script monitors CPU, memory, GPU, disk usage, and network traffic in real-time
for a configurable duration (default: 5 minutes), then generates a comprehensive
PDF report with visualizations and statistics.

Author: System Monitoring Engineer
License: MIT
"""

import argparse
import datetime
import os
import platform
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd
import psutil

# Optional GPU monitoring
try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    print("⚠️  GPUtil not available. GPU monitoring will be skipped.")


class SystemMonitor:
    """
    Main class for system resource monitoring.
    Collects CPU, memory, disk, network, and GPU metrics in real-time.
    """

    def __init__(self, duration_seconds: int = 300, interval_seconds: float = 1.0):
        """
        Initialize the system monitor.

        Args:
            duration_seconds: Total monitoring duration in seconds (default: 300 = 5 minutes)
            interval_seconds: Sampling interval in seconds (default: 1.0)
        """
        self.duration = duration_seconds
        self.interval = interval_seconds
        self.start_time = None
        self.data = defaultdict(list)
        self.timestamps = []

        # Initialize network counters for calculating rates
        self.last_net_io = psutil.net_io_counters()
        self.last_net_time = time.time()

    def get_cpu_info(self) -> Dict[str, float]:
        """
        Get current CPU usage and temperature (if available).

        Returns:
            Dictionary with CPU metrics
        """
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_freq = psutil.cpu_freq()

        result = {
            'cpu_percent': cpu_percent,
            'cpu_freq_current': cpu_freq.current if cpu_freq else 0,
        }

        # Try to get CPU temperature (works on some Linux systems)
        try:
            temps = psutil.sensors_temperatures()
            if 'coretemp' in temps:
                result['cpu_temp'] = temps['coretemp'][0].current
            elif 'cpu_thermal' in temps:
                result['cpu_temp'] = temps['cpu_thermal'][0].current
            else:
                result['cpu_temp'] = 0
        except (AttributeError, KeyError):
            result['cpu_temp'] = 0

        return result

    def get_memory_info(self) -> Dict[str, float]:
        """
        Get current memory usage statistics.

        Returns:
            Dictionary with memory metrics
        """
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            'mem_percent': mem.percent,
            'mem_used_gb': mem.used / (1024 ** 3),
            'mem_total_gb': mem.total / (1024 ** 3),
            'swap_percent': swap.percent,
        }

    def get_disk_info(self) -> Dict[str, float]:
        """
        Get current disk usage statistics.

        Returns:
            Dictionary with disk metrics
        """
        disk = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()

        return {
            'disk_percent': disk.percent,
            'disk_used_gb': disk.used / (1024 ** 3),
            'disk_total_gb': disk.total / (1024 ** 3),
            'disk_read_mb': disk_io.read_bytes / (1024 ** 2) if disk_io else 0,
            'disk_write_mb': disk_io.write_bytes / (1024 ** 2) if disk_io else 0,
        }

    def get_network_info(self) -> Dict[str, float]:
        """
        Get current network upload/download rates.

        Returns:
            Dictionary with network metrics (rates in MB/s)
        """
        current_net_io = psutil.net_io_counters()
        current_time = time.time()

        time_delta = current_time - self.last_net_time

        # Calculate rates
        bytes_sent_delta = current_net_io.bytes_sent - self.last_net_io.bytes_sent
        bytes_recv_delta = current_net_io.bytes_recv - self.last_net_io.bytes_recv

        upload_rate = (bytes_sent_delta / time_delta) / (1024 ** 2)  # MB/s
        download_rate = (bytes_recv_delta / time_delta) / (1024 ** 2)  # MB/s

        # Update last values
        self.last_net_io = current_net_io
        self.last_net_time = current_time

        return {
            'net_upload_mbps': upload_rate,
            'net_download_mbps': download_rate,
            'net_total_sent_gb': current_net_io.bytes_sent / (1024 ** 3),
            'net_total_recv_gb': current_net_io.bytes_recv / (1024 ** 3),
        }

    def get_gpu_info(self) -> Dict[str, float]:
        """
        Get current GPU usage and temperature (if available).

        Returns:
            Dictionary with GPU metrics
        """
        if not GPU_AVAILABLE:
            return {
                'gpu_percent': 0,
                'gpu_mem_percent': 0,
                'gpu_temp': 0,
            }

        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # Use first GPU
                return {
                    'gpu_percent': gpu.load * 100,
                    'gpu_mem_percent': gpu.memoryUtil * 100,
                    'gpu_temp': gpu.temperature,
                }
        except Exception as e:
            print(f"⚠️  GPU monitoring error: {e}")

        return {
            'gpu_percent': 0,
            'gpu_mem_percent': 0,
            'gpu_temp': 0,
        }

    def collect_sample(self) -> None:
        """
        Collect a single sample of all system metrics.
        """
        timestamp = datetime.datetime.now()
        self.timestamps.append(timestamp)

        # Collect all metrics
        cpu_info = self.get_cpu_info()
        mem_info = self.get_memory_info()
        disk_info = self.get_disk_info()
        net_info = self.get_network_info()
        gpu_info = self.get_gpu_info()

        # Store in data dictionary
        for key, value in {**cpu_info, **mem_info, **disk_info, **net_info, **gpu_info}.items():
            self.data[key].append(value)

    def get_dataframe(self) -> pd.DataFrame:
        """
        Convert collected data to a pandas DataFrame.

        Returns:
            DataFrame with all collected metrics
        """
        df = pd.DataFrame(self.data, index=self.timestamps)
        return df

    def get_summary_statistics(self) -> pd.DataFrame:
        """
        Calculate summary statistics for all metrics.

        Returns:
            DataFrame with average, max, and min values
        """
        df = self.get_dataframe()

        summary = pd.DataFrame({
            'Average': df.mean(),
            'Maximum': df.max(),
            'Minimum': df.min(),
            'Std Dev': df.std(),
        })

        return summary


class RealTimePlotter:
    """
    Handles real-time visualization of system metrics using matplotlib animation.
    """

    def __init__(self, monitor: SystemMonitor):
        """
        Initialize the real-time plotter.

        Args:
            monitor: SystemMonitor instance to visualize
        """
        self.monitor = monitor
        self.fig, self.axes = plt.subplots(3, 2, figsize=(14, 10))
        self.fig.suptitle('Real-Time System Resource Monitor', fontsize=16, fontweight='bold')

        # Flatten axes for easier indexing
        self.axes = self.axes.flatten()

        # Configure subplots
        self.plot_titles = [
            'CPU Usage (%)',
            'Memory Usage (%)',
            'Disk Usage (%)',
            'Network Traffic (MB/s)',
            'GPU Usage (%)',
            'Temperature (°C)'
        ]

        for ax, title in zip(self.axes, self.plot_titles):
            ax.set_title(title, fontweight='bold')
            ax.set_xlabel('Time')
            ax.set_ylabel('Value')
            ax.grid(True, alpha=0.3)

        # Initialize line objects
        self.lines = {}
        self.init_lines()

        plt.tight_layout()

    def init_lines(self) -> None:
        """
        Initialize line objects for each metric.
        """
        # CPU
        self.lines['cpu'], = self.axes[0].plot([], [], 'r-', label='CPU %', linewidth=2)
        self.axes[0].legend(loc='upper left')
        self.axes[0].set_ylim(0, 100)

        # Memory
        self.lines['mem'], = self.axes[1].plot([], [], 'b-', label='Memory %', linewidth=2)
        self.lines['swap'], = self.axes[1].plot([], [], 'c--', label='Swap %', linewidth=1.5)
        self.axes[1].legend(loc='upper left')
        self.axes[1].set_ylim(0, 100)

        # Disk
        self.lines['disk'], = self.axes[2].plot([], [], 'g-', label='Disk %', linewidth=2)
        self.axes[2].legend(loc='upper left')
        self.axes[2].set_ylim(0, 100)

        # Network
        self.lines['net_up'], = self.axes[3].plot([], [], 'orange', label='Upload', linewidth=2)
        self.lines['net_down'], = self.axes[3].plot([], [], 'purple', label='Download', linewidth=2)
        self.axes[3].legend(loc='upper left')

        # GPU
        self.lines['gpu'], = self.axes[4].plot([], [], 'm-', label='GPU %', linewidth=2)
        self.lines['gpu_mem'], = self.axes[4].plot([], [], 'y--', label='GPU Mem %', linewidth=1.5)
        self.axes[4].legend(loc='upper left')
        self.axes[4].set_ylim(0, 100)

        # Temperature
        self.lines['cpu_temp'], = self.axes[5].plot([], [], 'r-', label='CPU Temp', linewidth=2)
        self.lines['gpu_temp'], = self.axes[5].plot([], [], 'm-', label='GPU Temp', linewidth=2)
        self.axes[5].legend(loc='upper left')

    def update(self, frame: int) -> List:
        """
        Update function for animation. Called on each frame.

        Args:
            frame: Frame number

        Returns:
            List of updated line objects
        """
        if not self.monitor.timestamps:
            return list(self.lines.values())

        # Convert timestamps to elapsed seconds for x-axis
        elapsed = [(t - self.monitor.timestamps[0]).total_seconds()
                   for t in self.monitor.timestamps]

        # Update CPU
        if 'cpu_percent' in self.monitor.data:
            self.lines['cpu'].set_data(elapsed, self.monitor.data['cpu_percent'])
            self.axes[0].relim()
            self.axes[0].autoscale_view(scalex=True, scaley=False)

        # Update Memory
        if 'mem_percent' in self.monitor.data:
            self.lines['mem'].set_data(elapsed, self.monitor.data['mem_percent'])
            self.lines['swap'].set_data(elapsed, self.monitor.data['swap_percent'])
            self.axes[1].relim()
            self.axes[1].autoscale_view(scalex=True, scaley=False)

        # Update Disk
        if 'disk_percent' in self.monitor.data:
            self.lines['disk'].set_data(elapsed, self.monitor.data['disk_percent'])
            self.axes[2].relim()
            self.axes[2].autoscale_view(scalex=True, scaley=False)

        # Update Network
        if 'net_upload_mbps' in self.monitor.data:
            self.lines['net_up'].set_data(elapsed, self.monitor.data['net_upload_mbps'])
            self.lines['net_down'].set_data(elapsed, self.monitor.data['net_download_mbps'])
            self.axes[3].relim()
            self.axes[3].autoscale_view()

        # Update GPU
        if 'gpu_percent' in self.monitor.data:
            self.lines['gpu'].set_data(elapsed, self.monitor.data['gpu_percent'])
            self.lines['gpu_mem'].set_data(elapsed, self.monitor.data['gpu_mem_percent'])
            self.axes[4].relim()
            self.axes[4].autoscale_view(scalex=True, scaley=False)

        # Update Temperature
        if 'cpu_temp' in self.monitor.data:
            cpu_temps = self.monitor.data['cpu_temp']
            gpu_temps = self.monitor.data['gpu_temp']

            # Only plot non-zero values
            if any(t > 0 for t in cpu_temps):
                self.lines['cpu_temp'].set_data(elapsed, cpu_temps)
            if any(t > 0 for t in gpu_temps):
                self.lines['gpu_temp'].set_data(elapsed, gpu_temps)

            self.axes[5].relim()
            self.axes[5].autoscale_view()

        return list(self.lines.values())


class PDFReportGenerator:
    """
    Generates a comprehensive PDF report with all monitoring data and visualizations.
    """

    def __init__(self, monitor: SystemMonitor, output_path: str):
        """
        Initialize the PDF report generator.

        Args:
            monitor: SystemMonitor instance with collected data
            output_path: Path to save the PDF report
        """
        self.monitor = monitor
        self.output_path = output_path

    def generate_report(self) -> None:
        """
        Generate the complete PDF report with all sections.
        """
        print(f"\n📊 Generating PDF report: {self.output_path}")

        with PdfPages(self.output_path) as pdf:
            # Page 1: Title and Overview
            self._create_title_page(pdf)

            # Page 2: Summary Statistics
            self._create_summary_page(pdf)

            # Page 3-4: Detailed Charts
            self._create_cpu_memory_page(pdf)
            self._create_disk_network_page(pdf)
            self._create_gpu_temp_page(pdf)

            # Page 5: Observations
            self._create_observations_page(pdf)

            # Add metadata
            d = pdf.infodict()
            d['Title'] = 'System Resource Monitoring Report'
            d['Author'] = 'System Monitor'
            d['Subject'] = 'Real-time system resource tracking'
            d['CreationDate'] = datetime.datetime.now()

        print(f"✅ PDF report generated successfully!")

    def _create_title_page(self, pdf: PdfPages) -> None:
        """
        Create the title page with overview information.
        """
        fig = plt.figure(figsize=(8.5, 11))
        fig.text(0.5, 0.85, 'System Resource Monitoring Report',
                 ha='center', fontsize=24, fontweight='bold')

        # System information
        info_text = f"""
        Execution Date: {self.monitor.start_time.strftime('%Y-%m-%d %H:%M:%S')}
        Duration: {self.monitor.duration / 60:.1f} minutes ({self.monitor.duration} seconds)
        Samples Collected: {len(self.monitor.timestamps)}
        Sampling Interval: {self.monitor.interval} seconds

        System Information:
        • Platform: {platform.system()} {platform.release()}
        • Processor: {platform.processor() or platform.machine()}
        • Python Version: {platform.python_version()}
        • CPU Cores: {psutil.cpu_count(logical=False)} physical, {psutil.cpu_count(logical=True)} logical
        • Total Memory: {psutil.virtual_memory().total / (1024**3):.2f} GB
        • GPU Available: {'Yes' if GPU_AVAILABLE else 'No'}
        """

        fig.text(0.5, 0.45, info_text, ha='center', va='center',
                 fontsize=11, family='monospace',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

        plt.axis('off')
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def _create_summary_page(self, pdf: PdfPages) -> None:
        """
        Create the summary statistics page.
        """
        fig, ax = plt.subplots(figsize=(11, 8.5))
        fig.suptitle('Summary Statistics', fontsize=18, fontweight='bold', y=0.98)

        summary = self.monitor.get_summary_statistics()

        # Round values for better presentation
        summary_rounded = summary.round(2)

        # Create table
        ax.axis('tight')
        ax.axis('off')

        table_data = []
        table_data.append(['Metric', 'Average', 'Maximum', 'Minimum', 'Std Dev'])

        for idx, row in summary_rounded.iterrows():
            table_data.append([
                idx.replace('_', ' ').title(),
                f"{row['Average']:.2f}",
                f"{row['Maximum']:.2f}",
                f"{row['Minimum']:.2f}",
                f"{row['Std Dev']:.2f}"
            ])

        table = ax.table(cellText=table_data, cellLoc='left', loc='center',
                        colWidths=[0.3, 0.175, 0.175, 0.175, 0.175])

        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 2)

        # Style header row
        for i in range(5):
            table[(0, i)].set_facecolor('#4CAF50')
            table[(0, i)].set_text_props(weight='bold', color='white')

        # Alternate row colors
        for i in range(1, len(table_data)):
            for j in range(5):
                if i % 2 == 0:
                    table[(i, j)].set_facecolor('#f0f0f0')

        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def _create_cpu_memory_page(self, pdf: PdfPages) -> None:
        """
        Create CPU and memory usage charts.
        """
        df = self.monitor.get_dataframe()
        elapsed = [(t - self.monitor.timestamps[0]).total_seconds() / 60
                   for t in self.monitor.timestamps]

        fig, axes = plt.subplots(2, 1, figsize=(11, 8.5))
        fig.suptitle('CPU and Memory Usage Over Time', fontsize=16, fontweight='bold')

        # CPU Chart
        axes[0].plot(elapsed, df['cpu_percent'], 'r-', linewidth=2, label='CPU %')
        axes[0].axhline(y=df['cpu_percent'].mean(), color='r', linestyle='--',
                       alpha=0.7, label=f'Avg: {df["cpu_percent"].mean():.1f}%')
        axes[0].set_ylabel('CPU Usage (%)', fontsize=12)
        axes[0].set_ylim(0, 100)
        axes[0].grid(True, alpha=0.3)
        axes[0].legend(loc='upper right')
        axes[0].fill_between(elapsed, df['cpu_percent'], alpha=0.3, color='red')

        # Memory Chart
        axes[1].plot(elapsed, df['mem_percent'], 'b-', linewidth=2, label='Memory %')
        axes[1].plot(elapsed, df['swap_percent'], 'c--', linewidth=1.5, label='Swap %')
        axes[1].axhline(y=df['mem_percent'].mean(), color='b', linestyle='--',
                       alpha=0.7, label=f'Avg: {df["mem_percent"].mean():.1f}%')
        axes[1].set_xlabel('Time (minutes)', fontsize=12)
        axes[1].set_ylabel('Memory Usage (%)', fontsize=12)
        axes[1].set_ylim(0, 100)
        axes[1].grid(True, alpha=0.3)
        axes[1].legend(loc='upper right')
        axes[1].fill_between(elapsed, df['mem_percent'], alpha=0.3, color='blue')

        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def _create_disk_network_page(self, pdf: PdfPages) -> None:
        """
        Create disk and network usage charts.
        """
        df = self.monitor.get_dataframe()
        elapsed = [(t - self.monitor.timestamps[0]).total_seconds() / 60
                   for t in self.monitor.timestamps]

        fig, axes = plt.subplots(2, 1, figsize=(11, 8.5))
        fig.suptitle('Disk and Network Usage Over Time', fontsize=16, fontweight='bold')

        # Disk Chart
        axes[0].plot(elapsed, df['disk_percent'], 'g-', linewidth=2, label='Disk %')
        axes[0].axhline(y=df['disk_percent'].mean(), color='g', linestyle='--',
                       alpha=0.7, label=f'Avg: {df["disk_percent"].mean():.1f}%')
        axes[0].set_ylabel('Disk Usage (%)', fontsize=12)
        axes[0].set_ylim(0, 100)
        axes[0].grid(True, alpha=0.3)
        axes[0].legend(loc='upper right')
        axes[0].fill_between(elapsed, df['disk_percent'], alpha=0.3, color='green')

        # Network Chart
        axes[1].plot(elapsed, df['net_upload_mbps'], 'orange', linewidth=2, label='Upload (MB/s)')
        axes[1].plot(elapsed, df['net_download_mbps'], 'purple', linewidth=2, label='Download (MB/s)')
        axes[1].set_xlabel('Time (minutes)', fontsize=12)
        axes[1].set_ylabel('Network Rate (MB/s)', fontsize=12)
        axes[1].grid(True, alpha=0.3)
        axes[1].legend(loc='upper right')
        axes[1].fill_between(elapsed, df['net_upload_mbps'], alpha=0.2, color='orange')
        axes[1].fill_between(elapsed, df['net_download_mbps'], alpha=0.2, color='purple')

        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def _create_gpu_temp_page(self, pdf: PdfPages) -> None:
        """
        Create GPU and temperature charts.
        """
        df = self.monitor.get_dataframe()
        elapsed = [(t - self.monitor.timestamps[0]).total_seconds() / 60
                   for t in self.monitor.timestamps]

        fig, axes = plt.subplots(2, 1, figsize=(11, 8.5))
        fig.suptitle('GPU Usage and Temperature Over Time', fontsize=16, fontweight='bold')

        # GPU Chart
        axes[0].plot(elapsed, df['gpu_percent'], 'm-', linewidth=2, label='GPU %')
        axes[0].plot(elapsed, df['gpu_mem_percent'], 'y--', linewidth=1.5, label='GPU Memory %')
        if df['gpu_percent'].max() > 0:
            axes[0].axhline(y=df['gpu_percent'].mean(), color='m', linestyle='--',
                           alpha=0.7, label=f'Avg GPU: {df["gpu_percent"].mean():.1f}%')
        axes[0].set_ylabel('GPU Usage (%)', fontsize=12)
        axes[0].set_ylim(0, 100)
        axes[0].grid(True, alpha=0.3)
        axes[0].legend(loc='upper right')
        axes[0].fill_between(elapsed, df['gpu_percent'], alpha=0.3, color='magenta')

        if df['gpu_percent'].max() == 0:
            axes[0].text(0.5, 0.5, 'GPU monitoring not available',
                        ha='center', va='center', transform=axes[0].transAxes,
                        fontsize=14, color='gray')

        # Temperature Chart
        has_temp_data = False
        if df['cpu_temp'].max() > 0:
            axes[1].plot(elapsed, df['cpu_temp'], 'r-', linewidth=2, label='CPU Temp (°C)')
            has_temp_data = True
        if df['gpu_temp'].max() > 0:
            axes[1].plot(elapsed, df['gpu_temp'], 'm-', linewidth=2, label='GPU Temp (°C)')
            has_temp_data = True

        axes[1].set_xlabel('Time (minutes)', fontsize=12)
        axes[1].set_ylabel('Temperature (°C)', fontsize=12)
        axes[1].grid(True, alpha=0.3)
        axes[1].legend(loc='upper right')

        if not has_temp_data:
            axes[1].text(0.5, 0.5, 'Temperature monitoring not available',
                        ha='center', va='center', transform=axes[1].transAxes,
                        fontsize=14, color='gray')

        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    def _create_observations_page(self, pdf: PdfPages) -> None:
        """
        Create observations and automated summary page.
        """
        df = self.monitor.get_dataframe()
        summary = self.monitor.get_summary_statistics()

        fig = plt.figure(figsize=(8.5, 11))
        fig.text(0.5, 0.95, 'Automated Observations',
                 ha='center', fontsize=18, fontweight='bold')

        observations = []

        # CPU observations
        cpu_avg = summary.loc['cpu_percent', 'Average']
        cpu_max = summary.loc['cpu_percent', 'Maximum']
        if cpu_avg > 80:
            observations.append(f"⚠️  HIGH CPU USAGE: Average {cpu_avg:.1f}%, Peak {cpu_max:.1f}%")
        elif cpu_avg > 50:
            observations.append(f"📊 MODERATE CPU USAGE: Average {cpu_avg:.1f}%, Peak {cpu_max:.1f}%")
        else:
            observations.append(f"✅ LOW CPU USAGE: Average {cpu_avg:.1f}%, Peak {cpu_max:.1f}%")

        # Memory observations
        mem_avg = summary.loc['mem_percent', 'Average']
        mem_max = summary.loc['mem_percent', 'Maximum']
        if mem_avg > 80:
            observations.append(f"⚠️  HIGH MEMORY USAGE: Average {mem_avg:.1f}%, Peak {mem_max:.1f}%")
        elif mem_avg > 50:
            observations.append(f"📊 MODERATE MEMORY USAGE: Average {mem_avg:.1f}%, Peak {mem_max:.1f}%")
        else:
            observations.append(f"✅ LOW MEMORY USAGE: Average {mem_avg:.1f}%, Peak {mem_max:.1f}%")

        # Disk observations
        disk_avg = summary.loc['disk_percent', 'Average']
        if disk_avg > 90:
            observations.append(f"⚠️  DISK SPACE CRITICAL: {disk_avg:.1f}% used on average")
        elif disk_avg > 75:
            observations.append(f"📊 DISK SPACE WARNING: {disk_avg:.1f}% used on average")
        else:
            observations.append(f"✅ DISK SPACE HEALTHY: {disk_avg:.1f}% used on average")

        # Network observations
        net_up_avg = summary.loc['net_upload_mbps', 'Average']
        net_down_avg = summary.loc['net_download_mbps', 'Average']
        net_up_max = summary.loc['net_upload_mbps', 'Maximum']
        net_down_max = summary.loc['net_download_mbps', 'Maximum']

        observations.append(f"🌐 NETWORK ACTIVITY:")
        observations.append(f"   • Upload: Avg {net_up_avg:.3f} MB/s, Peak {net_up_max:.3f} MB/s")
        observations.append(f"   • Download: Avg {net_down_avg:.3f} MB/s, Peak {net_down_max:.3f} MB/s")

        # GPU observations
        gpu_avg = summary.loc['gpu_percent', 'Average']
        gpu_max = summary.loc['gpu_percent', 'Maximum']
        if gpu_max > 0:
            if gpu_avg > 80:
                observations.append(f"🎮 HIGH GPU USAGE: Average {gpu_avg:.1f}%, Peak {gpu_max:.1f}%")
            else:
                observations.append(f"🎮 GPU USAGE: Average {gpu_avg:.1f}%, Peak {gpu_max:.1f}%")
        else:
            observations.append("🎮 GPU monitoring not available or no GPU detected")

        # Temperature observations
        cpu_temp_max = summary.loc['cpu_temp', 'Maximum']
        gpu_temp_max = summary.loc['gpu_temp', 'Maximum']

        if cpu_temp_max > 0:
            if cpu_temp_max > 80:
                observations.append(f"🌡️  HIGH CPU TEMPERATURE: Peak {cpu_temp_max:.1f}°C")
            else:
                observations.append(f"🌡️  CPU TEMPERATURE: Peak {cpu_temp_max:.1f}°C")

        if gpu_temp_max > 0:
            if gpu_temp_max > 80:
                observations.append(f"🌡️  HIGH GPU TEMPERATURE: Peak {gpu_temp_max:.1f}°C")
            else:
                observations.append(f"🌡️  GPU TEMPERATURE: Peak {gpu_temp_max:.1f}°C")

        # Stability analysis
        cpu_std = summary.loc['cpu_percent', 'Std Dev']
        if cpu_std < 10:
            observations.append(f"📈 CPU load was STABLE (std dev: {cpu_std:.2f})")
        else:
            observations.append(f"📈 CPU load was VARIABLE (std dev: {cpu_std:.2f})")

        observations_text = '\n\n'.join(observations)

        fig.text(0.1, 0.75, observations_text,
                 ha='left', va='top', fontsize=10, family='monospace',
                 bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

        # Add recommendation section
        recommendations = [
            "💡 RECOMMENDATIONS:",
            "",
        ]

        if cpu_avg > 80:
            recommendations.append("• Consider upgrading CPU or optimizing processes")
        if mem_avg > 80:
            recommendations.append("• Consider adding more RAM or closing unused applications")
        if disk_avg > 90:
            recommendations.append("• Free up disk space immediately")
        if cpu_temp_max > 80:
            recommendations.append("• Check CPU cooling system")

        if len(recommendations) == 2:
            recommendations.append("• System resources are operating within normal parameters")

        rec_text = '\n'.join(recommendations)
        fig.text(0.1, 0.25, rec_text,
                 ha='left', va='top', fontsize=10, family='monospace',
                 bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))

        plt.axis('off')
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()


def run_monitoring(duration: int, interval: float, output_path: str) -> None:
    """
    Main function to run the monitoring process.

    Args:
        duration: Total monitoring duration in seconds
        interval: Sampling interval in seconds
        output_path: Path to save the PDF report
    """
    print("=" * 80)
    print("🖥️  SYSTEM RESOURCE MONITORING APPLICATION")
    print("=" * 80)
    print(f"⏱️  Duration: {duration} seconds ({duration/60:.1f} minutes)")
    print(f"📊 Sampling interval: {interval} seconds")
    print(f"📄 Output: {output_path}")
    print(f"💻 Platform: {platform.system()} {platform.release()}")
    print(f"🔧 Python: {platform.python_version()}")
    print(f"🎮 GPU monitoring: {'Enabled' if GPU_AVAILABLE else 'Disabled'}")
    print("=" * 80)
    print("\n🚀 Starting monitoring...\n")

    # Initialize monitor
    monitor = SystemMonitor(duration_seconds=duration, interval_seconds=interval)
    monitor.start_time = datetime.datetime.now()

    # Initialize plotter
    plotter = RealTimePlotter(monitor)

    # Collection state
    collection_complete = False
    samples_collected = 0
    total_samples = int(duration / interval)

    def collect_data(frame):
        """Data collection function for animation."""
        nonlocal collection_complete, samples_collected

        if collection_complete:
            return

        elapsed = time.time() - start_time

        if elapsed >= duration:
            collection_complete = True
            print(f"\n✅ Monitoring complete! Collected {samples_collected} samples.")
            return

        # Collect sample
        monitor.collect_sample()
        samples_collected += 1

        # Progress indicator
        progress = (elapsed / duration) * 100
        print(f"\r⏳ Progress: {progress:.1f}% | Samples: {samples_collected}/{total_samples} | "
              f"Time: {elapsed:.0f}/{duration}s", end='', flush=True)

    # Start collection
    start_time = time.time()

    # Create animation
    anim = animation.FuncAnimation(
        plotter.fig,
        lambda frame: [collect_data(frame)] + plotter.update(frame),
        interval=interval * 1000,  # Convert to milliseconds
        blit=False,
        cache_frame_data=False
    )

    try:
        plt.show()
    except KeyboardInterrupt:
        print("\n\n⚠️  Monitoring interrupted by user.")

    # Ensure we have some data
    if samples_collected == 0:
        print("\n❌ No data collected. Exiting.")
        return

    print("\n\n" + "=" * 80)
    print("📊 MONITORING SUMMARY")
    print("=" * 80)

    # Display summary statistics
    summary = monitor.get_summary_statistics()
    print("\n📈 Key Metrics:")
    print(f"  CPU Usage:    Avg {summary.loc['cpu_percent', 'Average']:.1f}% | "
          f"Max {summary.loc['cpu_percent', 'Maximum']:.1f}%")
    print(f"  Memory Usage: Avg {summary.loc['mem_percent', 'Average']:.1f}% | "
          f"Max {summary.loc['mem_percent', 'Maximum']:.1f}%")
    print(f"  Disk Usage:   Avg {summary.loc['disk_percent', 'Average']:.1f}% | "
          f"Max {summary.loc['disk_percent', 'Maximum']:.1f}%")
    print(f"  Network Up:   Avg {summary.loc['net_upload_mbps', 'Average']:.3f} MB/s | "
          f"Max {summary.loc['net_upload_mbps', 'Maximum']:.3f} MB/s")
    print(f"  Network Down: Avg {summary.loc['net_download_mbps', 'Average']:.3f} MB/s | "
          f"Max {summary.loc['net_download_mbps', 'Maximum']:.3f} MB/s")

    if GPU_AVAILABLE and summary.loc['gpu_percent', 'Maximum'] > 0:
        print(f"  GPU Usage:    Avg {summary.loc['gpu_percent', 'Average']:.1f}% | "
              f"Max {summary.loc['gpu_percent', 'Maximum']:.1f}%")

    print("\n" + "=" * 80)

    # Generate PDF report
    pdf_generator = PDFReportGenerator(monitor, output_path)
    pdf_generator.generate_report()

    print("\n" + "=" * 80)
    print("✅ MONITORING COMPLETE")
    print("=" * 80)
    print(f"📄 Report saved to: {os.path.abspath(output_path)}")
    print(f"📊 Total samples collected: {samples_collected}")
    print(f"⏱️  Total duration: {duration} seconds")
    print("=" * 80)


def main():
    """
    Main entry point for the application.
    Parses CLI arguments and starts monitoring.
    """
    parser = argparse.ArgumentParser(
        description='Real-time System Resource Monitoring Application',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor for 5 minutes (default)
  python system_monitor.py

  # Monitor for 2 minutes with custom output
  python system_monitor.py --duration 120 --output my_report.pdf

  # Monitor for 10 seconds (testing)
  python system_monitor.py --duration 10 --interval 0.5
        """
    )

    parser.add_argument(
        '-d', '--duration',
        type=int,
        default=300,
        help='Monitoring duration in seconds (default: 300 = 5 minutes)'
    )

    parser.add_argument(
        '-i', '--interval',
        type=float,
        default=1.0,
        help='Sampling interval in seconds (default: 1.0)'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        default='system_monitor_report.pdf',
        help='Output PDF file path (default: system_monitor_report.pdf)'
    )

    args = parser.parse_args()

    # Validate arguments
    if args.duration <= 0:
        print("❌ Error: Duration must be positive.")
        return

    if args.interval <= 0 or args.interval > args.duration:
        print("❌ Error: Interval must be positive and less than duration.")
        return

    # Run monitoring
    try:
        run_monitoring(args.duration, args.interval, args.output)
    except KeyboardInterrupt:
        print("\n\n⚠️  Application terminated by user.")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
