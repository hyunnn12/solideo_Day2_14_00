# 🔍 System Monitor 코드 리뷰 보고서

**작성일**: 2025-11-06
**대상 파일**: `system_monitor.py` (967 lines)
**리뷰 유형**: 보안 취약점 및 코드 품질 분석

---

## 📋 목차

1. [요약](#요약)
2. [보안 취약점](#보안-취약점)
3. [코드 품질 문제](#코드-품질-문제)
4. [성능 및 리소스 관리](#성능-및-리소스-관리)
5. [Best Practices 위반](#best-practices-위반)
6. [긍정적인 측면](#긍정적인-측면)
7. [우선순위별 권장사항](#우선순위별-권장사항)

---

## 🎯 요약

### 전체 평가

| 항목 | 점수 | 상태 |
|------|------|------|
| **보안** | ⚠️ 5/10 | 중간 위험 |
| **코드 품질** | 7/10 | 양호 |
| **성능** | 6/10 | 개선 필요 |
| **유지보수성** | 8/10 | 우수 |
| **전체** | 6.5/10 | 개선 권장 |

### 핵심 발견사항

- 🔴 **심각**: 1개 (Path Traversal 취약점)
- 🟠 **높음**: 3개 (입력 검증, DoS, 정보 노출)
- 🟡 **중간**: 5개 (예외 처리, 리소스 관리)
- 🟢 **낮음**: 4개 (코드 스타일, 최적화)

---

## 🚨 보안 취약점

### 1. 🔴 **[CRITICAL] Path Traversal 취약점** (Line 930-935, 748)

**위치**: `main()` 함수의 `--output` 인자 처리

```python
parser.add_argument(
    '-o', '--output',
    type=str,
    default='system_monitor_report.pdf',
    help='Output PDF file path (default: system_monitor_report.pdf)'
)
```

**문제점**:
- 사용자 입력 파일 경로를 **검증 없이** 그대로 사용
- Path Traversal 공격 가능: `../../etc/passwd`, `/tmp/malicious.pdf`
- 임의의 시스템 경로에 파일 쓰기 가능

**공격 시나리오**:
```bash
# 시스템 중요 디렉토리에 파일 작성
python system_monitor.py -o /etc/cron.d/backdoor --no-gui -d 1

# 상위 디렉토리 탐색
python system_monitor.py -o ../../../tmp/exploit.pdf --no-gui -d 1

# 심볼릭 링크를 통한 파일 덮어쓰기
ln -s /etc/important_file malicious.pdf
python system_monitor.py -o malicious.pdf --no-gui -d 1
```

**영향**:
- ⚠️ 시스템 파일 덮어쓰기
- ⚠️ 권한 상승 가능성
- ⚠️ 데이터 손실

**CWE**: CWE-22 (Improper Limitation of a Pathname to a Restricted Directory)

**권장 해결책**:
```python
import os
from pathlib import Path

def validate_output_path(filepath: str) -> str:
    """Validate and sanitize output file path."""
    # 1. 절대 경로 금지
    if os.path.isabs(filepath):
        raise ValueError("Absolute paths are not allowed")

    # 2. Path traversal 방지
    if '..' in filepath or filepath.startswith('/'):
        raise ValueError("Path traversal detected")

    # 3. 허용된 디렉토리로 제한
    base_dir = Path.cwd()
    full_path = (base_dir / filepath).resolve()

    # 4. 경로가 base_dir 내부인지 확인
    if not str(full_path).startswith(str(base_dir)):
        raise ValueError("Path must be within current directory")

    # 5. 파일 확장자 검증
    if not full_path.suffix.lower() == '.pdf':
        raise ValueError("Only .pdf files are allowed")

    return str(full_path)
```

---

### 2. 🟠 **[HIGH] 입력 검증 부족** (Line 946-952)

**위치**: 인자 검증 로직

```python
if args.duration <= 0:
    print("❌ Error: Duration must be positive.")
    return

if args.interval <= 0 or args.interval > args.duration:
    print("❌ Error: Interval must be positive and less than duration.")
    return
```

**문제점**:
1. **상한값 검증 없음**
   - `duration`에 `sys.maxsize` 같은 극단적 값 가능
   - DoS 공격 가능: `--duration 999999999`

2. **부동소수점 검증 미흡**
   - `interval`에 0.0001 같은 값 허용
   - CPU 폭주 가능

3. **타입 검증 의존**
   - argparse의 type 변환에만 의존
   - 예외적인 값 처리 부족

**공격 시나리오**:
```bash
# DoS: 극도로 긴 모니터링
python system_monitor.py -d 2147483647 --no-gui

# DoS: 극도로 짧은 interval
python system_monitor.py -d 60 -i 0.0001 --no-gui

# 메모리 고갈
python system_monitor.py -d 86400 -i 0.1 --no-gui  # 864,000개 샘플
```

**영향**:
- ⚠️ DoS (Denial of Service)
- ⚠️ 메모리 고갈
- ⚠️ CPU 리소스 독점

**권장 해결책**:
```python
# 상수 정의
MAX_DURATION = 3600  # 1시간
MIN_DURATION = 1
MAX_INTERVAL = 60
MIN_INTERVAL = 0.1
MAX_SAMPLES = 100000  # 최대 샘플 수

# 검증 로직
if not MIN_DURATION <= args.duration <= MAX_DURATION:
    print(f"❌ Error: Duration must be between {MIN_DURATION} and {MAX_DURATION} seconds.")
    return

if not MIN_INTERVAL <= args.interval <= MAX_INTERVAL:
    print(f"❌ Error: Interval must be between {MIN_INTERVAL} and {MAX_INTERVAL} seconds.")
    return

estimated_samples = args.duration / args.interval
if estimated_samples > MAX_SAMPLES:
    print(f"❌ Error: Too many samples ({estimated_samples:.0f}). Maximum is {MAX_SAMPLES}.")
    return
```

---

### 3. 🟠 **[HIGH] 예외 처리의 광범위한 catch** (Line 169-179, 959-962)

**위치 1**: GPU 정보 수집
```python
try:
    gpus = GPUtil.getGPUs()
    if gpus:
        gpu = gpus[0]
        return {...}
except Exception as e:  # ← 너무 광범위
    print(f"⚠️  GPU monitoring error: {e}")
```

**위치 2**: 메인 함수
```python
except Exception as e:  # ← 너무 광범위
    print(f"\n\n❌ Error occurred: {e}")
    import traceback
    traceback.print_exc()
```

**문제점**:
1. **모든 예외를 캐치**
   - 심각한 에러(메모리 부족, 권한 오류)도 숨김
   - 디버깅 어려움
   - 보안 문제 은폐 가능

2. **정보 노출**
   - traceback 전체 출력 → 경로, 버전 정보 노출
   - 공격자에게 시스템 정보 제공

3. **적절한 복구 전략 없음**
   - 예외 발생 시 계속 실행할지 중단할지 불명확

**보안 영향**:
- 🔍 정보 노출 (CWE-209)
- 🐛 에러 마스킹으로 인한 취약점 은폐

**권장 해결책**:
```python
# 구체적인 예외 타입 지정
try:
    gpus = GPUtil.getGPUs()
    if gpus:
        gpu = gpus[0]
        return {...}
except (AttributeError, ImportError, RuntimeError) as e:
    logging.warning(f"GPU monitoring unavailable: {type(e).__name__}")
    return default_gpu_info()
except Exception as e:
    logging.error(f"Unexpected GPU error: {type(e).__name__}")
    raise  # 예상치 못한 에러는 전파

# 메인 함수 - 프로덕션 모드에서는 상세 정보 숨김
except KeyboardInterrupt:
    print("\n⚠️  Application terminated by user.")
except (OSError, IOError) as e:
    print(f"❌ I/O Error: {e}")
    sys.exit(1)
except Exception as e:
    if DEBUG_MODE:  # 환경 변수로 제어
        traceback.print_exc()
    else:
        print(f"❌ An error occurred. Check logs for details.")
        logging.error(f"Fatal error: {e}", exc_info=True)
    sys.exit(1)
```

---

### 4. 🟠 **[HIGH] 정보 노출** (Line 428-446, 959-962)

**위치**: PDF 리포트 및 에러 출력

```python
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
```

**문제점**:
1. **시스템 상세 정보 노출**
   - OS 버전 → 알려진 취약점 활용 가능
   - Python 버전 → 라이브러리 취약점 식별
   - 하드웨어 정보 → 시스템 프로파일링

2. **에러 메시지에서 전체 traceback 노출**
   - 파일 경로 노출
   - 내부 구조 노출

**영향**:
- 🔍 정보 수집 (Information Gathering)
- 🎯 공격 벡터 식별 용이

**권장 해결책**:
```python
def get_safe_system_info() -> dict:
    """Get system info with sensitive data redacted."""
    return {
        'platform': platform.system(),  # Windows/Linux/Darwin만
        'python_version': '.'.join(platform.python_version().split('.')[:2]),  # 3.11만
        'cpu_cores': psutil.cpu_count(logical=True),
        'memory_gb': round(psutil.virtual_memory().total / (1024**3))
    }

# PDF에 포함할 정보 최소화
info_text = f"""
    Report Date: {self.monitor.start_time.strftime('%Y-%m-%d')}
    Monitoring Duration: {self.monitor.duration / 60:.1f} minutes
    Samples: {len(self.monitor.timestamps)}

    System: {safe_info['platform']}
    Resources: {safe_info['cpu_cores']} CPUs, {safe_info['memory_gb']} GB RAM
    """
```

---

### 5. 🟡 **[MEDIUM] Race Condition 가능성** (Line 57-59, 132-146)

**위치**: 네트워크 통계 업데이트

```python
# __init__
self.last_net_io = psutil.net_io_counters()
self.last_net_time = time.time()

# get_network_info
current_net_io = psutil.net_io_counters()
current_time = time.time()

time_delta = current_time - self.last_net_time
bytes_sent_delta = current_net_io.bytes_sent - self.last_net_io.bytes_sent

self.last_net_io = current_net_io  # ← Race condition
self.last_net_time = current_time
```

**문제점**:
- 멀티스레드 환경에서 `last_net_io`와 `last_net_time` 업데이트가 atomic하지 않음
- GUI 모드에서는 문제 없지만, 향후 확장 시 문제 발생 가능

**영향**:
- ⚠️ 부정확한 통계
- ⚠️ 음수 값 발생 가능

**권장 해결책**:
```python
from threading import Lock

class SystemMonitor:
    def __init__(self, ...):
        self._net_lock = Lock()
        ...

    def get_network_info(self) -> Dict[str, float]:
        with self._net_lock:
            current_net_io = psutil.net_io_counters()
            current_time = time.time()

            time_delta = current_time - self.last_net_time
            bytes_sent_delta = current_net_io.bytes_sent - self.last_net_io.bytes_sent

            # atomic update
            self.last_net_io = current_net_io
            self.last_net_time = current_time

            return {...}
```

---

### 6. 🟡 **[MEDIUM] 하드코딩된 디스크 경로** (Line 114)

**위치**: `get_disk_info()`

```python
disk = psutil.disk_usage('/')  # ← 루트 디렉토리만 모니터링
```

**문제점**:
1. **Windows에서 실패**
   - Windows는 드라이브 레터 사용 (C:, D:)
   - `/` 경로가 유효하지 않음

2. **제한된 모니터링**
   - 마운트된 다른 디스크 무시
   - 사용자 데이터 디스크 누락 가능

**영향**:
- ⚠️ 크로스 플랫폼 호환성 문제
- ⚠️ 부정확한 디스크 정보

**권장 해결책**:
```python
def get_disk_info(self) -> Dict[str, float]:
    """Get disk usage for the current working directory."""
    try:
        # 현재 작업 디렉토리의 디스크 사용량
        disk = psutil.disk_usage(os.getcwd())
    except (PermissionError, FileNotFoundError):
        # 폴백: 홈 디렉토리
        disk = psutil.disk_usage(os.path.expanduser('~'))

    disk_io = psutil.disk_io_counters()

    return {
        'disk_percent': disk.percent,
        'disk_used_gb': disk.used / (1024 ** 3),
        'disk_total_gb': disk.total / (1024 ** 3),
        'disk_read_mb': disk_io.read_bytes / (1024 ** 2) if disk_io else 0,
        'disk_write_mb': disk_io.write_bytes / (1024 ** 2) if disk_io else 0,
    }
```

---

### 7. 🟡 **[MEDIUM] 리소스 정리 부족** (Line 400, 810, 840)

**위치**: PDF 생성 및 matplotlib 객체

```python
with PdfPages(self.output_path) as pdf:  # ✓ Context manager 사용
    ...

# 하지만 matplotlib 객체는?
plotter = RealTimePlotter(monitor)  # ← 명시적 정리 없음
anim = animation.FuncAnimation(...)  # ← 참조 유지 필요하나 정리 없음
```

**문제점**:
1. **메모리 누수 가능성**
   - matplotlib figure 객체가 제대로 해제되지 않을 수 있음
   - 긴 시간 실행 시 메모리 증가

2. **에러 발생 시 리소스 누수**
   - 예외 발생 시 figure가 닫히지 않을 수 있음

**권장 해결책**:
```python
def run_monitoring(...):
    monitor = SystemMonitor(...)
    plotter = None

    try:
        if no_gui:
            # headless mode
            ...
        else:
            plotter = RealTimePlotter(monitor)
            anim = animation.FuncAnimation(...)
            try:
                plt.show()
            finally:
                plt.close('all')  # 모든 figure 정리
    finally:
        if plotter is not None:
            plt.close(plotter.fig)

        # 메모리 명시적 정리
        if hasattr(monitor, 'data'):
            monitor.data.clear()
```

---

## 💻 코드 품질 문제

### 8. 🟡 **[MEDIUM] 전역 상태 사용** (Line 28-34)

```python
try:
    import GPUtil
    GPU_AVAILABLE = True  # ← 전역 변수
except ImportError:
    GPU_AVAILABLE = False
    print("⚠️  GPUtil not available. GPU monitoring will be skipped.")
```

**문제점**:
- 전역 변수 사용
- 테스트 어려움
- 모듈 import 시 부작용 (print 실행)

**권장 개선**:
```python
class GPUMonitor:
    _gpu_available = None

    @classmethod
    def is_available(cls) -> bool:
        if cls._gpu_available is None:
            try:
                import GPUtil
                cls._gpu_available = True
            except ImportError:
                cls._gpu_available = False
        return cls._gpu_available
```

---

### 9. 🟡 **[MEDIUM] 하드코딩된 임계값** (Line 644-712)

```python
if cpu_avg > 80:  # ← 하드코딩
    observations.append(...)
elif cpu_avg > 50:
    observations.append(...)
```

**문제점**:
- 임계값이 코드에 박혀있음
- 시스템마다 다른 임계값이 필요할 수 있음
- 설정 변경 시 코드 수정 필요

**권장 개선**:
```python
class AlertThresholds:
    CPU_HIGH = 80
    CPU_MODERATE = 50
    MEMORY_HIGH = 80
    MEMORY_MODERATE = 50
    DISK_CRITICAL = 90
    DISK_WARNING = 75
    TEMP_HIGH = 80

# 또는 설정 파일 사용
import json
with open('thresholds.json') as f:
    THRESHOLDS = json.load(f)
```

---

### 10. 🟢 **[LOW] 매직 넘버** (Line 68, 800, 843)

```python
cpu_percent = psutil.cpu_percent(interval=0.1)  # ← 0.1은 왜?
time.sleep(interval)
interval=interval * 1000,  # ← 1000은 왜?
```

**문제점**:
- 의미 없는 숫자들
- 코드 가독성 저하

**권장 개선**:
```python
CPU_SAMPLE_INTERVAL = 0.1  # seconds
MILLISECONDS_PER_SECOND = 1000

cpu_percent = psutil.cpu_percent(interval=CPU_SAMPLE_INTERVAL)
animation_interval_ms = interval * MILLISECONDS_PER_SECOND
```

---

### 11. 🟢 **[LOW] 긴 함수** (Line 628-745)

**위치**: `_create_observations_page()` - 117 lines

**문제점**:
- 단일 함수가 너무 김
- 여러 책임 수행
- 테스트 어려움

**권장 개선**:
```python
def _create_observations_page(self, pdf: PdfPages) -> None:
    observations = self._generate_observations()
    recommendations = self._generate_recommendations()

    fig = self._create_observation_figure(observations, recommendations)
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()

def _generate_observations(self) -> List[str]:
    """Generate system observations from collected data."""
    ...

def _generate_recommendations(self) -> List[str]:
    """Generate recommendations based on observations."""
    ...
```

---

## ⚡ 성능 및 리소스 관리

### 12. 🟡 **[MEDIUM] 메모리 효율성** (Line 54, 202-203)

```python
self.data = defaultdict(list)  # ← 모든 샘플을 메모리에 저장
self.timestamps = []

# 5분, 1초 간격 = 300개 샘플
# 각 샘플 ~15개 메트릭 = 4500개 float
# 1시간 모니터링 = 54,000개 float = ~432KB (괜찮음)
# 24시간 = ~10MB (아직 괜찮음)
```

**문제점**:
- 긴 모니터링 시 메모리 증가
- streaming 처리 없음

**영향**: 현재는 문제 없으나, 확장성 제한

**권장 개선**:
```python
# Option 1: 원형 버퍼 사용
from collections import deque

class SystemMonitor:
    def __init__(self, ..., max_samples=10000):
        self.max_samples = max_samples
        self.data = defaultdict(lambda: deque(maxlen=max_samples))
        self.timestamps = deque(maxlen=max_samples)

# Option 2: SQLite에 저장
import sqlite3

class SystemMonitor:
    def __init__(self, ..., db_path=':memory:'):
        self.conn = sqlite3.connect(db_path)
        self._create_table()

    def collect_sample(self):
        # DB에 직접 저장
        self.conn.execute("INSERT INTO samples VALUES (?, ?, ...)", ...)
```

---

### 13. 🟢 **[LOW] 불필요한 계산** (Line 510-511, 547-548, 582-583)

```python
elapsed = [(t - self.monitor.timestamps[0]).total_seconds() / 60
           for t in self.monitor.timestamps]
# ← PDF 생성 시 3번 반복 계산
```

**문제점**:
- 동일한 계산을 여러 번 수행
- 리스트 컴프리헨션이 매번 실행됨

**권장 개선**:
```python
def generate_report(self) -> None:
    # 한 번만 계산
    elapsed_minutes = self._calculate_elapsed_minutes()

    with PdfPages(self.output_path) as pdf:
        self._create_cpu_memory_page(pdf, elapsed_minutes)
        self._create_disk_network_page(pdf, elapsed_minutes)
        self._create_gpu_temp_page(pdf, elapsed_minutes)

def _calculate_elapsed_minutes(self) -> List[float]:
    if not self.monitor.timestamps:
        return []
    base_time = self.monitor.timestamps[0]
    return [(t - base_time).total_seconds() / 60
            for t in self.monitor.timestamps]
```

---

## ✅ Best Practices 위반

### 14. 🟢 **[LOW] Logging 대신 print 사용** (전체)

```python
print("⚠️  GPUtil not available...")  # Line 34
print(f"⚠️  GPU monitoring error: {e}")  # Line 179
print(f"\n📊 Generating PDF report: {self.output_path}")  # Line 398
```

**문제점**:
- stdout/stderr 구분 없음
- 로그 레벨 제어 불가
- 파일 저장 불가
- 프로덕션 환경에 부적합

**권장 개선**:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('system_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 사용
logger.warning("GPUtil not available. GPU monitoring will be skipped.")
logger.info(f"Generating PDF report: {self.output_path}")
logger.error(f"GPU monitoring error: {e}")
```

---

### 15. 🟢 **[LOW] 타입 힌트 불완전** (일부 함수)

```python
def collect_sample(self) -> None:  # ✓ 좋음
    ...

def update(self, frame: int) -> List:  # ⚠️ List[?] 불명확
    ...

def collect_data(frame):  # ❌ 타입 힌트 없음
    ...
```

**권장 개선**:
```python
from typing import List, Any
from matplotlib.lines import Line2D

def update(self, frame: int) -> List[Line2D]:
    ...

def collect_data(frame: int) -> None:
    ...
```

---

### 16. 🟢 **[LOW] 문서화 부족**

```python
def init_lines(self) -> None:
    """
    Initialize line objects for each metric.
    """
    # 구현만 있고 파라미터, 반환값 설명 없음
```

**권장 개선**:
```python
def init_lines(self) -> None:
    """
    Initialize matplotlib line objects for real-time plotting.

    Creates line objects for CPU, memory, disk, network, GPU metrics
    and temperature sensors. Each line is configured with appropriate
    colors, styles, and labels.

    Modifies:
        self.lines: Dictionary mapping metric names to Line2D objects
        self.axes: Configures plot limits and legends

    Note:
        Should be called only once during plotter initialization.
    """
```

---

## 🌟 긍정적인 측면

### ✅ 잘된 점들

1. **구조화된 클래스 설계**
   - `SystemMonitor`, `RealTimePlotter`, `PDFReportGenerator` 명확한 분리
   - 단일 책임 원칙 준수

2. **Context Manager 사용**
   ```python
   with PdfPages(self.output_path) as pdf:  # 리소스 자동 정리
   ```

3. **Graceful Degradation**
   - GPU 없어도 동작
   - 온도 센서 없어도 동작
   - 유연한 에러 처리

4. **타입 힌트 사용**
   - 대부분의 함수에 타입 힌트 존재
   - 코드 가독성 향상

5. **Docstring 작성**
   - 모든 클래스와 주요 메서드에 문서화
   - Args, Returns 명시

6. **설정 가능한 파라미터**
   - CLI 인자로 duration, interval, output 제어
   - 유연한 사용

7. **크로스 플랫폼 고려**
   - platform 모듈 사용
   - psutil로 추상화

---

## 📊 우선순위별 권장사항

### 🔴 **즉시 수정 필요** (Critical)

| # | 문제 | 위험도 | 영향 | 예상 작업 |
|---|------|--------|------|----------|
| 1 | Path Traversal | CRITICAL | 시스템 파일 덮어쓰기 | 2시간 |

**수정 순서**:
1. `validate_output_path()` 함수 추가
2. `main()` 함수에서 검증 적용
3. 단위 테스트 작성

---

### 🟠 **빠른 시일 내 수정** (High Priority)

| # | 문제 | 위험도 | 영향 | 예상 작업 |
|---|------|--------|------|----------|
| 2 | 입력 검증 부족 | HIGH | DoS 공격 | 1시간 |
| 3 | 광범위한 예외 처리 | HIGH | 보안 문제 은폐 | 2시간 |
| 4 | 정보 노출 | HIGH | 공격 벡터 식별 | 1시간 |

---

### 🟡 **계획하여 수정** (Medium Priority)

| # | 문제 | 위험도 | 영향 | 예상 작업 |
|---|------|--------|------|----------|
| 5 | Race Condition | MEDIUM | 통계 부정확 | 1시간 |
| 6 | 하드코딩된 경로 | MEDIUM | 호환성 문제 | 30분 |
| 7 | 리소스 정리 부족 | MEDIUM | 메모리 누수 | 1시간 |
| 8 | 전역 상태 | MEDIUM | 테스트 어려움 | 1시간 |
| 9 | 하드코딩된 임계값 | MEDIUM | 유지보수성 | 2시간 |
| 12 | 메모리 효율성 | MEDIUM | 확장성 제한 | 3시간 |

---

### 🟢 **여유가 있을 때 개선** (Low Priority)

| # | 문제 | 위험도 | 영향 | 예상 작업 |
|---|------|--------|------|----------|
| 10 | 매직 넘버 | LOW | 가독성 | 30분 |
| 11 | 긴 함수 | LOW | 유지보수성 | 2시간 |
| 13 | 불필요한 계산 | LOW | 성능 | 30분 |
| 14 | print → logging | LOW | 프로덕션 준비 | 1시간 |
| 15 | 타입 힌트 보완 | LOW | 코드 품질 | 1시간 |
| 16 | 문서화 개선 | LOW | 가독성 | 2시간 |

---

## 🎯 개선 로드맵

### Phase 1: 보안 강화 (우선순위 높음) - 1주

```
Week 1:
├── Day 1-2: Path Traversal 수정 및 테스트
├── Day 3: 입력 검증 강화
├── Day 4: 예외 처리 개선
└── Day 5: 정보 노출 최소화 및 테스트
```

### Phase 2: 안정성 개선 (중간 우선순위) - 2주

```
Week 2-3:
├── Race Condition 해결
├── 리소스 관리 개선
├── 크로스 플랫폼 테스트
└── 메모리 효율성 개선
```

### Phase 3: 코드 품질 (낮은 우선순위) - 1주

```
Week 4:
├── Logging 시스템 도입
├── 코드 리팩토링
├── 문서화 보완
└── 단위 테스트 추가
```

---

## 📚 추가 권장사항

### 1. 보안 테스트 도구 도입

```bash
# Static Analysis
bandit -r system_monitor.py

# Dependency Security
pip-audit

# Code Quality
pylint system_monitor.py
flake8 system_monitor.py
```

### 2. 단위 테스트 작성

```python
# tests/test_system_monitor.py
import pytest
from system_monitor import SystemMonitor, validate_output_path

def test_path_traversal_prevention():
    with pytest.raises(ValueError):
        validate_output_path("../../etc/passwd")

    with pytest.raises(ValueError):
        validate_output_path("/tmp/malicious.pdf")

def test_input_validation():
    with pytest.raises(ValueError):
        # duration too long
        validate_duration(999999)

    with pytest.raises(ValueError):
        # interval too small
        validate_interval(0.0001)
```

### 3. 설정 파일 도입

```yaml
# config.yaml
monitoring:
  max_duration: 3600
  min_duration: 1
  max_interval: 60
  min_interval: 0.1
  max_samples: 100000

thresholds:
  cpu:
    high: 80
    moderate: 50
  memory:
    high: 80
    moderate: 50
  disk:
    critical: 90
    warning: 75
  temperature:
    high: 80

security:
  allow_absolute_paths: false
  allowed_extensions: ['.pdf']
  max_filename_length: 255
```

### 4. 환경별 설정

```python
import os

DEBUG_MODE = os.getenv('DEBUG', 'false').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
MAX_DURATION = int(os.getenv('MAX_DURATION', '3600'))
```

---

## 📝 결론

### 종합 평가

`system_monitor.py`는 **기능적으로는 우수**하지만, **보안과 프로덕션 준비 측면에서 개선이 필요**합니다.

### 핵심 위험

1. **Path Traversal 취약점** - 즉시 수정 필요
2. **DoS 공격 가능성** - 입력 검증 강화 필요
3. **정보 노출** - 에러 처리 및 출력 정보 최소화 필요

### 권장 조치

1. ✅ **즉시**: Path Traversal 수정, 입력 검증 강화
2. 📅 **1주 내**: 예외 처리 개선, 정보 노출 최소화
3. 📅 **1달 내**: 리소스 관리, 코드 품질 개선
4. 📅 **지속적**: 단위 테스트, 보안 스캔, 문서화

### 최종 의견

이 코드는 **교육용 또는 개인 사용**에는 적합하지만, **프로덕션 환경**에 배포하기 전에는 반드시 보안 취약점을 수정해야 합니다.

특히 **Path Traversal 취약점**은 시스템 보안에 직접적인 위험을 초래할 수 있으므로, 최우선으로 수정이 필요합니다.

---

**리뷰 작성**: Claude (Anthropic AI)
**분석 기준**: OWASP Top 10, CWE Top 25, Python Security Best Practices
**문의**: 추가 설명이나 코드 수정 지원이 필요하면 연락 주세요.
