/**
 * ChatHeader Component:
 * Displays the current status of the connection and the session identifier.
 */
// EDUCATIONAL NOTE: This Component Displays Status but Never Determines It
// Connection state is owned by App.tsx (which polls the backend) and flows
// down as a prop. If the header probed /health itself, three components could
// disagree about whether Nexus is "Online" at the same instant — the classic
// multiple-sources-of-truth bug. Typing status as the union 'Online'|'Offline'
// instead of string completes the contract: the compiler rejects a typo like
// 'online' at the call site, so the status-dot ternary below can safely treat
// "not Online" as Offline without a defensive else-if chain.
interface ChatHeaderProps {
  /**
   * Status can only be 'Online' or 'Offline'. 
   * This is more specific and safer than just using a generic 'string'.
   */
  status: 'Online' | 'Offline'
  sessionId: string
}

export function ChatHeader({ status, sessionId }: ChatHeaderProps) {
  return (
    <div className="p-5 border-b border-slate-700/50 [background:rgba(15,23,42,0.8)] flex items-center justify-between backdrop-blur-md">
      <h3 className="font-bold flex items-center gap-3 text-lg">
        {/* 
          Template Literals (` `): 
          Used here to dynamically generate CSS class names.
          If status is 'Online', we add 'bg-emerald-500' and 'animate-pulse'.
          Otherwise, we use 'bg-rose-500' (red).
        */}
        <span className={`w-3 h-3 rounded-full ${status === 'Online' ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`}></span>
        Live Session
      </h3>
      
      {/* 
        Curly braces {} are used to embed JavaScript expressions 
        directly into our JSX (HTML-like) code. 
      */}
      <span className="text-xs text-slate-400 font-mono [background:rgb(30,41,59)] px-2 py-1 rounded">
        {sessionId}
      </span>
    </div>
  )
}
