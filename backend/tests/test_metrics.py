"""
Unit tests for metrics collection service.

Tests cover:
- Request metrics collection
- Database query metrics
- Cache metrics
- Storage metrics
- Usage analytics (privacy-preserving)
- Metrics aggregation
- Metrics endpoints
"""

import pytest
import time
from datetime import datetime, timedelta, timezone

from app.services.metrics_service import (
    MetricsCollector,
    get_metrics_collector,
    reset_metrics_collector,
    AggregatedMetrics,
    DatabaseMetrics,
    CacheMetrics,
    StorageMetrics,
    UsageMetrics
)


@pytest.fixture
def metrics_collector():
    """Create a fresh metrics collector for each test."""
    reset_metrics_collector()
    collector = MetricsCollector(retention_minutes=60)
    return collector


class TestMetricsCollector:
    """Test metrics collector functionality."""
    
    def test_record_request_metrics(self, metrics_collector):
        """Test recording request metrics."""
        metrics_collector.record_request(
            endpoint="/api/v1/chat",
            method="POST",
            status_code=200,
            duration_ms=150.5
        )
        
        endpoint_metrics = metrics_collector.get_endpoint_metrics()
        assert "/api/v1/chat" in endpoint_metrics
        
        chat_metrics = endpoint_metrics["/api/v1/chat"]
        assert chat_metrics.total_requests == 1
        assert chat_metrics.successful_requests == 1
        assert chat_metrics.failed_requests == 0
        assert chat_metrics.avg_duration_ms == 150.5
    
    def test_record_multiple_requests(self, metrics_collector):
        """Test recording multiple requests to same endpoint."""
        for i in range(10):
            metrics_collector.record_request(
                endpoint="/api/v1/documents",
                method="GET",
                status_code=200,
                duration_ms=100.0 + i * 10
            )
        
        endpoint_metrics = metrics_collector.get_endpoint_metrics()
        docs_metrics = endpoint_metrics["/api/v1/documents"]
        
        assert docs_metrics.total_requests == 10
        assert docs_metrics.successful_requests == 10
        assert docs_metrics.min_duration_ms == 100.0
        assert docs_metrics.max_duration_ms == 190.0
        assert 140 < docs_metrics.avg_duration_ms < 150
    
    def test_record_failed_requests(self, metrics_collector):
        """Test recording failed requests with error types."""
        metrics_collector.record_request(
            endpoint="/api/v1/automation",
            method="POST",
            status_code=500,
            duration_ms=50.0,
            error_type="ValueError"
        )
        
        metrics_collector.record_request(
            endpoint="/api/v1/automation",
            method="POST",
            status_code=404,
            duration_ms=30.0,
            error_type="NotFoundError"
        )
        
        endpoint_metrics = metrics_collector.get_endpoint_metrics()
        auto_metrics = endpoint_metrics["/api/v1/automation"]
        
        assert auto_metrics.total_requests == 2
        assert auto_metrics.failed_requests == 2
        assert auto_metrics.error_rate == 1.0
        assert "ValueError" in auto_metrics.errors_by_type
        assert "NotFoundError" in auto_metrics.errors_by_type
    
    def test_percentile_calculations(self, metrics_collector):
        """Test percentile calculations for response times."""
        # Record 100 requests with varying durations
        for i in range(100):
            metrics_collector.record_request(
                endpoint="/api/v1/test",
                method="GET",
                status_code=200,
                duration_ms=float(i + 1)
            )
        
        endpoint_metrics = metrics_collector.get_endpoint_metrics()
        test_metrics = endpoint_metrics["/api/v1/test"]
        
        # Check percentiles
        assert 45 < test_metrics.p50_duration_ms < 55  # Median around 50
        assert 90 < test_metrics.p95_duration_ms < 100  # 95th percentile
        assert 95 < test_metrics.p99_duration_ms < 100  # 99th percentile
    
    def test_database_metrics(self, metrics_collector):
        """Test database query metrics collection."""
        metrics_collector.record_database_query("users", 50.0, "SELECT")
        metrics_collector.record_database_query("documents", 1500.0, "SELECT")
        metrics_collector.record_database_query("sessions", 30.0, "INSERT")
        
        db_metrics = metrics_collector.get_database_metrics()
        
        assert db_metrics.total_queries == 3
        assert db_metrics.slow_queries == 1  # 1500ms query
        assert db_metrics.max_query_time_ms == 1500.0
        assert "users" in db_metrics.queries_by_table
        assert "documents" in db_metrics.queries_by_table
        assert "sessions" in db_metrics.queries_by_table
    
    def test_cache_hit_metrics(self, metrics_collector):
        """Test cache hit/miss tracking."""
        # Record cache operations
        for _ in range(7):
            metrics_collector.record_cache_hit(duration_ms=5.0)
        
        for _ in range(3):
            metrics_collector.record_cache_miss(duration_ms=10.0)
        
        cache_metrics = metrics_collector.get_cache_metrics()
        
        assert cache_metrics.total_requests == 10
        assert cache_metrics.hits == 7
        assert cache_metrics.misses == 3
        assert cache_metrics.hit_rate == 0.7
        assert cache_metrics.miss_rate == 0.3
    
    def test_cache_set_metrics(self, metrics_collector):
        """Test cache set operation metrics."""
        for i in range(5):
            metrics_collector.record_cache_set(duration_ms=20.0 + i)
        
        cache_metrics = metrics_collector.get_cache_metrics()
        assert 20 < cache_metrics.avg_set_time_ms < 25
    
    def test_storage_upload_metrics(self, metrics_collector):
        """Test document upload metrics."""
        metrics_collector.record_storage_upload(
            duration_ms=500.0,
            bytes_uploaded=1024 * 1024,  # 1MB
            success=True
        )
        
        metrics_collector.record_storage_upload(
            duration_ms=0.0,
            bytes_uploaded=0,
            success=False
        )
        
        storage_metrics = metrics_collector.get_storage_metrics()
        
        assert storage_metrics.total_uploads == 1
        assert storage_metrics.failed_uploads == 1
        assert storage_metrics.total_bytes_uploaded == 1024 * 1024
        assert storage_metrics.avg_upload_time_ms == 500.0
    
    def test_storage_download_metrics(self, metrics_collector):
        """Test document download metrics."""
        metrics_collector.record_storage_download(
            duration_ms=300.0,
            bytes_downloaded=2 * 1024 * 1024,  # 2MB
            success=True
        )
        
        storage_metrics = metrics_collector.get_storage_metrics()
        
        assert storage_metrics.total_downloads == 1
        assert storage_metrics.total_bytes_downloaded == 2 * 1024 * 1024
        assert storage_metrics.avg_download_time_ms == 300.0
    
    def test_storage_delete_metrics(self, metrics_collector):
        """Test document deletion metrics."""
        for _ in range(3):
            metrics_collector.record_storage_delete()
        
        storage_metrics = metrics_collector.get_storage_metrics()
        assert storage_metrics.total_deletes == 3
    
    def test_session_metrics(self, metrics_collector):
        """Test session tracking (privacy-preserving)."""
        # Start sessions
        metrics_collector.record_session_start("session_1")
        metrics_collector.record_session_start("session_2")
        metrics_collector.record_session_start("session_3")
        
        # End some sessions
        metrics_collector.record_session_end("session_1", duration_minutes=15.5)
        metrics_collector.record_session_end("session_2", duration_minutes=30.0)
        
        usage_metrics = metrics_collector.get_usage_metrics()
        
        assert usage_metrics.total_sessions == 3
        assert usage_metrics.active_sessions == 1  # session_3 still active
        assert 20 < usage_metrics.avg_session_duration_minutes < 25
    
    def test_service_request_metrics(self, metrics_collector):
        """Test service request tracking (aggregated)."""
        metrics_collector.record_service_request("aadhaar")
        metrics_collector.record_service_request("aadhaar")
        metrics_collector.record_service_request("pan_card")
        metrics_collector.record_service_request("certificate")
        
        usage_metrics = metrics_collector.get_usage_metrics()
        
        assert usage_metrics.services_requested["aadhaar"] == 2
        assert usage_metrics.services_requested["pan_card"] == 1
        assert usage_metrics.services_requested["certificate"] == 1
    
    def test_language_usage_metrics(self, metrics_collector):
        """Test language usage tracking."""
        metrics_collector.record_language_usage("en")
        metrics_collector.record_language_usage("en")
        metrics_collector.record_language_usage("hi")
        
        usage_metrics = metrics_collector.get_usage_metrics()
        
        assert usage_metrics.languages_used["en"] == 2
        assert usage_metrics.languages_used["hi"] == 1
    
    def test_automation_session_metrics(self, metrics_collector):
        """Test automation session tracking."""
        for _ in range(5):
            metrics_collector.record_automation_session()
        
        usage_metrics = metrics_collector.get_usage_metrics()
        assert usage_metrics.automation_sessions == 5
    
    def test_document_processing_metrics(self, metrics_collector):
        """Test document processing tracking."""
        for _ in range(10):
            metrics_collector.record_document_processed()
        
        usage_metrics = metrics_collector.get_usage_metrics()
        assert usage_metrics.documents_processed == 10
    
    def test_get_all_metrics(self, metrics_collector):
        """Test getting all metrics at once."""
        # Record various metrics
        metrics_collector.record_request("/api/v1/test", "GET", 200, 100.0)
        metrics_collector.record_database_query("users", 50.0)
        metrics_collector.record_cache_hit()
        metrics_collector.record_storage_upload(100.0, 1024, True)
        metrics_collector.record_session_start("session_1")
        
        all_metrics = metrics_collector.get_all_metrics()
        
        assert "timestamp" in all_metrics
        assert "endpoints" in all_metrics
        assert "database" in all_metrics
        assert "cache" in all_metrics
        assert "storage" in all_metrics
        assert "usage" in all_metrics
    
    def test_reset_metrics(self, metrics_collector):
        """Test resetting all metrics."""
        # Record some metrics
        metrics_collector.record_request("/api/v1/test", "GET", 200, 100.0)
        metrics_collector.record_cache_hit()
        metrics_collector.record_session_start("session_1")
        
        # Reset
        metrics_collector.reset_metrics()
        
        # Verify all metrics are cleared
        endpoint_metrics = metrics_collector.get_endpoint_metrics()
        cache_metrics = metrics_collector.get_cache_metrics()
        usage_metrics = metrics_collector.get_usage_metrics()
        
        assert len(endpoint_metrics) == 0
        assert cache_metrics.total_requests == 0
        assert usage_metrics.total_sessions == 0
    
    def test_metrics_retention(self, metrics_collector):
        """Test that metrics are retained for the configured period."""
        # Create collector with normal retention
        normal_retention = MetricsCollector(retention_minutes=60)
        
        # Record a metric
        normal_retention.record_request("/api/v1/test", "GET", 200, 100.0)
        
        # Metrics should be available
        endpoint_metrics = normal_retention.get_endpoint_metrics()
        assert len(endpoint_metrics) > 0
        assert "/api/v1/test" in endpoint_metrics
    
    def test_thread_safety(self, metrics_collector):
        """Test thread-safe metric collection."""
        import threading
        
        def record_metrics():
            for i in range(100):
                metrics_collector.record_request(
                    "/api/v1/test",
                    "GET",
                    200,
                    float(i)
                )
        
        # Create multiple threads
        threads = [threading.Thread(target=record_metrics) for _ in range(5)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify all requests were recorded
        endpoint_metrics = metrics_collector.get_endpoint_metrics()
        test_metrics = endpoint_metrics["/api/v1/test"]
        assert test_metrics.total_requests == 500  # 5 threads * 100 requests
    
    def test_specific_endpoint_metrics(self, metrics_collector):
        """Test getting metrics for specific endpoint."""
        metrics_collector.record_request("/api/v1/chat", "POST", 200, 100.0)
        metrics_collector.record_request("/api/v1/documents", "GET", 200, 50.0)
        
        # Get specific endpoint
        chat_metrics = metrics_collector.get_endpoint_metrics("/api/v1/chat")
        
        assert len(chat_metrics) == 1
        assert "/api/v1/chat" in chat_metrics
        assert "/api/v1/documents" not in chat_metrics


class TestPrivacyPreservation:
    """Test that metrics are privacy-preserving."""
    
    def test_no_pii_in_metrics(self, metrics_collector):
        """Test that no PII is stored in metrics."""
        # Record various metrics
        metrics_collector.record_session_start("user_12345_session")
        metrics_collector.record_service_request("aadhaar")
        metrics_collector.record_language_usage("en")
        
        # Get all metrics
        all_metrics = metrics_collector.get_all_metrics()
        
        # Convert to string and check for PII patterns
        metrics_str = str(all_metrics)
        
        # Should not contain user IDs or session IDs in aggregated metrics
        usage = all_metrics["usage"]
        assert "user_12345" not in str(usage)
        
        # Only aggregated counts should be present
        assert isinstance(usage["total_sessions"], int)
        assert isinstance(usage["services_requested"], dict)
    
    def test_aggregated_usage_only(self, metrics_collector):
        """Test that usage metrics are aggregated only."""
        # Record multiple sessions
        for i in range(10):
            metrics_collector.record_session_start(f"session_{i}")
            metrics_collector.record_service_request("aadhaar")
        
        usage_metrics = metrics_collector.get_usage_metrics()
        
        # Should only have counts, not individual session data
        assert usage_metrics.total_sessions == 10
        assert usage_metrics.services_requested["aadhaar"] == 10
        
        # No individual session information
        assert not hasattr(usage_metrics, 'session_ids')
        assert not hasattr(usage_metrics, 'user_ids')
