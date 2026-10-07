import React, { useState } from 'react';
import { Crosshair, ShieldCheck, Zap, Bot, Sliders, Layers, Target, Clock, Cpu } from 'lucide-react';

export default function ControlPanel({ settings, onUpdateSettings }) {
  const [selectedAssetTab, setSelectedAssetTab] = useState('nasdaq');

  const activeMode = settings?.active_symbol_mode || 'BOTH';

  // Configurações independentes por ativo com fallbacks seguros
  const nasdaqCfg = settings?.nasdaq || {
    auto_ia: !!settings?.auto_profile_ia,
    profile: settings?.profile || 'guardiao',
    use_ce_50: settings?.use_ce_50 !== false,
    require_sweep: !!settings?.require_sweep
  };

  const goldCfg = settings?.gold || {
    auto_ia: !!settings?.auto_profile_ia,
    profile: settings?.profile || 'tatico',
    use_ce_50: settings?.use_ce_50 !== false,
    require_sweep: !!settings?.require_sweep
  };

  const handleUpdateAssetField = (assetKey, field, value) => {
    const currentAssetConfig = assetKey === 'nasdaq' ? nasdaqCfg : goldCfg;
    const updated = {
      ...currentAssetConfig,
      [field]: value
    };
    onUpdateSettings({ [assetKey]: updated });
  };

  const handleToggleGlobal = (field) => {
    onUpdateSettings({ [field]: !settings?.[field] });
  };

  const currentCfg = selectedAssetTab === 'nasdaq' ? nasdaqCfg : goldCfg;

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

      {/* 2. LIMITES FINANCEIROS & METAS DA MESA */}
      <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4 space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 block">
            2. Risk & Prop Firm Targets
          </label>
          <span className="text-[9px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded font-mono font-bold">
            CHALLENGE RULES
          </span>
        </div>

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

        <div className="grid grid-cols-2 gap-3 pt-1 border-t border-zinc-800/60">
          <div>
            <span className="text-[10px] text-emerald-400 font-mono font-bold block mb-1">
              Meta de Lucro da Mesa ($)
            </span>
            <input
              type="number"
              defaultValue={settings?.prop_target_profit || 8000}
              onBlur={(e) => onUpdateSettings({ prop_target_profit: Number(e.target.value) })}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-2.5 text-xs font-mono font-bold text-emerald-300 focus:outline-none focus:border-emerald-500"
            />
          </div>
          <div>
            <span className="text-[10px] text-zinc-400 font-mono block mb-1">
              Saldo da Conta ($)
            </span>
            <input
              type="number"
              defaultValue={settings?.initial_account_size || 100000}
              onBlur={(e) => onUpdateSettings({ initial_account_size: Number(e.target.value) })}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-2.5 text-xs font-mono font-bold text-zinc-200 focus:outline-none focus:border-violet-500"
            />
          </div>
        </div>
      </div>

      {/* 3. CONTROLE HÍBRIDO INDEPENDENTE POR ATIVO */}
      <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4 space-y-3.5">
        <div className="flex items-center justify-between">
          <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 block">
            3. Asset Strategy Engine
          </label>
          <span className="text-[9px] bg-violet-500/10 text-violet-300 border border-violet-500/20 px-1.5 py-0.5 rounded font-mono font-bold">
            HÍBRIDO / INDEPENDENTE
          </span>
        </div>

        {/* Abas de Seleção de Ativo */}
        <div className="grid grid-cols-2 gap-1.5 bg-zinc-950 p-1 rounded-xl border border-zinc-800 text-xs font-mono font-bold">
          <button
            onClick={() => setSelectedAssetTab('nasdaq')}
            className={`py-2 rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              selectedAssetTab === 'nasdaq'
                ? 'bg-zinc-800 text-violet-300 shadow'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}>
            NASDAQ (US100)
            {nasdaqCfg.auto_ia && <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />}
          </button>
          <button
            onClick={() => setSelectedAssetTab('gold')}
            className={`py-2 rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              selectedAssetTab === 'gold'
                ? 'bg-zinc-800 text-amber-300 shadow'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}>
            GOLD (XAUUSD)
            {goldCfg.auto_ia && <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />}
          </button>
        </div>

        {/* Toggle Modo do Ativo (AUTO IA 30D vs MANUAL) */}
        <div className="bg-zinc-950/70 p-3 rounded-xl border border-zinc-800/80 space-y-2">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5">
                <Bot size={14} className={currentCfg.auto_ia ? "text-violet-400" : "text-zinc-500"} />
                <strong className="text-xs text-zinc-200">
                  Modo: {currentCfg.auto_ia ? 'AUTO IA (Base 30D)' : 'MANUAL'}
                </strong>
              </div>
              <span className="text-[10px] text-zinc-500 block mt-0.5">
                {currentCfg.auto_ia 
                  ? 'A IA analisa 30 dias de pregão e calibra o setup com maior Prop Score.'
                  : 'Você define o perfil e os parâmetros fixos para este ativo.'}
              </span>
            </div>

            <button
              onClick={() => handleUpdateAssetField(selectedAssetTab, 'auto_ia', !currentCfg.auto_ia)}
              className={`px-3 py-1.5 rounded-lg text-[10px] font-mono font-bold border transition-all ${
                currentCfg.auto_ia
                  ? 'bg-violet-500/20 text-violet-300 border-violet-500/40'
                  : 'bg-zinc-800 text-zinc-400 border-zinc-700'
              }`}>
              {currentCfg.auto_ia ? 'DESATIVAR IA' : 'ATIVAR IA (30D)'}
            </button>
          </div>
        </div>

        {/* Parâmetros do Ativo (Ativos no modo MANUAL, bloqueados visualmente no modo AUTO) */}
        <div className={`space-y-3 transition-opacity ${currentCfg.auto_ia ? 'opacity-40 pointer-events-none' : 'opacity-100'}`}>
          <div>
            <span className="text-[10px] text-zinc-400 font-mono block mb-1.5">
              Perfil de Execução ({selectedAssetTab === 'nasdaq' ? 'NASDAQ' : 'GOLD'}):
            </span>
            <div className="grid grid-cols-3 gap-2">
              <button
                onClick={() => handleUpdateAssetField(selectedAssetTab, 'profile', 'sniper')}
                className={`p-2.5 rounded-xl border flex flex-col items-center gap-1 transition-all ${
                  currentCfg.profile === 'sniper'
                    ? 'bg-amber-500/10 border-amber-500/40 text-amber-300'
                    : 'bg-zinc-950 border-zinc-800 text-zinc-400'
                }`}>
                <Crosshair size={14} />
                <span className="text-[9px] font-bold font-mono">SNIPER (1:4)</span>
              </button>

              <button
                onClick={() => handleUpdateAssetField(selectedAssetTab, 'profile', 'tatico')}
                className={`p-2.5 rounded-xl border flex flex-col items-center gap-1 transition-all ${
                  currentCfg.profile === 'tatico'
                    ? 'bg-blue-500/10 border-blue-500/40 text-blue-300'
                    : 'bg-zinc-950 border-zinc-800 text-zinc-400'
                }`}>
                <Zap size={14} />
                <span className="text-[9px] font-bold font-mono">TACTICAL (1:2.5)</span>
              </button>

              <button
                onClick={() => handleUpdateAssetField(selectedAssetTab, 'profile', 'guardiao')}
                className={`p-2.5 rounded-xl border flex flex-col items-center gap-1 transition-all ${
                  currentCfg.profile === 'guardiao'
                    ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                    : 'bg-zinc-950 border-zinc-800 text-zinc-400'
                }`}>
                <ShieldCheck size={14} />
                <span className="text-[9px] font-bold font-mono">GUARDIAN (1:1.5)</span>
              </button>
            </div>
          </div>

          <div>
            <span className="text-[10px] text-zinc-400 font-mono block mb-1.5">Ponto de Entrada FVG:</span>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleUpdateAssetField(selectedAssetTab, 'use_ce_50', true)}
                className={`py-1.5 rounded-xl text-[10px] font-mono font-bold border transition-all ${
                  currentCfg.use_ce_50 !== false
                    ? 'bg-violet-500/10 border-violet-500/40 text-violet-300'
                    : 'bg-zinc-950 border-zinc-800 text-zinc-500'
                }`}>
                50% (Consequent Encroachment)
              </button>
              <button
                onClick={() => handleUpdateAssetField(selectedAssetTab, 'use_ce_50', false)}
                className={`py-1.5 rounded-xl text-[10px] font-mono font-bold border transition-all ${
                  currentCfg.use_ce_50 === false
                    ? 'bg-violet-500/10 border-violet-500/40 text-violet-300'
                    : 'bg-zinc-950 border-zinc-800 text-zinc-500'
                }`}>
                Borda do FVG
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between py-1 border-t border-zinc-800/60">
            <div>
              <strong className="text-xs text-zinc-200 block">Exigir Liquidity Sweep</strong>
              <span className="text-[10px] text-zinc-500 block">Só entra após varredura recente</span>
            </div>
            <input
              type="checkbox"
              checked={!!currentCfg.require_sweep}
              onChange={(e) => handleUpdateAssetField(selectedAssetTab, 'require_sweep', e.target.checked)}
              className="w-5 h-5 accent-violet-600 rounded cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* 4. TOGGLES GLOBAIS DE EXECUÇÃO */}
      <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4 space-y-3">
        <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 block mb-1">
          4. Execution Guards (Globais)
        </label>

        <div className="flex items-center justify-between py-1.5 border-b border-zinc-800/60">
          <div>
            <strong className="text-xs text-zinc-200 block">Auto Break-Even (1.2R)</strong>
            <span className="text-[10px] text-zinc-500 block">Move SL para o ponto de entrada no lucro</span>
          </div>
          <input
            type="checkbox"
            checked={settings?.breakeven_enabled !== false}
            onChange={() => handleToggleGlobal('breakeven_enabled')}
            className="w-5 h-5 accent-emerald-600 rounded cursor-pointer"
          />
        </div>

        <div className="flex items-center justify-between py-1.5 border-b border-zinc-800/60">
          <div>
            <strong className="text-xs text-zinc-200 block">Trailing Stop (M1)</strong>
            <span className="text-[10px] text-zinc-500 block">Rastreia vela a vela após atingir 1.5R</span>
          </div>
          <input
            type="checkbox"
            checked={!!settings?.trailing_enabled}
            onChange={() => handleToggleGlobal('trailing_enabled')}
            className="w-5 h-5 accent-blue-600 rounded cursor-pointer"
          />
        </div>

        <div className="flex items-center justify-between py-1.5">
          <div>
            <strong className="text-xs text-zinc-200 block">Filtrar por Killzones</strong>
            <span className="text-[10px] text-zinc-500 block">Opera apenas nas janelas de Londres e NY em UTC</span>
          </div>
          <input
            type="checkbox"
            checked={settings?.use_session_filter !== false}
            onChange={() => handleToggleGlobal('use_session_filter')}
            className="w-5 h-5 accent-emerald-600 rounded cursor-pointer"
          />
        </div>
      </div>
    </div>
  );
}