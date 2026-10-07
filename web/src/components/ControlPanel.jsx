import React from 'react';
import { Crosshair, ShieldCheck, Zap, Bot, ArrowRightLeft, ShieldAlert } from 'lucide-react';

export default function ControlPanel({ settings, onUpdateSettings }) {
  const currentProfile = settings?.profile || 'tatico';
  const activeMode = settings?.active_symbol_mode || 'BOTH';

  const handleToggle = (field) => {
    onUpdateSettings({ [field]: !settings?.[field] });
  };

  return (
    <div className="space-y-4">
      {/* 1. ATIVOS A OPERAR */}
      <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4">
        <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 block mb-2.5">
          1. Target Assets
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
              {mode === 'BOTH' ? 'BOTH' : mode === 'US100' ? 'NASDAQ' : 'GOLD (XAU)'}
            </button>
          ))}
        </div>
      </div>

      {/* 2. LIMITES FINANCEIROS */}
      <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4 space-y-3">
        <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 block">
          2. Risk Limits (Prop Firm Shield)
        </label>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <span className="text-[10px] text-zinc-500 font-mono block mb-1">Risk / Trade ($)</span>
            <input
              type="number"
              defaultValue={settings?.risk_per_trade || 50}
              onBlur={(e) => onUpdateSettings({ risk_per_trade: Number(e.target.value) })}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-2.5 text-xs font-mono font-bold text-zinc-100 focus:outline-none focus:border-violet-500"
            />
          </div>
          <div>
            <span className="text-[10px] text-zinc-500 font-mono block mb-1">Daily Max Loss ($)</span>
            <input
              type="number"
              defaultValue={settings?.max_daily_loss || 500}
              onBlur={(e) => onUpdateSettings({ max_daily_loss: Number(e.target.value) })}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-2.5 text-xs font-mono font-bold text-rose-400 focus:outline-none focus:border-rose-500"
            />
          </div>
        </div>
      </div>

      {/* 3. SELEÇÃO DE PERFIL */}
      <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4">
        <div className="flex items-center justify-between mb-2.5">
          <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400">
            3. Execution Profile (R:R)
          </label>
          {settings?.auto_profile_ia && (
            <span className="text-[9px] bg-violet-500/20 text-violet-300 border border-violet-500/30 px-1.5 py-0.5 rounded font-mono font-bold">
              AI MANAGED
            </span>
          )}
        </div>

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
            <span className="text-[10px] font-bold font-mono">TACTICAL (1:2.5)</span>
          </button>

          <button
            onClick={() => onUpdateSettings({ profile: 'guardiao' })}
            className={`p-3 rounded-xl border flex flex-col items-center gap-1 transition-all ${
              currentProfile === 'guardiao'
                ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                : 'bg-zinc-950 border-zinc-800 text-zinc-400'
            }`}>
            <ShieldCheck size={16} />
            <span className="text-[10px] font-bold font-mono">GUARDIAN</span>
          </button>
        </div>
      </div>

      {/* 4. OS TOGGLES DE AUTOMAÇÃO */}
      <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4 space-y-3">
        <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 block mb-1">
          4. Smart Toggles
        </label>

        {/* AI Auto-Adapt */}
        <div className="flex items-center justify-between py-1.5 border-b border-zinc-800/60">
          <div>
            <div className="flex items-center gap-1.5">
              <Bot size={14} className="text-violet-400" />
              <strong className="text-xs text-zinc-200">AI Auto-Adapt Profile</strong>
            </div>
            <span className="text-[10px] text-zinc-500 block">
              Groq switches profile automatically based on 5-day backtest & volatility
            </span>
          </div>
          <input
            type="checkbox"
            checked={!!settings?.auto_profile_ia}
            onChange={() => handleToggle('auto_profile_ia')}
            className="w-5 h-5 accent-violet-600 rounded cursor-pointer"
          />
        </div>

        {/* Break-even */}
        <div className="flex items-center justify-between py-1.5 border-b border-zinc-800/60">
          <div>
            <strong className="text-xs text-zinc-200 block">Auto Break-Even</strong>
            <span className="text-[10px] text-zinc-500 block">Move SL to Entry Price at 1:1 R:R</span>
          </div>
          <input
            type="checkbox"
            checked={!!settings?.breakeven_enabled}
            onChange={() => handleToggle('breakeven_enabled')}
            className="w-5 h-5 accent-emerald-600 rounded cursor-pointer"
          />
        </div>

        {/* Trailing Stop */}
        <div className="flex items-center justify-between py-1.5 border-b border-zinc-800/60">
          <div>
            <strong className="text-xs text-zinc-200 block">Trailing Stop (M1)</strong>
            <span className="text-[10px] text-zinc-500 block">Trail candle-by-candle once in profit</span>
          </div>
          <input
            type="checkbox"
            checked={!!settings?.trailing_enabled}
            onChange={() => handleToggle('trailing_enabled')}
            className="w-5 h-5 accent-blue-600 rounded cursor-pointer"
          />
        </div>

        {/* Parciais */}
        <div className="flex items-center justify-between py-1.5">
          <div>
            <strong className="text-xs text-zinc-200 block">Partial Take Profit</strong>
            <span className="text-[10px] text-zinc-500 block">Close 50% of volume at 1.5R target</span>
          </div>
          <input
            type="checkbox"
            checked={!!settings?.partial_enabled}
            onChange={() => handleToggle('partial_enabled')}
            className="w-5 h-5 accent-amber-600 rounded cursor-pointer"
          />
        </div>
      </div>
    </div>
  );
}