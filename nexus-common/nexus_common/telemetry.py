import logging
import os
import time
from collections.abc import Awaitable, Callable
from typing import Any

# EDUCATIONAL NOTE: Centralized Observability
# This shared module ensures that all microservices in the Nexus ecosystem
# use a consistent OpenTelemetry configuration, enabling seamless distributed
# tracing across the entire call graph.

def setup_telemetry(service_name: str, app: Any | None = None, app_type: str = "fastapi") -> None:
    """
    Initializes OpenTelemetry Tracing and Prometheus Metrics.
    """
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    
    # 1. Shared Resource Configuration
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    resource = Resource(attributes={SERVICE_NAME: service_name})

    try:
        # ----------------------------------------------------------------------
        # TRACING (OTLP to Jaeger/Tempo)
        # ----------------------------------------------------------------------
        if otlp_endpoint:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.propagate import set_global_textmap
            from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
            from opentelemetry.baggage.propagation import W3CBaggagePropagator
            from opentelemetry.propagators.composite import CompositePropagator

            # Configure global propagator to enable W3C Trace Context across boundaries
            set_global_textmap(CompositePropagator([TraceContextTextMapPropagator(), W3CBaggagePropagator()]))

            trace_provider = TracerProvider(resource=resource)
            span_processor = BatchSpanProcessor(OTLPSpanExporter())
            trace_provider.add_span_processor(span_processor)
            trace.set_tracer_provider(trace_provider)

        # ----------------------------------------------------------------------
        # METRICS (Prometheus)
        # ----------------------------------------------------------------------
        # EDUCATIONAL NOTE: [Why] We use prometheus_client directly for maximum reliability and 
        # explicit control over metric registration in this educational lab.
        from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry
        
        # Check for multi-process configuration
        # EDUCATIONAL NOTE: Multi-Process Metrics
        # [Why] In production (like Gunicorn with multiple workers), each worker process 
        # normally keeps its own isolated metrics. PROMETHEUS_MULTIPROC_DIR tells the 
        # prometheus_client to use a shared memory-mapped directory so metrics are 
        # correctly aggregated across all workers when the /metrics endpoint is scraped.
        multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
        if multiproc_dir:
            from prometheus_client import multiprocess
            registry = CollectorRegistry()
            # prometheus_client.multiprocess ships no annotations upstream.
            multiprocess.MultiProcessCollector(registry)  # type: ignore[no-untyped-call]
            
            def get_metrics_data() -> bytes:
                return generate_latest(registry)
        else:
            def get_metrics_data() -> bytes:
                return generate_latest()
        
        # Define standard metrics for all services
        REQUEST_COUNT = Counter(
            "nexus_http_requests_total", 
            "Total HTTP requests", 
            ["method", "endpoint", "status", "service"]
        )
        REQUEST_LATENCY = Histogram(
            "nexus_http_request_duration_seconds", 
            "HTTP request latency", 
            ["method", "endpoint", "service"]
        )

        # ----------------------------------------------------------------------
        # INSTRUMENTATION
        # ----------------------------------------------------------------------
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        HTTPXClientInstrumentor().instrument()

        if app:
            if app_type == "fastapi":
                # Imported from starlette (not fastapi): fastapi.Request/Response
                # ARE starlette's classes re-exported, and starlette is present in
                # every consumer's environment — while fastapi is only installed
                # by the orchestrator. This keeps strict mypy runs in the
                # starlette-only services (mcp, a2a) able to follow this module.
                from starlette.requests import Request
                from starlette.responses import Response

                # `app` is deliberately Any (this helper serves FastAPI and
                # Starlette apps alike), so its decorators are untyped to mypy.
                @app.middleware("http")  # type: ignore[untyped-decorator]
                async def prometheus_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
                    start_time = time.time()
                    response = await call_next(request)
                    duration = time.time() - start_time
                    
                    endpoint = request.url.path
                    method = request.method
                    status = str(response.status_code)
                    
                    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status, service=service_name).inc()
                    REQUEST_LATENCY.labels(method=method, endpoint=endpoint, service=service_name).observe(duration)
                    
                    return response

                @app.get("/metrics")  # type: ignore[untyped-decorator]
                async def metrics() -> Response:
                    return Response(content=get_metrics_data(), media_type=CONTENT_TYPE_LATEST)
                
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
                FastAPIInstrumentor.instrument_app(app)
                
            elif app_type == "starlette":
                # EDUCATIONAL NOTE: Starlette Middleware & Streaming
                # [Why] We use a standard ASGI middleware pattern here instead of 
                # BaseHTTPMiddleware to avoid issues with streaming responses (like SSE).
                from starlette.responses import Response
                
                class MetricsMiddleware:
                    def __init__(self, app: Any):
                        self.app = app

                    async def __call__(self, scope: dict[str, Any], receive: Callable[[], Awaitable[Any]], send: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
                        if scope["type"] != "http":
                            await self.app(scope, receive, send)
                            return

                        start_time = time.time()
                        status_code = 200

                        async def wrapped_send(message: dict[str, Any]) -> None:
                            nonlocal status_code
                            if message["type"] == "http.response.start":
                                status_code = message["status"]
                            await send(message)

                        await self.app(scope, receive, wrapped_send)
                        
                        duration = time.time() - start_time
                        endpoint = scope.get("path", "")
                        method = scope.get("method", "")
                        
                        # Only record if it's a real request (not /metrics or /health)
                        if endpoint not in ["/metrics", "/health"]:
                            REQUEST_COUNT.labels(
                                method=method, 
                                endpoint=endpoint, 
                                status=str(status_code), 
                                service=service_name
                            ).inc()
                            REQUEST_LATENCY.labels(
                                method=method, 
                                endpoint=endpoint, 
                                service=service_name
                            ).observe(duration)

                app.add_middleware(MetricsMiddleware)
                
                async def metrics_route(request: Any) -> Response:
                    return Response(content=get_metrics_data(), media_type=CONTENT_TYPE_LATEST)
                
                app.add_route("/metrics", metrics_route, methods=["GET"])
                
                from opentelemetry.instrumentation.starlette import StarletteInstrumentor
                StarletteInstrumentor.instrument_app(app)

        logging.info(f"Nexus Shared Telemetry (Traces & Metrics) initialized for {service_name}")
    except ImportError as e:
        logging.warning(f"OpenTelemetry packages not found for {service_name}: {e}. Skipping instrumentation.")
    except Exception as e:
        logging.error(f"Failed to initialize telemetry for {service_name}: {e}")
