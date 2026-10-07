import React from 'react';
import { Crosshair, ShieldCheck, Zap, Bot, Sliders, Layers, Target, Clock } from 'lucide-react';

export default function ControlPanel({ settings, onUpdateSettings }) {
  const currentProfile = settings?.profile || 'tatico';
  const activeMode = settings?.active_symbol_mode || 'BOTH';
  const isAutoAI = !!settings?.auto_profile_ia;

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
          {isAutoAI && (
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
            <span className="text-[10px] font-bold font-mono">GUARDIAN (1:1.5)</span>
          </button>
        </div>
      </div>

      {/* 4. CONFIGURAÇÃO MANUAL DE ESTRATÉGIA */}
      <div className={`bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4 space-y-3 transition-opacity ${
        isAutoAI ? 'opacity-50 pointer-events-none' : 'opacity-100'
      }`}>
        <div className="flex items-center justify-between">
          <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
            <Sliders size={13} className="text-amber-400" />
            4. Manual Strategy Parameters
          </label>
          {isAutoAI && (
            <span className="text-[9px] text-zinc-500 font-mono">Desative 'AI Auto-Adapt' para editar</span>
          )}
        </div>

        {/* Tipo de Entrada: 50% CE vs Borda */}
        <div>
          <span className="text-[10px] text-zinc-400 font-mono block mb-1.5">Ponto de Entrada FVG:</span>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => onUpdateSettings({ use_ce_50: true })}
              className={`py-1.5 rounded-xl text-[11px] font-mono font-bold border transition-all ${
                settings?.use_ce_50 !== false
                  ? 'bg-violet-500/10 border-violet-500/40 text-violet-300'
                  : 'bg-zinc-950 border-zinc-800 text-zinc-500'
              }`}>
              50% (Consequent Encroachment)
            </button>
            <button
              onClick={() => onUpdateSettings({ use_ce_50: false })}
              className={`py-1.5 rounded-xl text-[11px] font-mono font-bold border transition-all ${
                settings?.use_ce_50 === false
                  ? 'bg-violet-500/10 border-violet-500/40 text-violet-300'
                  : 'bg-zinc-950 border-zinc-800 text-zinc-500'
              }`}>
              Borda do FVG (Tradicional)
            </button>
          </div>
        </div>

        {/* Filtro de Liquidity Sweep */}
        <div className="flex items-center justify-between py-1 border-t border-zinc-800/60">
          <div>
            <strong className="text-xs text-zinc-200 block">Exigir Liquidity Sweep Prévio</strong>
            <span className="text-[10px] text-zinc-500 block">Só entra se varreu topo/fundo recente</span>
          </div>
          <input
            type="checkbox"
            checked={!!settings?.require_sweep}
            onChange={() => handleToggle('require_sweep')}
            className="w-5 h-5 accent-violet-600 rounded cursor-pointer"
          />
        </div>

        {/* Filtro de Sessões (Killzones) */}
        <div className="flex items-center justify-between py-1 border-t border-zinc-800/60">
          <div>
            <strong className="text-xs text-zinc-200 block">Filtrar por Killzones</strong>
            <span className="text-[10px] text-zinc-500 block">Opera apenas nas janelas de Londres e NY</span>
          </div>
          <input
            type="checkbox"
            checked={settings?.use_session_filter !== false}
            onChange={() => handleToggle('use_session_filter')}
            className="w-5 h-5 accent-emerald-600 rounded cursor-pointer"
          />
        </div>
      </div>

      {/* 5. TOGGLES DE AUTOMAÇÃO */}
      <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4 space-y-3">
        <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 block mb-1">
          5. Smart Toggles
        </label>

        {/* AI Auto-Adapt */}
        <div className="flex items-center justify-between py-1.5 border-b border-zinc-800/60">
          <div>
            <div className="flex items-center gap-1.5">
              <Bot size={14} className="text-violet-400" />
              <strong className="text-xs text-zinc-200">AI Auto-Adapt Profile</strong>
            </div>
            <span className="text-[10px] text-zinc-500 block">
              IA & Scout assumem perfil e parâmetros dinamicamente
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
            <strong className="text-xs text-zinc-200 block">Auto Break-Even (1.2R)</strong>
            <span className="text-[10px] text-zinc-500 block">Move SL para o ponto de entrada no lucro</span>
          </div>
          <input
            type="checkbox"
            checked={settings?.breakeven_enabled !== false}
            onChange={() => handleToggle('breakeven_enabled')}
            className="w-5 h-5 accent-emerald-600 rounded cursor-pointer"
          />
        </div>

        {/* Trailing Stop */}
        <div className="flex items-center justify-between py-1.5">
          <div>
            <strong className="text-xs text-zinc-200 block">Trailing Stop (M1)</strong>
            <span className="text-[10px] text-zinc-500 block">Rastreia vela a vela após atingir 1.5R</span>
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