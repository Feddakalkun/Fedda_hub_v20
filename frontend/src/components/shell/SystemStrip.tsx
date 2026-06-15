import { useEffect, useState } from 'react';
import { Activity, Cpu, ScrollText, Server } from 'lucide-react';
import { useComfyStatus } from '../../hooks/useComfyStatus';
import { useOllamaStatus } from '../../hooks/useOllamaStatus';
import { BACKEND_API } from '../../config/api';
import { clearUiLogs, getUiLogs, UI_LOG_EVENT, type UiLogEntry } from '../../services/uiLogger';
import { Button } from '../../ui/primitives';

export function SystemStrip() {
  const { isConnected: comfyOnline } = useComfyStatus(4000);
  const { isConnected: ollamaOnline } = useOllamaStatus();
  const [backendOnline, setBackendOnline] = useState(false);
  const [logsOpen, setLogsOpen] = useState(false);
  const [logs, setLogs] = useState<UiLogEntry[]>(getUiLogs());

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const response = await fetch(`${BACKEND_API.BASE_URL}/api/hardware/stats`, { cache: 'no-store' });
        if (!cancelled) setBackendOnline(response.ok);
      } catch {
        if (!cancelled) setBackendOnline(false);
      }
    };
    check();
    const timer = setInterval(check, 5000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    const refresh = () => setLogs(getUiLogs());
    window.addEventListener(UI_LOG_EVENT, refresh);
    return () => window.removeEventListener(UI_LOG_EVENT, refresh);
  }, []);

  return (
    <div className="fedda-system-strip">
      <div className="fedda-system-pills">
        <StatusPill icon={Server} label="ComfyUI" online={comfyOnline} />
        <StatusPill icon={Cpu} label="Backend" online={backendOnline} />
        <StatusPill icon={Activity} label="Ollama" online={ollamaOnline} />
      </div>
      <Button variant="ghost" onClick={() => setLogsOpen((open) => !open)}>
        <ScrollText size={14} />
        Logs
      </Button>
      {logsOpen && (
        <div className="fedda-log-panel">
          <div className="fedda-log-panel-header">
            <strong>UI Logs</strong>
            <Button
              variant="ghost"
              onClick={() => {
                clearUiLogs();
                setLogs([]);
              }}
            >
              Clear
            </Button>
          </div>
          <div className="fedda-log-list">
            {logs.length === 0 && <p className="fedda-log-empty">No UI logs yet.</p>}
            {logs.slice().reverse().map((entry) => (
              <div key={entry.id} className={`fedda-log-entry fedda-log-${entry.level}`}>
                <span>{new Date(entry.ts).toLocaleTimeString()}</span>
                <span>{entry.source}</span>
                <span>{entry.message}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatusPill({
  icon: Icon,
  label,
  online,
}: {
  icon: typeof Server;
  label: string;
  online: boolean;
}) {
  return (
    <span className={`fedda-status-pill ${online ? 'online' : 'offline'}`}>
      <Icon size={13} />
      {label}
      <span className="fedda-status-dot" />
    </span>
  );
}