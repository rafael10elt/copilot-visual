import React from 'react';
import { Crosshair, ShieldCheck, Zap, Bot } from 'lucide-react';

export default function ControlPanel({ settings, onUpdateSettings }) {
  const currentProfile = settings?.profile || 'tatico';
  const activeMode = settings?.active_symbol_mode || 'BOTH';

  return (
    <div className="space-y-4">
      {/* 1. SELETOR DE ATIVOS */}
      <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4">
        <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 block mb-2.5">
          1. Ativos a Operar
        </label>
        <div className="grid grid-cols-3 gap-2">
          {['BOTH', 'US100', 'XAUUSD'].map((mode) => (
            <button
              key={mode}
              onClick={() => onUpdateSettings({ active_symbol_mode: mode })}
              className={`py-2 rounded-xl text-xs font-bold font-mono border transition-all ${
                activeMode === mode
                  ? 'bg-violet-500/10 border-violet-500/40 text-violet-300'
                  : 'bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700'
              }`}>
              {mode === 'BOTH' ? 'AMBOS' : mode === 'US100' ? 'NASDAQ' : 'OURO'}
            </button>
          ))}
        </div>
      </div>

      {/* 2. GESTÃO DE RISCO EM DINHEIRO ($) */}
      <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4 space-y-3">
        <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 block">
          2. Limites de Risco (Mesa Proprietária)
        </label>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <span className="text-[10px] text-zinc-500 font-mono block mb-1">Risco por Trade ($)</span>
            <input
              type="number"
              defaultValue={settings?.risk_per_trade || 50}
              onBlur={(e) => onUpdateSettings({ risk_per_trade: Number(e.target.value) })}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-2.5 text-xs font-mono font-bold text-zinc-100 focus:outline-none focus:border-violet-500"
            />
          </div>
          <div>
            <span className="text-[10px] text-zinc-500 font-mono block mb-1">Perda Máx. Diária ($)</span>
            <input
              type="number"
              defaultValue={settings?.max_daily_loss || 200}
              onBlur={(e) => onUpdateSettings({ max_daily_loss: Number(e.target.value) })}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-2.5 text-xs font-mono font-bold text-rose-400 focus:outline-none focus:border-rose-500"
            />
          </div>
        </div>
      </div>

      {/* 3. PERFIL DE RISCO */}
      <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4">
        <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 block mb-2.5">
          3. Perfil de R:R e Stop
        </label>
        <div className="grid grid-cols-3 gap-2">
          <button
            onClick={() => onUpdateSettings({ profile: 'sniper' })}
            className={`p-3 rounded-xl border flex flex-col items-center gap-1 transition-all ${
              currentProfile === 'sniper'
                ? 'bg-amber-500/10 border-amber-500/40 text-amber-300'
                : 'bg-zinc-950 border-zinc-800 text-zinc-400'
            }`}>
            <Crosshair size={16} />
            <span className="text-[10px] font-bold font-mono">SNIPER (1:4)</span>
          </button>

          <button
            onClick={() => onUpdateSettings({ profile: 'tatico' })}
            className={`p-3 rounded-xl border flex flex-col items-center gap-1 transition-all ${
              currentProfile === 'tatico'
                ? 'bg-blue-500/10 border-blue-500/40 text-blue-300'
                : 'bg-zinc-950 border-zinc-800 text-zinc-400'
            }`}>
            <Zap size={16} />
            <span className="text-[10px] font-bold font-mono">TÁTICO (1:2.5)</span>
          </button>

          <button
            onClick={() => onUpdateSettings({ profile: 'guardiao' })}
            className={`p-3 rounded-xl border flex flex-col items-center gap-1 transition-all ${
              currentProfile === 'guardiao'
                ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                : 'bg-zinc-950 border-zinc-800 text-zinc-400'
            }`}>
            <ShieldCheck size={16} />
            <span className="text-[10px] font-bold font-mono">GUARDIÃO</span>
          </button>
        </div>
      </div>
    </div>
  );
}