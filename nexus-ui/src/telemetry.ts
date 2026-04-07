import 'zone.js';
import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';
import { registerInstrumentations } from '@opentelemetry/instrumentation';
import { ZoneContextManager } from '@opentelemetry/context-zone';
import { W3CTraceContextPropagator } from '@opentelemetry/core';
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch';
import { DocumentLoadInstrumentation } from '@opentelemetry/instrumentation-document-load';
import { MeterProvider, PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-http';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';

// EDUCATIONAL NOTE: Unified Frontend Observability
// [Why] We instrument both Traces (Tempo) and Metrics (Prometheus).
// Traces show the 'How' (request flow), while Metrics show the 'How Many' 
// (interaction counts, load times).

const resource = new Resource({
  [SemanticResourceAttributes.SERVICE_NAME]: 'nexus-ui',
});
const traceExporter = new OTLPTraceExporter({
  url: 'http://localhost:4319/v1/traces',
});

const tracerProvider = new WebTracerProvider({
  resource: resource,
  spanProcessors: [
    new BatchSpanProcessor(traceExporter)
  ]
});

tracerProvider.register({
  contextManager: new ZoneContextManager(),
  propagator: new W3CTraceContextPropagator(),
});

// ----------------------------------------------------------------------
// 2. METRICS (Prometheus)
// ----------------------------------------------------------------------
const metricExporter = new OTLPMetricExporter({
  url: 'http://localhost:4319/v1/metrics',
});

const meterProvider = new MeterProvider({
  resource: resource,
  readers: [
    new PeriodicExportingMetricReader({
      exporter: metricExporter,
      exportIntervalMillis: 5000,
    }),
  ],
});

export const meter = meterProvider.getMeter('nexus-ui-meter');

// ----------------------------------------------------------------------
// 3. INSTRUMENTATION
// ----------------------------------------------------------------------
registerInstrumentations({
  instrumentations: [
    new DocumentLoadInstrumentation(),
    new FetchInstrumentation({
      propagateTraceHeaderCorsUrls: [
        /http:\/\/localhost:8080\.*/,
      ],
    }),
  ],
});
