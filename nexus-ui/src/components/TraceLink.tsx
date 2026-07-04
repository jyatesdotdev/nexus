import { Activity } from 'lucide-react'
import { cn } from '../lib/utils'
import { buildTraceUrl, shortTraceId } from '../lib/trace'

/**
 * EDUCATIONAL NOTE: Trace Visibility (Observability UX)
 * WHY: Every agent reply is the tip of a distributed workflow — the
 * orchestrator may have called sub-agents over MCP and A2A. This small chip
 * exposes that hidden machinery: it deep-links the message's OTel trace id
 * to Grafana Tempo, where the full span tree across services is visible.
 * HOW: A plain anchor styled as an unobtrusive chip. It opens in a new tab
 * (target="_blank" with rel="noopener noreferrer" to sever the window
 * reference for security) and shows only a short prefix of the 32-char hex
 * id, like a git short hash.
 */
interface TraceLinkProps {
  /** OpenTelemetry trace id (32-char hex) from the X-Trace-Id header. */
  traceId: string
  className?: string
}

export function TraceLink({ traceId, className }: TraceLinkProps) {
  return (
    <a
      href={buildTraceUrl(traceId)}
      target="_blank"
      rel="noopener noreferrer"
      title={`View trace ${traceId} in Grafana Tempo`}
      className={cn(
        'mt-2 inline-flex w-fit items-center gap-1 rounded-full border border-slate-600/60 bg-slate-900/40 px-2 py-0.5',
        'font-mono text-[10px] text-slate-400 no-underline transition-colors',
        'hover:border-indigo-400/60 hover:text-indigo-300',
        className
      )}
    >
      <Activity className="w-3 h-3" aria-hidden="true" />
      trace {shortTraceId(traceId)}
    </a>
  )
}
