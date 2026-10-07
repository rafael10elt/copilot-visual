import React from 'react';
import { ShieldCheck, DollarSign, Power, Sparkles, UserCheck } from 'lucide-react';

export default function Dashboard({ status, settings, onEmergencyStop }) {
  const isOnline = status?.is_online;
  const pnl = Number(status?.pnl_today || 0);

  return (
    <div className="space-y-3.5">
      {/* CARD DA CONTA FTMO */}
      <div className="bg-zinc-900/90 border border-zinc-800 p-4 rounded-2xl flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-violet-500/10 border border-violet-500/20 text-violet-400">
            <UserCheck size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-zinc-200 font-mono">FTMO #{status?.account_login || '1514861405'}</span>
              <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
            </div>
            <p className="text-[10px] text-zinc-500 font-mono">{status?.broker || 'FTMO-Demo'} • {isOnline ? 'ONLINE' : 'OFFLINE'}</p>
          </div>
        </div>
        <div className="text-right">
          <span className="text-[10px] text-zinc-500 font-mono block">PATRIMÔNIO (EQUITY)</span>
          <strong className="text-sm font-black text-zinc-100 font-mono">${status?.account_equity || '0.00'}</strong>
        </div>
      </div>

      {/* PLACAR PNL HOJE & SALDO */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-zinc-900/90 border border-zinc-800 p-3.5 rounded-2xl">
          <span className="text-[10px] font-mono text-zinc-500 uppercase block">Saldo da Conta</span>
          <strong className="text-base font-bold text-zinc-200 font-mono block mt-1">
            ${status?.account_balance || '0.00'}
          </strong>
        </div>

        <div className="bg-zinc-900/90 border border-zinc-800 p-3.5 rounded-2xl">
          <span className="text-[10px] font-mono text-zinc-500 uppercase block">PNL da Sessão</span>
          <strong className={`text-base font-black font-mono block mt-1 ${pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {pnl >= 0 ? `+$${pnl.toFixed(2)}` : `-$${Math.abs(pnl).toFixed(2)}`}
          </strong>
        </div>
      </div>

      {/* SHADOW TRADING & EMERGÊNCIA */}
      <div className="bg-gradient-to-br from-zinc-900 to-zinc-950 border border-zinc-800/80 p-3.5 rounded-2xl">
        <div className="flex items-center gap-2 mb-1.5">
          <Sparkles size={15} className="text-amber-400" />
          <h4 className="text-xs font-bold text-zinc-200 uppercase font-mono">Shadow Trading</h4>
        </div>
        <p className="text-[11px] text-zinc-400 leading-relaxed font-sans">
          Simulando os perfis não utilizados. No final da sessão você verá qual teria gerado o melhor lucro.
        </p>
      </div>

      <button
        onClick={onEmergencyStop}
        className="w-full py-3 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 text-rose-300 rounded-xl text-xs font-bold font-mono uppercase tracking-wider flex items-center justify-center gap-2 transition-all">
        <Power size={14} /> Trava de Emergência (Zerar)
      </button>
    </div>
  );
}