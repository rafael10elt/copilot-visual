import React from 'react';
import { Crosshair, ShieldCheck, Zap, Bot, Check } from 'lucide-react';

export default function ControlPanel({ settings, onUpdateSettings }) {
  const currentProfile = settings?.profile || 'tatico';

  const handleProfileSelect = (p) => {
    onUpdateSettings({ profile: p });
  };

  const handleToggle = (key) => {
    onUpdateSettings({ [key]: !settings?.[key] });
  };

  return (
    <div className="space-y-4">
      {/* SELETOR DE PERFIL DE RISCO */}
      <div>
        <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 block mb-2">
          1. Perfil Operacional (R:R & Stops)
        </label>
        
        <div className="grid grid-cols-3 gap-2">
          {/* SNIPER */}
          <button
            onClick={() => handleProfileSelect('sniper')}
            className={`p-3 rounded-xl border flex flex-col items-center justify-center gap-1.5 transition-all ${
              currentProfile === 'sniper'
                ? 'bg-amber-500/10 border-amber-500/40 text-amber-300'
                : 'bg-zinc-900/60 border-zinc-800/80 text-zinc-400 hover:border-zinc-700'
            }`}>
            <Crosshair size={18} />
            <span className="text-[11px] font-bold font-mono">SNIPER</span>
            <span className="text-[9px] text-zinc-500 font-mono">1:4 R:R</span>
          </button>

          {/* TÁTICO */}
          <button
            onClick={() => handleProfileSelect('tatico')}
            className={`p-3 rounded-xl border flex flex-col items-center justify-center gap-1.5 transition-all ${
              currentProfile === 'tatico'
                ? 'bg-blue-500/10 border-blue-500/40 text-blue-300'
                : 'bg-zinc-900/60 border-zinc-800/80 text-zinc-400 hover:border-zinc-700'
            }`}>
            <Zap size={18} />
            <span className="text-[11px] font-bold font-mono">TÁTICO</span>
            <span className="text-[9px] text-zinc-500 font-mono">1:2.5 R:R</span>
          </button>

          {/* GUARDIÃO */}
          <button
            onClick={() => handleProfileSelect('guardiao')}
            className={`p-3 rounded-xl border flex flex-col items-center justify-center gap-1.5 transition-all ${
              currentProfile === 'guardiao'
                ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                : 'bg-zinc-900/60 border-zinc-800/80 text-zinc-400 hover:border-zinc-700'
            }`}>
            <ShieldCheck size={18} />
            <span className="text-[11px] font-bold font-mono">GUARDIÃO</span>
            <span className="text-[9px] text-zinc-500 font-mono">1:1.5 R:R</span>
          </button>
        </div>
      </div>

      {/* TOGGLES TÁTICOS */}
      <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4 space-y-3.5">
        <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 block">
          2. Automação & Gestão Ativa
        </label>

        {/* Toggle IA Auto-Adapt */}
        <div className="flex items-center justify-between py-1">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-violet-500/10 text-violet-400 border border-violet-500/20">
              <Bot size={16} />
            </div>
            <div>
              <strong className="text-xs text-zinc-100 block">IA Auto-Adapt</strong>
              <span className="text-[10px] text-zinc-500 block">Groq ajusta perfil conforme volatilidade</span>
            </div>
          </div>
          <input
            type="checkbox"
            checked={!!settings?.auto_profile_ia}
            onChange={() => handleToggle('auto_profile_ia')}
            className="w-5 h-5 accent-violet-600 rounded cursor-pointer"
          />
        </div>

        {/* Toggle Break-even */}
        <div className="flex items-center justify-between py-1 border-t border-zinc-800/60">
          <div>
            <strong className="text-xs text-zinc-100 block">Break-even Automático</strong>
            <span className="text-[10px] text-zinc-500 block">Move SL para o 0x0 ao andar 1R</span>
          </div>
          <input
            type="checkbox"
            checked={!!settings?.breakeven_enabled}
            onChange={() => handleToggle('breakeven_enabled')}
            className="w-5 h-5 accent-emerald-600 rounded cursor-pointer"
          />
        </div>

        {/* Toggle Trailing Stop */}
        <div className="flex items-center justify-between py-1 border-t border-zinc-800/60">
          <div>
            <strong className="text-xs text-zinc-100 block">Trailing Stop (M1)</strong>
            <span className="text-[10px] text-zinc-500 block">Enforca vela a vela protegendo o lucro</span>
          </div>
          <input
            type="checkbox"
            checked={!!settings?.trailing_enabled}
            onChange={() => handleToggle('trailing_enabled')}
            className="w-5 h-5 accent-blue-600 rounded cursor-pointer"
          />
        </div>
      </div>
    </div>
  );
}