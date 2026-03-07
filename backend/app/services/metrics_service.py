"""
Metrics collection service for monitoring and observability.

This module provides:
- Performance metrics collection (response times, request counts)
- Error rate tracking by endpoint and error type
- Privacy-preserving usage analytics (no PII)
- Database query performance tracking
- Cache hit/miss rate tracking
- Document storage operation metrics
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
import statistics


class MetricType(str, Enum):
    """Types of metrics collected"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class EndpointMetric(str, Enum):
    """API endpoint categories for metrics"""
    CHAT = "chat"
    DOCUMENTS = "documents"
    AUTOMATION = "automation"
    DASHBOARD = "dashboard"
    DIGILOCKER = "digilocker"
    OCR = "ocr"
    AUTH = "auth"
    OTHER = "other"


@dataclass
class RequestMetrics:
    """Metrics for a single request"""
    endpoint: str
    method: str
    status_code: int
    duration_ms: float
    timestamp: datetime
    error_type: Optional[str] = None


@dataclass
class AggregatedMetrics:
    """Aggregated metrics for an endpoint"""
    endpoint: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    p50_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    p99_duration_ms: float = 0.0
    error_rate: float = 0.0
    requests_per_minute: float = 0.0
    errors_by_type: Dict[str, int] = field(default_factory=dict)


@dataclass
class DatabaseMetrics:
    """Database query performance metrics"""
    total_queries: int = 0
    slow_queries: int = 0  # Queries > 1000ms
    avg_query_time_ms: float = 0.0
    max_query_time_ms: float = 0.0
    queries_by_table: Dict[str, int] = field(default_factory=dict)


@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    total_requests: int = 0
    hits: int = 0
    misses: int = 0
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    avg_get_time_ms: float = 0.0
    avg_set_time_ms: float = 0.0


@dataclass
class StorageMetrics:
    """Document storage operation metrics"""
    total_uploads: int = 0
    total_downloads: int = 0
    total_deletes: int = 0
    failed_uploads: int = 0
    failed_downloads: int = 0
    avg_upload_time_ms: float = 0.0
    avg_download_time_ms: float = 0.0
    total_bytes_uploaded: int = 0
    total_bytes_downloaded: int = 0


@dataclass
class UsageMetrics:
    """Privacy-preserving usage analytics"""
    total_sessions: int = 0
    active_sessions: int = 0
    avg_session_duration_minutes: float = 0.0
    services_requested: Dict[str, int] = field(default_factory=dict)
    languages_used: Dict[str, int] = field(default_factory=dict)
    automation_sessions: int = 0
    documents_processed: int = 0


class MetricsCollector:
    """
    Thread-safe metrics collection service.
    
    Collects and aggregates metrics for monitoring and observability.
    All metrics are privacy-preserving (no PII stored).
    """
    
    def __init__(self, retention_minutes: int = 60):
        """
        Initialize metrics collector.
        
        Args:
            retention_minutes: How long to retain detailed metrics in memory
        """
        self.retention_minutes = retention_minutes
        self._lock = threading.RLock()
        
        # Request metrics storage (time-windowed)
        self._request_metrics: deque = deque(maxlen=10000)
        
        # Aggregated metrics by endpoint
        self._endpoint_metrics: Dict[str, List[float]] = defaultdict(list)
        
        # Error tracking
        self._errors_by_endpoint: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        # Database metrics
        self._db_queries: List[Dict[str, Any]] = []
        
        # Cache metrics
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_get_times: List[float] = []
        self._cache_set_times: List[float] = []
        
        # Storage metrics
        self._storage_uploads = 0
        self._storage_downloads = 0
        self._storage_deletes = 0
        self._storage_failed_uploads = 0
        self._storage_failed_downloads = 0
        self._storage_upload_times: List[float] = []
        self._storage_download_times: List[float] = []
        self._storage_bytes_uploaded = 0
        self._storage_bytes_downloaded = 0
        
        # Usage metrics
        self._total_sessions = 0
        self._active_sessions = set()
        self._session_durations: List[float] = []
        self._services_requested: Dict[str, int] = defaultdict(int)
        self._languages_used: Dict[str, int] = defaultdict(int)
        self._automation_sessions = 0
        self._documents_processed = 0
    
    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        error_type: Optional[str] = None
    ) -> None:
        """
        Record API request metrics.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            status_code: Response status code
            duration_ms: Request duration in milliseconds
            error_type: Type of error if request failed
        """
        with self._lock:
            metric = RequestMetrics(
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                duration_ms=duration_ms,
                timestamp=datetime.now(timezone.utc),
                error_type=error_type
            )
            
            self._request_metrics.append(metric)
            self._endpoint_metrics[endpoint].append(duration_ms)
            
            # Track errors
            if error_type:
                self._errors_by_endpoint[endpoint][error_type] += 1
            
            # Cleanup old metrics
            self._cleanup_old_metrics()
    
    def record_database_query(
        self,
        table: str,
        duration_ms: float,
        query_type: str = "SELECT"
    ) -> None:
        """
        Record database query metrics.
        
        Args:
            table: Database table name
            duration_ms: Query duration in milliseconds
            query_type: Type of query (SELECT, INSERT, UPDATE, DELETE)
        """
        with self._lock:
            self._db_queries.append({
                'table': table,
                'duration_ms': duration_ms,
                'query_type': query_type,
                'timestamp': datetime.now(timezone.utc)
            })
            
            # Keep only recent queries
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.retention_minutes)
            self._db_queries = [
                q for q in self._db_queries
                if q['timestamp'] > cutoff
            ]
    
    def record_cache_hit(self, duration_ms: float = 0.0) -> None:
        """Record cache hit."""
        with self._lock:
            self._cache_hits += 1
            if duration_ms > 0:
                self._cache_get_times.append(duration_ms)
    
    def record_cache_miss(self, duration_ms: float = 0.0) -> None:
        """Record cache miss."""
        with self._lock:
            self._cache_misses += 1
            if duration_ms > 0:
                self._cache_get_times.append(duration_ms)
    
    def record_cache_set(self, duration_ms: float) -> None:
        """Record cache set operation."""
        with self._lock:
            self._cache_set_times.append(duration_ms)
    
    def record_storage_upload(
        self,
        duration_ms: float,
        bytes_uploaded: int,
        success: bool = True
    ) -> None:
        """Record document upload."""
        with self._lock:
            if success:
                self._storage_uploads += 1
                self._storage_upload_times.append(duration_ms)
                self._storage_bytes_uploaded += bytes_uploaded
            else:
                self._storage_failed_uploads += 1
    
    def record_storage_download(
        self,
        duration_ms: float,
        bytes_downloaded: int,
        success: bool = True
    ) -> None:
        """Record document download."""
        with self._lock:
            if success:
                self._storage_downloads += 1
                self._storage_download_times.append(duration_ms)
                self._storage_bytes_downloaded += bytes_downloaded
            else:
                self._storage_failed_downloads += 1
    
    def record_storage_delete(self) -> None:
        """Record document deletion."""
        with self._lock:
            self._storage_deletes += 1
    
    def record_session_start(self, session_id: str) -> None:
        """Record new session start (privacy-preserving)."""
        with self._lock:
            self._total_sessions += 1
            self._active_sessions.add(session_id)
    
    def record_session_end(self, session_id: str, duration_minutes: float) -> None:
        """Record session end."""
        with self._lock:
            self._active_sessions.discard(session_id)
            self._session_durations.append(duration_minutes)
    
    def record_service_request(self, service_category: str) -> None:
        """Record service request (aggregated, no user info)."""
        with self._lock:
            self._services_requested[service_category] += 1
    
    def record_language_usage(self, language: str) -> None:
        """Record language usage (aggregated)."""
        with self._lock:
            self._languages_used[language] += 1
    
    def record_automation_session(self) -> None:
        """Record automation session start."""
        with self._lock:
            self._automation_sessions += 1
    
    def record_document_processed(self) -> None:
        """Record document processing (OCR, parsing, etc.)."""
        with self._lock:
            self._documents_processed += 1
    
    def get_endpoint_metrics(self, endpoint: Optional[str] = None) -> Dict[str, AggregatedMetrics]:
        """
        Get aggregated metrics for endpoints.
        
        Args:
            endpoint: Specific endpoint to get metrics for, or None for all
            
        Returns:
            Dictionary of endpoint metrics
        """
        with self._lock:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.retention_minutes)
            recent_metrics = [
                m for m in self._request_metrics
                if m.timestamp > cutoff
            ]
            
            # Group by endpoint
            endpoint_groups: Dict[str, List[RequestMetrics]] = defaultdict(list)
            for metric in recent_metrics:
                if endpoint is None or metric.endpoint == endpoint:
                    endpoint_groups[metric.endpoint].append(metric)
            
            # Aggregate metrics
            result = {}
            for ep, metrics in endpoint_groups.items():
                durations = [m.duration_ms for m in metrics]
                successful = [m for m in metrics if 200 <= m.status_code < 400]
                failed = [m for m in metrics if m.status_code >= 400]
                
                # Calculate percentiles
                sorted_durations = sorted(durations)
                p50 = self._percentile(sorted_durations, 50)
                p95 = self._percentile(sorted_durations, 95)
                p99 = self._percentile(sorted_durations, 99)
                
                # Calculate requests per minute
                if metrics:
                    time_span_minutes = (
                        max(m.timestamp for m in metrics) - 
                        min(m.timestamp for m in metrics)
                    ).total_seconds() / 60
                    rpm = len(metrics) / max(time_span_minutes, 1)
                else:
                    rpm = 0.0
                
                result[ep] = AggregatedMetrics(
                    endpoint=ep,
                    total_requests=len(metrics),
                    successful_requests=len(successful),
                    failed_requests=len(failed),
                    total_duration_ms=sum(durations),
                    min_duration_ms=min(durations) if durations else 0.0,
                    max_duration_ms=max(durations) if durations else 0.0,
                    avg_duration_ms=statistics.mean(durations) if durations else 0.0,
                    p50_duration_ms=p50,
                    p95_duration_ms=p95,
                    p99_duration_ms=p99,
                    error_rate=len(failed) / len(metrics) if metrics else 0.0,
                    requests_per_minute=rpm,
                    errors_by_type=dict(self._errors_by_endpoint.get(ep, {}))
                )
            
            return result
    
    def get_database_metrics(self) -> DatabaseMetrics:
        """Get database performance metrics."""
        with self._lock:
            if not self._db_queries:
                return DatabaseMetrics()
            
            durations = [q['duration_ms'] for q in self._db_queries]
            slow_queries = [q for q in self._db_queries if q['duration_ms'] > 1000]
            
            queries_by_table = defaultdict(int)
            for query in self._db_queries:
                queries_by_table[query['table']] += 1
            
            return DatabaseMetrics(
                total_queries=len(self._db_queries),
                slow_queries=len(slow_queries),
                avg_query_time_ms=statistics.mean(durations) if durations else 0.0,
                max_query_time_ms=max(durations) if durations else 0.0,
                queries_by_table=dict(queries_by_table)
            )
    
    def get_cache_metrics(self) -> CacheMetrics:
        """Get cache performance metrics."""
        with self._lock:
            total = self._cache_hits + self._cache_misses
            
            return CacheMetrics(
                total_requests=total,
                hits=self._cache_hits,
                misses=self._cache_misses,
                hit_rate=self._cache_hits / total if total > 0 else 0.0,
                miss_rate=self._cache_misses / total if total > 0 else 0.0,
                avg_get_time_ms=statistics.mean(self._cache_get_times) if self._cache_get_times else 0.0,
                avg_set_time_ms=statistics.mean(self._cache_set_times) if self._cache_set_times else 0.0
            )
    
    def get_storage_metrics(self) -> StorageMetrics:
        """Get document storage metrics."""
        with self._lock:
            return StorageMetrics(
                total_uploads=self._storage_uploads,
                total_downloads=self._storage_downloads,
                total_deletes=self._storage_deletes,
                failed_uploads=self._storage_failed_uploads,
                failed_downloads=self._storage_failed_downloads,
                avg_upload_time_ms=statistics.mean(self._storage_upload_times) if self._storage_upload_times else 0.0,
                avg_download_time_ms=statistics.mean(self._storage_download_times) if self._storage_download_times else 0.0,
                total_bytes_uploaded=self._storage_bytes_uploaded,
                total_bytes_downloaded=self._storage_bytes_downloaded
            )
    
    def get_usage_metrics(self) -> UsageMetrics:
        """Get privacy-preserving usage analytics."""
        with self._lock:
            return UsageMetrics(
                total_sessions=self._total_sessions,
                active_sessions=len(self._active_sessions),
                avg_session_duration_minutes=statistics.mean(self._session_durations) if self._session_durations else 0.0,
                services_requested=dict(self._services_requested),
                languages_used=dict(self._languages_used),
                automation_sessions=self._automation_sessions,
                documents_processed=self._documents_processed
            )
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics in a single call.
        
        Returns:
            Dictionary containing all metric categories
        """
        endpoint_metrics = self.get_endpoint_metrics()
        
        return {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'endpoints': {k: asdict(v) for k, v in endpoint_metrics.items()},
            'database': asdict(self.get_database_metrics()),
            'cache': asdict(self.get_cache_metrics()),
            'storage': asdict(self.get_storage_metrics()),
            'usage': asdict(self.get_usage_metrics())
        }
    
    def reset_metrics(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._request_metrics.clear()
            self._endpoint_metrics.clear()
            self._errors_by_endpoint.clear()
            self._db_queries.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            self._cache_get_times.clear()
            self._cache_set_times.clear()
            self._storage_uploads = 0
            self._storage_downloads = 0
            self._storage_deletes = 0
            self._storage_failed_uploads = 0
            self._storage_failed_downloads = 0
            self._storage_upload_times.clear()
            self._storage_download_times.clear()
            self._storage_bytes_uploaded = 0
            self._storage_bytes_downloaded = 0
            self._total_sessions = 0
            self._active_sessions.clear()
            self._session_durations.clear()
            self._services_requested.clear()
            self._languages_used.clear()
            self._automation_sessions = 0
            self._documents_processed = 0
    
    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than retention period."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.retention_minutes)
        
        # Request metrics are handled by deque maxlen
        # Just need to clean up endpoint metrics
        for endpoint in list(self._endpoint_metrics.keys()):
            # Keep only recent durations (approximate)
            if len(self._endpoint_metrics[endpoint]) > 1000:
                self._endpoint_metrics[endpoint] = self._endpoint_metrics[endpoint][-1000:]
    
    @staticmethod
    def _percentile(sorted_data: List[float], percentile: int) -> float:
        """Calculate percentile from sorted data."""
        if not sorted_data:
            return 0.0
        
        index = (len(sorted_data) - 1) * percentile / 100
        lower = int(index)
        upper = lower + 1
        
        if upper >= len(sorted_data):
            return sorted_data[-1]
        
        weight = index - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_metrics_collector() -> None:
    """Reset the global metrics collector (useful for testing)."""
    global _metrics_collector
    _metrics_collector = None
