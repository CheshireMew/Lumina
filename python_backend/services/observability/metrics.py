"""
Observability - Metrics Module.
Prometheus-compatible metrics for monitoring Lumina services.
"""

import time
import logging
from typing import Optional, Callable
from functools import wraps

from prometheus_client import Counter, Histogram, Gauge, Info, REGISTRY
from prometheus_client.exposition import generate_latest, CONTENT_TYPE_LATEST

logger = logging.getLogger("Observability.Metrics")

# ============================================================
# Application Info
# ============================================================

APP_INFO = Info('lumina', 'Lumina Application Info')
APP_INFO.info({
    'version': '5.6.0',
    'service': 'main'
})

# ============================================================
# HTTP Request Metrics
# ============================================================

HTTP_REQUESTS_TOTAL = Counter(
    'lumina_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

HTTP_REQUEST_DURATION = Histogram(
    'lumina_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    'lumina_http_requests_in_progress',
    'HTTP requests currently in progress',
    ['method', 'endpoint']
)

# ============================================================
# Worker Metrics
# ============================================================

ACTIVE_WORKERS = Gauge(
    'lumina_active_workers',
    'Number of active worker connections',
    ['worker_type']
)

WORKER_LOAD = Gauge(
    'lumina_worker_load',
    'Worker load (0.0 - 1.0)',
    ['worker_id', 'worker_type']
)

WORKER_HEARTBEATS = Counter(
    'lumina_worker_heartbeats_total',
    'Total worker heartbeats received',
    ['worker_id']
)

# ============================================================
# Capability Module Metrics
# ============================================================

CAPABILITY_MODULE_STATUS = Gauge(
    'lumina_capability_module_status',
    'Capability module status (1=enabled, 0=disabled)',
    ['module_id', 'module_type']
)

CAPABILITY_MODULE_INVOCATIONS = Counter(
    'lumina_capability_module_invocations_total',
    'Total capability module invocations',
    ['module_id', 'result']  # result: success, error
)

# ============================================================
# LLM Metrics
# ============================================================

LLM_REQUESTS = Counter(
    'lumina_llm_requests_total',
    'Total LLM API requests',
    ['model', 'status']
)

LLM_TOKENS = Counter(
    'lumina_llm_tokens_total',
    'Total LLM tokens used',
    ['model', 'type']  # type: prompt, completion
)

LLM_REQUEST_DURATION = Histogram(
    'lumina_llm_request_duration_seconds',
    'LLM request duration in seconds',
    ['model'],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

# ============================================================
# STT/TTS Metrics
# ============================================================

STT_TRANSCRIPTIONS = Counter(
    'lumina_stt_transcriptions_total',
    'Total STT transcriptions',
    ['driver', 'status']
)

STT_AUDIO_DURATION = Histogram(
    'lumina_stt_audio_duration_seconds',
    'Duration of audio processed by STT',
    ['driver'],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0)
)

TTS_GENERATIONS = Counter(
    'lumina_tts_generations_total',
    'Total TTS generations',
    ['driver', 'status']
)

TTS_TEXT_LENGTH = Histogram(
    'lumina_tts_text_length_chars',
    'Length of text processed by TTS',
    ['driver'],
    buckets=(10, 50, 100, 250, 500, 1000, 2500)
)

# ============================================================
# Memory/Database Metrics
# ============================================================

MEMORY_OPERATIONS = Counter(
    'lumina_memory_operations_total',
    'Total memory operations',
    ['operation', 'status']  # operation: add, search, delete
)

DB_CONNECTIONS = Gauge(
    'lumina_db_connections_active',
    'Active database connections'
)

# ============================================================
# Utility Functions
# ============================================================

def get_metrics() -> bytes:
    """Generate Prometheus metrics output."""
    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """Get content type for metrics response."""
    return CONTENT_TYPE_LATEST


def track_request_duration(method: str, endpoint: str):
    """Decorator to track request duration."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
            start_time = time.time()
            status_code = "200"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status_code = "500"
                raise
            finally:
                duration = time.time() - start_time
                HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
                HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
                HTTP_REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
        return wrapper
    return decorator


# ============================================================
# Convenience Functions for Common Operations
# ============================================================

def record_llm_request(model: str, prompt_tokens: int, completion_tokens: int, 
                       duration: float, success: bool = True):
    """Record LLM request metrics."""
    status = "success" if success else "error"
    LLM_REQUESTS.labels(model=model, status=status).inc()
    LLM_TOKENS.labels(model=model, type="prompt").inc(prompt_tokens)
    LLM_TOKENS.labels(model=model, type="completion").inc(completion_tokens)
    LLM_REQUEST_DURATION.labels(model=model).observe(duration)


def record_stt_transcription(driver: str, audio_duration: float, success: bool = True):
    """Record STT transcription metrics."""
    status = "success" if success else "error"
    STT_TRANSCRIPTIONS.labels(driver=driver, status=status).inc()
    if success:
        STT_AUDIO_DURATION.labels(driver=driver).observe(audio_duration)


def record_tts_generation(driver: str, text_length: int, success: bool = True):
    """Record TTS generation metrics."""
    status = "success" if success else "error"
    TTS_GENERATIONS.labels(driver=driver, status=status).inc()
    if success:
        TTS_TEXT_LENGTH.labels(driver=driver).observe(text_length)


def update_worker_status(worker_id: str, worker_type: str, load: float):
    """Update worker status metrics."""
    WORKER_LOAD.labels(worker_id=worker_id, worker_type=worker_type).set(load)
    WORKER_HEARTBEATS.labels(worker_id=worker_id).inc()


def update_capability_module_status(module_id: str, module_type: str, enabled: bool):
    """Update capability module status metric."""
    CAPABILITY_MODULE_STATUS.labels(module_id=module_id, module_type=module_type).set(1 if enabled else 0)


logger.info("📊 Prometheus metrics module initialized")
