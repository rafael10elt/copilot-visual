import React, { useState } from 'react';
import { Crosshair, ShieldCheck, Zap, Bot, Sliders, Target, Clock, ShieldAlert } from 'lucide-react';

export default function ControlPanel({ settings, onUpdateSettings }) {
  const [selectedAssetTab, setSelectedAssetTab] = useState('nasdaq');

  const activeMode = settings?.active_symbol_mode || 'BOTH';
  const isRawMode = !!settings?.raw_backtest_mode;

  const nasdaqCfg = settings?.nasdaq || {
    auto_ia: !!settings?.auto_profile_ia,
    profile: settings?.profile || 'guardiao',
    use_ce_50: settings?.use_ce_50 !== false,
    require_sweep: !!settings?.require_sweep,
    session_mode: 'KILLZONES'
  };

  const goldCfg = settings?.gold || {
    auto_ia: !!settings?.auto_profile_ia,
    profile: settings?.profile || 'tatico',
    use_ce_50: settings?.use_ce_50 !== false,
    require_sweep: !!settings?.require_sweep,
    session_mode: '24H'
  };

  const currentCfg = selectedAssetTab === 'nasdaq' ? nasdaqCfg : goldCfg;

  const handleUpdateAssetField = (assetKey, field, value) => {
    const baseConfig = assetKey === 'nasdaq' ? nasdaqCfg : goldCfg;
    const updatedAsset = {
      ...baseConfig,
      [field]: value
    };

    // Dispara a atualização imediata no estado central
    onUpdateSettings({ [assetKey]: updatedAsset });
  };

  const handleToggleGlobal = (field) => {
    onUpdateSettings({ [field]: !settings?.[field] });
  };

  return (
    <div className="space-y-4 lg:space-y-0 lg:grid lg:grid-cols-12 lg:gap-4 xl:gap-5">
      
      {/* ============================================================== */}
      {/* COLUNA ESQUERDA — 5 Colunas */}
      {/* ============================================================== */}
      <div className="space-y-4 lg:col-span-5">

        {/* 0. SELETOR MASTER */}
        <div className={`p-4 rounded-2xl border transition-all shadow-xl ${
          isRawMode 
            ? 'bg-amber-950/20 border-amber-500/40 text-amber-200' 
            : 'bg-zinc-900/90 border-zinc-800 text-zinc-300'
        }`}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Target size={18} className={isRawMode ? "text-amber-400" : "text-violet-400"} />
              <strong className="text-xs font-mono uppercase tracking-wider text-zinc-100">
                {isRawMode ? 'MODO FIEL AO BACKTEST (1:1)' : 'MODO BLINDAGEM MESA'}
              </strong>
            </div>
            <button
              onClick={() => handleToggleGlobal('raw_backtest_mode')}
              className={`px-3 py-1 rounded-xl text-[10px] font-mono font-bold border transition-all ${
                isRawMode 
                  ? 'bg-amber-500/30 text-amber-300 border-amber-500/50' 
                  : 'bg-zinc-800 text-zinc-400 border-zinc-700'
              }`}>
              {isRawMode ? 'ATIVO (FIEL)' : 'ATIVAR FIEL'}
            </button>
          </div>
          <p className="text-[10px] text-zinc-400 leading-relaxed font-mono">
            {isRawMode
              ? 'Opera estritamente como no Sandbox: desativa vetos da IA Groq, estrutura M15 e cancelamento por notícias.'
              : 'Blindagem total ativa: usa filtros adicionais de M15, notícias de alto impacto e veto da IA Groq.'}
          </p>
        </div>
        
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
              PROP FIRM RULES
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
                Meta de Lucro ($)
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

        {/* 4. EXECUTION GUARDS */}
        <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4 space-y-3">
          <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 block mb-1">
            4. Execution Guards (Proteções de Capital)
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

          <div className="flex items-center justify-between py-1.5">
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
        </div>
      </div>

      {/* ============================================================== */}
      {/* COLUNA DIREITA — 7 Colunas */}
      {/* ============================================================== */}
      <div className="space-y-4 lg:col-span-7">
        
        {/* 3. CONTROLE HÍBRIDO INDEPENDENTE */}
        <div className="bg-zinc-900/90 border border-zinc-800 rounded-2xl p-4 lg:p-5 space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-[11px] font-mono uppercase tracking-wider text-zinc-400 block">
              3. Independent Asset Engine
            </label>
            <span className="text-[9px] bg-violet-500/10 text-violet-300 border border-violet-500/20 px-2 py-0.5 rounded font-mono font-bold">
              DNA INDEPENDENTE
            </span>
          </div>

          {/* Abas dos Ativos */}
          <div className="grid grid-cols-2 gap-2 bg-zinc-950 p-1.5 rounded-xl border border-zinc-800 text-xs font-mono font-bold">
            <button
              onClick={() => setSelectedAssetTab('nasdaq')}
              className={`py-2.5 rounded-lg transition-all flex items-center justify-center gap-2 ${
                selectedAssetTab === 'nasdaq'
                  ? 'bg-zinc-800 text-violet-300 shadow'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}>
              NASDAQ (US100)
              {nasdaqCfg.auto_ia && <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />}
            </button>
            <button
              onClick={() => setSelectedAssetTab('gold')}
              className={`py-2.5 rounded-lg transition-all flex items-center justify-center gap-2 ${
                selectedAssetTab === 'gold'
                  ? 'bg-zinc-800 text-amber-300 shadow'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}>
              GOLD (XAUUSD)
              {goldCfg.auto_ia && <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />}
            </button>
          </div>

          {/* SESSÃO DO ATIVO */}
          <div className="bg-zinc-950 p-3.5 rounded-xl border border-zinc-800 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock size={15} className="text-zinc-400" />
                <span className="text-xs font-mono font-bold text-zinc-200">
                  Horário de Operação ({selectedAssetTab === 'nasdaq' ? 'NASDAQ' : 'GOLD'}):
                </span>
              </div>
              <span className="text-[9px] font-mono text-zinc-500">Relógio do MT5</span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleUpdateAssetField(selectedAssetTab, 'session_mode', 'KILLZONES')}
                className={`py-2 rounded-xl text-[11px] font-mono font-bold border transition-all ${
                  (currentCfg.session_mode || 'KILLZONES') === 'KILLZONES'
                    ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300 shadow-sm'
                    : 'bg-zinc-900 border-zinc-800 text-zinc-500 hover:text-zinc-300'
                }`}>
                KILLZONES (Londres/NY)
              </button>
              <button
                onClick={() => handleUpdateAssetField(selectedAssetTab, 'session_mode', '24H')}
                className={`py-2 rounded-xl text-[11px] font-mono font-bold border transition-all ${
                  currentCfg.session_mode === '24H'
                    ? 'bg-amber-500/10 border-amber-500/40 text-amber-300 shadow-sm'
                    : 'bg-zinc-900 border-zinc-800 text-zinc-500 hover:text-zinc-300'
                }`}>
                24 HORAS (Sem Filtro)
              </button>
            </div>
            <span className="text-[10px] text-zinc-500 block">
              {currentCfg.session_mode === '24H' 
                ? 'Opera a qualquer momento (inclusive madrugada e Ásia), exceto no fechamento/rollover diário.'
                : 'Filtra horários nobres de alta volatilidade e spreads baixos.'}
            </span>
          </div>

          {/* Toggle Modo do Ativo */}
          <div className="bg-zinc-950/70 p-3.5 rounded-xl border border-zinc-800/80 space-y-2">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <Bot size={16} className={currentCfg.auto_ia ? "text-violet-400" : "text-zinc-500"} />
                  <strong className="text-xs lg:text-sm text-zinc-200">
                    Modo: {currentCfg.auto_ia ? 'AUTO IA (Base 30D)' : 'MANUAL'}
                  </strong>
                </div>
                <span className="text-[10px] text-zinc-400 block mt-0.5">
                  {currentCfg.auto_ia 
                    ? 'A IA calibra o setup com maior Prop Score dos últimos 30 dias.'
                    : 'Você define o perfil e os parâmetros fixos para este ativo.'}
                </span>
              </div>

              <button
                onClick={() => handleUpdateAssetField(selectedAssetTab, 'auto_ia', !currentCfg.auto_ia)}
                className={`px-3.5 py-2 rounded-xl text-[10px] font-mono font-bold border transition-all ${
                  currentCfg.auto_ia
                    ? 'bg-violet-500/20 text-violet-300 border-violet-500/40'
                    : 'bg-zinc-800 text-zinc-400 border-zinc-700'
                }`}>
                {currentCfg.auto_ia ? 'DESATIVAR IA' : 'ATIVAR IA (30D)'}
              </button>
            </div>
          </div>

          {/* Parâmetros do Ativo */}
          <div className={`space-y-4 transition-opacity ${currentCfg.auto_ia ? 'opacity-40 pointer-events-none' : 'opacity-100'}`}>
            <div>
              <span className="text-[10px] text-zinc-400 font-mono block mb-2">
                Perfil de Execução ({selectedAssetTab === 'nasdaq' ? 'NASDAQ' : 'GOLD'}):
              </span>
              <div className="grid grid-cols-3 gap-2.5">
                <button
                  onClick={() => handleUpdateAssetField(selectedAssetTab, 'profile', 'sniper')}
                  className={`p-3 rounded-xl border flex flex-col items-center gap-1.5 transition-all ${
                    currentCfg.profile === 'sniper'
                      ? 'bg-amber-500/10 border-amber-500/40 text-amber-300'
                      : 'bg-zinc-950 border-zinc-800 text-zinc-400'
                  }`}>
                  <Crosshair size={16} />
                  <span className="text-[10px] font-bold font-mono">SNIPER (1:4)</span>
                </button>

                <button
                  onClick={() => handleUpdateAssetField(selectedAssetTab, 'profile', 'tatico')}
                  className={`p-3 rounded-xl border flex flex-col items-center gap-1.5 transition-all ${
                    currentCfg.profile === 'tatico'
                      ? 'bg-blue-500/10 border-blue-500/40 text-blue-300'
                      : 'bg-zinc-950 border-zinc-800 text-zinc-400'
                  }`}>
                  <Zap size={16} />
                  <span className="text-[10px] font-bold font-mono">TACTICAL (1:2.5)</span>
                </button>

                <button
                  onClick={() => handleUpdateAssetField(selectedAssetTab, 'profile', 'guardiao')}
                  className={`p-3 rounded-xl border flex flex-col items-center gap-1.5 transition-all ${
                    currentCfg.profile === 'guardiao'
                      ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                      : 'bg-zinc-950 border-zinc-800 text-zinc-400'
                  }`}>
                  <ShieldCheck size={16} />
                  <span className="text-[10px] font-bold font-mono">GUARDIAN (1:1.5)</span>
                </button>
              </div>
            </div>

            <div>
              <span className="text-[10px] text-zinc-400 font-mono block mb-2">Ponto de Entrada FVG:</span>
              <div className="grid grid-cols-2 gap-2.5">
                <button
                  onClick={() => handleUpdateAssetField(selectedAssetTab, 'use_ce_50', true)}
                  className={`py-2 rounded-xl text-[11px] font-mono font-bold border transition-all ${
                    currentCfg.use_ce_50 !== false
                      ? 'bg-violet-500/10 border-violet-500/40 text-violet-300'
                      : 'bg-zinc-950 border-zinc-800 text-zinc-500'
                  }`}>
                  50% (Consequent Encroachment)
                </button>
                <button
                  onClick={() => handleUpdateAssetField(selectedAssetTab, 'use_ce_50', false)}
                  className={`py-2 rounded-xl text-[11px] font-mono font-bold border transition-all ${
                    currentCfg.use_ce_50 === false
                      ? 'bg-violet-500/10 border-violet-500/40 text-violet-300'
                      : 'bg-zinc-950 border-zinc-800 text-zinc-500'
                  }`}>
                  Borda do FVG
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between py-2 border-t border-zinc-800/60">
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
      </div>
    </div>
  );
}