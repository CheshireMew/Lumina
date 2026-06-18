"""
Observability Package.
Provides metrics, structured logging, and tracing capabilities.
"""

from .metrics import (
    get_metrics,
    get_metrics_content_type,
    track_request_duration,
    record_llm_request,
    record_stt_transcription,
    record_tts_generation,
    update_worker_status,
    update_provider_status,
    # Expose raw metrics for direct access
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION,
    ACTIVE_WORKERS,
    WORKER_LOAD,
    PROVIDER_STATUS,
    LLM_REQUESTS,
    LLM_TOKENS,
)

from .structured_logger import (
    get_structured_logger,
    set_log_context,
    reset_log_context,
    log_duration,
    StructuredLogger,
    trace_id_ctx,
    user_id_ctx,
    operation_ctx,
)

__all__ = [
    # Metrics
    'get_metrics',
    'get_metrics_content_type',
    'track_request_duration',
    'record_llm_request',
    'record_stt_transcription',
    'record_tts_generation',
    'update_worker_status',
    'update_provider_status',
    # Structured Logging
    'get_structured_logger',
    'set_log_context',
    'reset_log_context',
    'log_duration',
    'StructuredLogger',
]

