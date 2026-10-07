import React from 'react';
import { Activity, ShieldAlert, DollarSign, Power, Sparkles, TrendingUp } from 'lucide-react';

export default function Dashboard({ status, settings, onEmergencyStop }) {
  const isOnline = status?.is_online;
  const pnl = Number(status?.pnl_today || 0);

  return (
    <div className="space-y-4">
      {/* CARD STATUS & PNL */}
      <div className="grid grid-cols-2 gap-3">
        {/* Status Robô */}
        <div className="bg-zinc-900/90 border border-zinc-800 p-4 rounded-2xl flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider">Notebook MT5</span>
            <span className={`w-2.5 h-2.5 rounded-full ${isOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
          </div>
          <div className="mt-2">
            <span className={`text-base font-bold ${isOnline ? 'text-emerald-400' : 'text-rose-400'}`}>
              {isOnline ? 'CONECTADO' : 'OFFLINE'}
            </span>
            <p className="text-[10px] text-zinc-500 font-mono mt-0.5">
              {status?.last_seen ? new Date(status.last_seen).toLocaleTimeString('pt-BR') : '--:--'}
            </p>
          </div>
        </div>

        {/* PNL Diário */}
        <div className="bg-zinc-900/90 border border-zinc-800 p-4 rounded-2xl flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider">PNL Hoje</span>
            <DollarSign size={14} className={pnl >= 0 ? "text-emerald-400" : "text-rose-400"} />
          </div>
          <div className="mt-2">
            <span className={`text-lg font-black font-mono ${pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {pnl >= 0 ? `+$${pnl.toFixed(2)}` : `-$${Math.abs(pnl).toFixed(2)}`}
            </span>
            <p className="text-[10px] text-zinc-500 font-mono mt-0.5">
              Limite: -${settings?.max_daily_loss || 200}
            </p>
          </div>
        </div>
      </div>

      {/* ATIVOS & PERFIL ATUAL */}
      <div className="bg-zinc-900/90 border border-zinc-800 p-4 rounded-2xl flex items-center justify-between">
        <div>
          <span className="text-[10px] font-mono uppercase tracking-widest text-zinc-400 block">Vigilância Ativa</span>
          <strong className="text-sm font-bold text-zinc-100 font-mono">NASDAQ (US100) • OURO (XAU)</strong>
        </div>
        <div className="text-right">
          <span className="text-[10px] font-mono uppercase tracking-widest text-zinc-400 block">Perfil Ativo</span>
          <span className="text-xs px-2.5 py-0.5 rounded-full font-bold uppercase font-mono bg-violet-500/10 text-violet-400 border border-violet-500/30">
            {status?.current_profile || 'TÁTICO'}
          </span>
        </div>
      </div>

      {/* SHADOW TRADING PREVIEW (Relatório Matinal / Fim de Dia) */}
      <div className="bg-gradient-to-br from-zinc-900 to-zinc-950 border border-zinc-800/80 p-4 rounded-2xl">
        <div className="flex items-center gap-2 mb-2">
          <Sparkles size={15} className="text-amber-400" />
          <h4 className="text-xs font-bold text-zinc-200 uppercase tracking-wider">Shadow Trading (Sessão)</h4>
        </div>
        <p className="text-[11px] text-zinc-400 leading-relaxed">
          Simulando os outros 2 perfis em segundo plano. O relatório de fechamento de mercado indicará qual perfil teria tido o melhor desempenho hoje.
        </p>
      </div>

      {/* BOTÃO DE PÂNICO */}
      <button
        onClick={onEmergencyStop}
        className="w-full py-3 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 text-rose-300 rounded-xl text-xs font-bold font-mono uppercase tracking-wider flex items-center justify-center gap-2 transition-all active:scale-[0.98]">
        <Power size={14} /> Trava de Emergência (Zerar Tudo)
      </button>
    </div>
  );
}