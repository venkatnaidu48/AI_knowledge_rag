# Monitoring & Observability Setup Guide

## Overview

This guide explains how to set up and configure the complete monitoring and observability stack for the RAG Application.

## Components

1. **Prometheus** - Metrics collection and storage
2. **Grafana** - Metrics visualization and dashboards
3. **Elasticsearch** - Log aggregation (optional)
4. **Kibana** - Log visualization (optional)
5. **Prometheus AlertManager** - Alert routing and notification
6. **Python Prometheus Client** - Application metrics export

## Quick Start

### 1. Basic Monitoring Stack (Prometheus + Grafana)

```bash
# Start the basic monitoring stack
docker-compose --profile monitoring up -d

# Verify services are running
docker-compose ps
```

**Available endpoints:**
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus metrics: http://localhost:8000/metrics

### 2. Full Observability Stack (add Logging)

```bash
# Start with logging stack
docker-compose --profile monitoring --profile logging up -d

# Additional endpoints:
# Elasticsearch: http://localhost:9200
# Kibana: http://localhost:5601
```

## Configuration

### Prometheus Configuration

**File:** `monitoring/prometheus.yml`

Key settings:
```yaml
global:
  scrape_interval: 15s      # Default scrape interval
  evaluation_interval: 15s  # Alert rule evaluation interval

scrape_configs:
  - job_name: 'rag-app'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

### Alert Rules

**File:** `monitoring/alert_rules.yml`

Predefined alerts for:
- Application health (down, high error rate)
- Performance metrics (response time, retrieval time, generation time)
- RAG quality (hallucination rate, confidence score)
- Database issues (connection pool, slow queries)
- Cache issues (low hit ratio)
- Rate limiting (high rejections)

## Monitoring Metrics

### Request Metrics

```
http_requests_total{method, endpoint, status}      - Total requests
http_request_duration_seconds{method, endpoint}    - Request latency
http_request_size_bytes{method, endpoint}          - Request size
http_response_size_bytes{method, endpoint, status} - Response size
```

### RAG Pipeline Metrics

```
rag_documents_total{operation}          - Documents processed
rag_chunks_total                         - Chunks generated
rag_queries_total{status}                - Queries processed
rag_retrieval_time_seconds               - Document retrieval time
rag_generation_time_seconds              - LLM generation time
rag_hallucination_score                  - Current hallucination rate
rag_confidence_score                     - Average confidence
```

### Database Metrics

```
db_connections_total                    - Active connections
db_query_duration_seconds{operation}    - Query latency
```

### Cache Metrics

```
cache_hits_total{cache_type}        - Cache hits
cache_misses_total{cache_type}      - Cache misses
cache_evictions_total{cache_type}   - Cache evictions
```

### Application Health

```
app_health                          - Health status (1=healthy, 0=unhealthy)
app_info{app_name, version, env}   - Application information
```

## Accessing Metrics

### 1. Prometheus Query Interface

Access: http://localhost:9090

**Example queries:**
```
# HTTP request rate (requests/sec)
rate(http_requests_total[1m])

# Average response time (milliseconds)
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) * 1000

# Hallucination rate
rag_hallucination_score

# Document retrieval success rate
(sum(rag_documents_total{operation="ingestion"}) / 
 (sum(rag_documents_total) + 1)) * 100

# Cache hit ratio
sum(rate(cache_hits_total[5m])) / 
(sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m])))
```

### 2. Grafana Dashboards

Access: http://localhost:3000 (admin/admin)

**default dashboards available:**
- Application Health Dashboard
- RAG Pipeline Performance Dashboard
- Database & Cache Metrics Dashboard
- Error & Alert Dashboard

**To add custom dashboard:**

1. Click "+" → "Dashboard"
2. Add panels with Prometheus queries
3. Example panel query:
   ```
   histogram_quantile(0.95, rate(rag_generation_time_seconds_bucket[5m]))
   ```
4. Save dashboard

### 3. Application Metrics Endpoint

Direct access: http://localhost:8000/metrics

Returns metrics in Prometheus text format:
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{endpoint="/api/search",method="POST",status="200"} 1523.0
```

## Alert Configuration

### Viewing Active Alerts

In Prometheus: http://localhost:9090/alerts

### Alert Rules

Key alerts (from `alert_rules.yml`):

| Alert | Threshold | Action |
|-------|-----------|--------|
| ApplicationDown | down > 1m | Check app logs, restart |
| HighErrorRate | > 5% for 5m | Review error logs |
| HighResponseTime | p95 > 2s for 5m | Check database, LLM |
| SlowRetrieval | p95 > 5s for 5m | Optimize retrieval |
| HighHallucinationRate | > 10% for 5m | Review LLM settings |
| LowConfidenceScore | < 60% for 5m | Improve context |

### Configuring AlertManager

To enable email/Slack notifications (optional):

1. Install AlertManager:
```bash
docker pull prom/alertmanager:latest
```

2. Create `alertmanager.yml`:
```yaml
global:
  resolve_timeout: 5m

route:
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'

receivers:
  - name: 'default'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
```

3. Start AlertManager:
```bash
docker run -d \
  -v alertmanager.yml:/etc/alertmanager/alertmanager.yml \
  -p 9093:9093 \
  prom/alertmanager
```

## Logging Stack (Optional)

### Elasticsearch + Kibana Setup

```bash
# Start logging stack
docker-compose --profile logging up -d

# Kibana: http://localhost:5601
# Elasticsearch: http://localhost:9200
```

**Create index pattern in Kibana:**
1. Visit: http://localhost:5601
2. Management → Index Patterns
3. Create new pattern: `logs-*`
4. Time field: `@timestamp`

## Performance Monitoring

### Key Metrics to Watch

1. **Query Performance**
   - p95 latency: should be < 2s
   - p99 latency: should be < 5s
   - Error rate: should be < 1%

2. **RAG Pipeline**
   - Retrieval time: 0.1-5s (depending on query complexity)
   - Generation time: 0.5-10s (depends on prompt size)
   - Hallucination rate: < 5% (should be maintained)

3. **System Resources**
   - DB connections: < 15 active
   - Cache hit ratio: > 70%
   - Memory usage: monitor for leaks

### Custom Metrics in Code

To add custom metrics:

```python
from src.api.middleware import (
    set_hallucination_score,
    set_confidence_score,
    record_document_operation,
    record_chunk_generation
)

# Record metrics
set_hallucination_score(0.03)      # 3% hallucination
set_confidence_score(0.92)         # 92% confidence
record_document_operation('ingestion', 5)  # Added 5 docs
record_chunk_generation(250)       # Generated 250 chunks
```

## Production Monitoring Checklist

- [ ] Prometheus scrape interval: 10s
- [ ] Retention period: 15+ days
- [ ] Alert rules enabled and tested
- [ ] AlertManager configured for notifications
- [ ] Grafana dashboards created and shared
- [ ] Elasticsearch retention: 30+ days
- [ ] Regular backup of monitoring data
- [ ] Monitoring dashboards reviewed daily
- [ ] Alert thresholds tuned to your environment
- [ ] SLA monitoring in place

## Troubleshooting

### Prometheus not scraping metrics

1. Check if app is running and /metrics endpoint is accessible
2. Verify prometheus.yml configuration
3. Check Prometheus logs: `docker-compose logs prometheus`

### Grafana dashboards empty

1. Verify Prometheus data source is connected
2. Check if Prometheus has collected metrics
3. Ensure query time range is recent

### High memory usage in Prometheus

1. Reduce retention period in prometheus.yml
2. Increase scrape interval
3. Add metric relabeling to drop unused metrics

### Missing logs in Kibana

1. Verify Elasticsearch is running
2. Check if app is sending logs to Elasticsearch
3. Create proper index pattern

## Best Practices

1. **Alert Fatigue**: Only alert on actionable conditions
2. **Retention**: Balance storage vs cost (15-30 days recommended)
3. **Granularity**: Use labels appropriately for filtering
4. **Testing**: Test alerts before going to production
5. **Documentation**: Document custom metrics and alerts
6. **Backups**: Regular backups of monitoring configuration
7. **Review**: Quarterly review of alerts and dashboards

## Additional Resources

- Prometheus docs: https://prometheus.io/docs/
- Grafana docs: https://grafana.com/docs/
- PromQL guide: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Alerting guide: https://prometheus.io/docs/alerting/latest/overview/
