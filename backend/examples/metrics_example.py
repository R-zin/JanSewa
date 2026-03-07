"""
Example demonstrating the metrics collection system.

This example shows how to:
1. Record various types of metrics
2. Retrieve aggregated metrics
3. Use metrics for monitoring
"""

from app.services.metrics_service import get_metrics_collector
import time
import random


def simulate_api_requests():
    """Simulate API requests with varying performance."""
    metrics = get_metrics_collector()
    
    print("Simulating API requests...")
    
    # Simulate 100 requests to different endpoints
    endpoints = [
        "/api/v1/chat",
        "/api/v1/documents",
        "/api/v1/automation",
        "/api/v1/dashboard"
    ]
    
    for i in range(100):
        endpoint = random.choice(endpoints)
        
        # Simulate varying response times
        duration_ms = random.uniform(50, 500)
        
        # Simulate occasional errors
        if random.random() < 0.05:  # 5% error rate
            status_code = 500
            error_type = "InternalServerError"
        else:
            status_code = 200
            error_type = None
        
        metrics.record_request(
            endpoint=endpoint,
            method="POST" if endpoint == "/api/v1/chat" else "GET",
            status_code=status_code,
            duration_ms=duration_ms,
            error_type=error_type
        )
    
    print(f"✓ Recorded {100} API requests")


def simulate_database_queries():
    """Simulate database queries."""
    metrics = get_metrics_collector()
    
    print("\nSimulating database queries...")
    
    tables = ["users", "documents", "sessions", "service_requests"]
    
    for i in range(50):
        table = random.choice(tables)
        
        # Simulate varying query times
        duration_ms = random.uniform(10, 200)
        
        # Occasionally simulate slow queries
        if random.random() < 0.1:  # 10% slow queries
            duration_ms = random.uniform(1000, 2000)
        
        metrics.record_database_query(
            table=table,
            duration_ms=duration_ms,
            query_type="SELECT"
        )
    
    print(f"✓ Recorded {50} database queries")


def simulate_cache_operations():
    """Simulate cache operations."""
    metrics = get_metrics_collector()
    
    print("\nSimulating cache operations...")
    
    # Simulate 80% hit rate
    for i in range(100):
        if random.random() < 0.8:
            metrics.record_cache_hit(duration_ms=random.uniform(1, 5))
        else:
            metrics.record_cache_miss(duration_ms=random.uniform(5, 15))
    
    print(f"✓ Recorded {100} cache operations")


def simulate_storage_operations():
    """Simulate document storage operations."""
    metrics = get_metrics_collector()
    
    print("\nSimulating storage operations...")
    
    # Simulate uploads
    for i in range(20):
        metrics.record_storage_upload(
            duration_ms=random.uniform(200, 800),
            bytes_uploaded=random.randint(100_000, 5_000_000),
            success=random.random() > 0.05  # 95% success rate
        )
    
    # Simulate downloads
    for i in range(50):
        metrics.record_storage_download(
            duration_ms=random.uniform(100, 400),
            bytes_downloaded=random.randint(100_000, 5_000_000),
            success=random.random() > 0.02  # 98% success rate
        )
    
    print(f"✓ Recorded {70} storage operations")


def simulate_usage_analytics():
    """Simulate privacy-preserving usage analytics."""
    metrics = get_metrics_collector()
    
    print("\nSimulating usage analytics...")
    
    # Simulate sessions
    for i in range(50):
        session_id = f"session_{i}"
        metrics.record_session_start(session_id)
        
        # Simulate some sessions ending
        if i < 40:
            metrics.record_session_end(
                session_id,
                duration_minutes=random.uniform(5, 30)
            )
    
    # Simulate service requests
    services = ["aadhaar", "pan_card", "certificate", "voter_id"]
    for _ in range(100):
        metrics.record_service_request(random.choice(services))
    
    # Simulate language usage
    languages = ["en", "hi", "ta", "te", "bn"]
    for _ in range(100):
        metrics.record_language_usage(random.choice(languages))
    
    # Simulate automation sessions
    for _ in range(25):
        metrics.record_automation_session()
    
    # Simulate document processing
    for _ in range(60):
        metrics.record_document_processed()
    
    print(f"✓ Recorded usage analytics (privacy-preserving)")


def display_metrics():
    """Display collected metrics."""
    metrics = get_metrics_collector()
    
    print("\n" + "="*80)
    print("METRICS SUMMARY")
    print("="*80)
    
    # Endpoint metrics
    print("\n📊 API ENDPOINT PERFORMANCE")
    print("-" * 80)
    endpoint_metrics = metrics.get_endpoint_metrics()
    
    for endpoint, data in sorted(endpoint_metrics.items()):
        print(f"\n{endpoint}")
        print(f"  Total Requests:     {data.total_requests}")
        print(f"  Success Rate:       {(data.successful_requests/data.total_requests)*100:.1f}%")
        print(f"  Error Rate:         {data.error_rate*100:.1f}%")
        print(f"  Avg Response Time:  {data.avg_duration_ms:.1f}ms")
        print(f"  P50 Response Time:  {data.p50_duration_ms:.1f}ms")
        print(f"  P95 Response Time:  {data.p95_duration_ms:.1f}ms")
        print(f"  P99 Response Time:  {data.p99_duration_ms:.1f}ms")
        print(f"  Requests/min:       {data.requests_per_minute:.1f}")
        
        if data.errors_by_type:
            print(f"  Errors by Type:     {data.errors_by_type}")
    
    # Database metrics
    print("\n💾 DATABASE PERFORMANCE")
    print("-" * 80)
    db_metrics = metrics.get_database_metrics()
    print(f"Total Queries:      {db_metrics.total_queries}")
    print(f"Slow Queries:       {db_metrics.slow_queries} (>{1000}ms)")
    print(f"Avg Query Time:     {db_metrics.avg_query_time_ms:.1f}ms")
    print(f"Max Query Time:     {db_metrics.max_query_time_ms:.1f}ms")
    print(f"Queries by Table:   {db_metrics.queries_by_table}")
    
    # Cache metrics
    print("\n🔄 CACHE PERFORMANCE")
    print("-" * 80)
    cache_metrics = metrics.get_cache_metrics()
    print(f"Total Requests:     {cache_metrics.total_requests}")
    print(f"Hits:               {cache_metrics.hits}")
    print(f"Misses:             {cache_metrics.misses}")
    print(f"Hit Rate:           {cache_metrics.hit_rate*100:.1f}%")
    print(f"Miss Rate:          {cache_metrics.miss_rate*100:.1f}%")
    print(f"Avg Get Time:       {cache_metrics.avg_get_time_ms:.2f}ms")
    
    # Storage metrics
    print("\n📦 STORAGE OPERATIONS")
    print("-" * 80)
    storage_metrics = metrics.get_storage_metrics()
    print(f"Total Uploads:      {storage_metrics.total_uploads}")
    print(f"Failed Uploads:     {storage_metrics.failed_uploads}")
    print(f"Total Downloads:    {storage_metrics.total_downloads}")
    print(f"Failed Downloads:   {storage_metrics.failed_downloads}")
    print(f"Total Deletes:      {storage_metrics.total_deletes}")
    print(f"Avg Upload Time:    {storage_metrics.avg_upload_time_ms:.1f}ms")
    print(f"Avg Download Time:  {storage_metrics.avg_download_time_ms:.1f}ms")
    print(f"Bytes Uploaded:     {storage_metrics.total_bytes_uploaded:,} bytes ({storage_metrics.total_bytes_uploaded/1024/1024:.1f} MB)")
    print(f"Bytes Downloaded:   {storage_metrics.total_bytes_downloaded:,} bytes ({storage_metrics.total_bytes_downloaded/1024/1024:.1f} MB)")
    
    # Usage metrics
    print("\n👥 USAGE ANALYTICS (Privacy-Preserving)")
    print("-" * 80)
    usage_metrics = metrics.get_usage_metrics()
    print(f"Total Sessions:     {usage_metrics.total_sessions}")
    print(f"Active Sessions:    {usage_metrics.active_sessions}")
    print(f"Avg Session Time:   {usage_metrics.avg_session_duration_minutes:.1f} minutes")
    print(f"Services Requested: {usage_metrics.services_requested}")
    print(f"Languages Used:     {usage_metrics.languages_used}")
    print(f"Automation Sessions:{usage_metrics.automation_sessions}")
    print(f"Documents Processed:{usage_metrics.documents_processed}")
    
    print("\n" + "="*80)
    print("✓ All metrics are privacy-preserving (no PII stored)")
    print("="*80)


def main():
    """Run the metrics example."""
    print("="*80)
    print("METRICS COLLECTION SYSTEM EXAMPLE")
    print("="*80)
    
    # Reset metrics for clean demo
    metrics = get_metrics_collector()
    metrics.reset_metrics()
    
    # Simulate various operations
    simulate_api_requests()
    simulate_database_queries()
    simulate_cache_operations()
    simulate_storage_operations()
    simulate_usage_analytics()
    
    # Display collected metrics
    display_metrics()
    
    print("\n✓ Example completed successfully!")
    print("\nTo access metrics via API:")
    print("  GET http://localhost:8000/api/v1/metrics")
    print("  GET http://localhost:8000/api/v1/metrics/endpoints")
    print("  GET http://localhost:8000/api/v1/metrics/cache")
    print("  GET http://localhost:8000/api/v1/metrics/usage")


if __name__ == "__main__":
    main()
