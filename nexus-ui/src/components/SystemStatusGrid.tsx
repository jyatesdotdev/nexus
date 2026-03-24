import type { ServiceStatus } from '../types'
import { Card, Badge } from './ui'

/**
 * SystemStatusGrid Component:
 * HOW: Displays the health of the backend services in a responsive grid.
 */
interface SystemStatusProps {
  status: ServiceStatus
}

export function SystemStatusGrid({ status }: SystemStatusProps) {
  /**
   * Helper Function:
   * WHY: Instead of repeating the logic for checking if a service is 'Online', 
   * 'Connected', or 'Reachable', we wrap it in a single function for consistency.
   */
  const isOnline = (val: string) => ['Online', 'Connected', 'Reachable'].includes(val)

  /**
   * Data Mapping:
   * We define an array of services and then map over it to avoid 
   * duplicating the JSX (HTML-like code) for each card.
   */
  const services = [
    { 
      id: 'orchestrator', 
      label: 'Orchestrator', 
      port: '8080',
      subStatus: null
    },
    { 
      id: 'mcp_server', 
      label: 'MCP Server', 
      port: '8000',
      subStatus: { label: 'Database', val: status.mcp_db }
    },
    { 
      id: 'a2a_agent', 
      label: 'A2A Agent', 
      port: '8001',
      subStatus: { label: 'Weather API', val: status.a2a_api }
    },
  ]

  return (
    <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {services.map((s) => (
        <Card key={s.label} className="p-5 flex flex-col justify-between bg-white dark:bg-neutral-900/50 gap-4 hover:shadow-md transition-all">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] text-neutral-400 uppercase tracking-widest font-black mb-1.5">{s.label}</p>
              <p className="text-sm font-mono text-neutral-500 dark:text-neutral-400 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-neutral-300 dark:bg-neutral-700"></span>
                Port {s.port}
              </p>
            </div>
            
            {/* 
              Type Casting (as keyof ServiceStatus):
              WHY: TypeScript needs to be sure that the string 's.id' 
              is actually one of the valid keys of the ServiceStatus interface.
            */}
            <Badge variant={isOnline(status[s.id as keyof ServiceStatus]) ? 'success' : 'error'}>
              {status[s.id as keyof ServiceStatus]}
            </Badge>
          </div>

          {/* 
            Sub-status section:
            Only renders if the service has a 'subStatus' object (e.g., Database status for the MCP server).
          */}
          {s.subStatus && (
            <div className="flex items-center justify-between pt-3 border-t border-neutral-100 dark:border-neutral-800">
              <span className="text-[10px] text-neutral-400 font-bold uppercase tracking-tighter">{s.subStatus.label}</span>
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-bold ${isOnline(s.subStatus.val) ? 'text-emerald-600 dark:text-emerald-500' : 'text-rose-600'}`}>
                  {s.subStatus.val}
                </span>
                <div className={`w-1.5 h-1.5 rounded-full ${isOnline(s.subStatus.val) ? 'bg-emerald-500' : 'bg-rose-500'}`}></div>
              </div>
            </div>
          )}
        </Card>
      ))}
    </section>
  )
}
