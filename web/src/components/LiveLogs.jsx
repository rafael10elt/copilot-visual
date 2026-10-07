import React from 'react';
import { Terminal, Clock, ShieldAlert } from 'lucide-react';

export default function LiveLogs({ logs, onClear }) {
  const getBadgeStyle = (level) => {
    switch (level) {
      case 'SUCCESS':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'WARN':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'DANGER':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      default:
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    }
  };

  return (
    <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4">
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <Terminal size={15} className="text-zinc-400" />
          <h3 className="text-xs font-bold text-zinc-200 uppercase tracking-wider font-mono">
            Feed de Operações ({logs.length})
          </h3>
        </div>
        {logs.length > 0 && (
          <button
            onClick={onClear}
            className="text-[10px] font-mono text-zinc-500 hover:text-zinc-300 transition-colors">
            Limpar
          </button>
        )}
      </div>

      {logs.length === 0 ? (
        <div className="py-8 text-center text-zinc-500 text-xs font-mono">
          Nenhum evento registrado ainda.<br />Inicie o motor no notebook para ver o feed.
        </div>
      ) : (
        <div className="max-h-[380px] overflow-y-auto space-y-2 pr-1 font-mono text-[11px]">
          {logs.map((log) => (
            <div
              key={log.id}
              className="bg-zinc-950/70 border border-zinc-800/80 p-2.5 rounded-xl flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  {log.symbol && (
                    <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300">
                      {log.symbol}
                    </span>
                  )}
                  <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${getBadgeStyle(log.level)}`}>
                    {log.level}
                  </span>
                </div>
                <p className="text-zinc-200 break-words">{log.message}</p>
              </div>

              <span className="text-[9px] text-zinc-500 whitespace-nowrap mt-0.5">
                {new Date(log.created_at).toLocaleTimeString('pt-BR')}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}