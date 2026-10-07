import React, { useState } from 'react';
import { 
  UserCheck, Power, Sparkles, BarChart3, AlertTriangle, X, 
  CheckCircle2, Trophy, ArrowRight, Loader2, Activity, Clock, 
  Radar, Cpu, Sliders, ShieldCheck, Zap, Crosshair
} from 'lucide-react';

export default function Dashboard({ 
  status, 
  settings, 
  onEmergencyStop, 
  onRunBacktest, 
  onUpdateSettings,
  latestBacktest,
  showReportModal,
  setShowReportModal,
  isBacktestLoading
}) {
  const isOnline = status?.is_online;
  const pnl = Number(status?.pnl_today || 0);

  const [showEmergencyModal, setShowEmergencyModal] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState('US100');
  const [selectedDays, setSelectedDays] = useState(5);
  const [backtestViewTab, setBacktestViewTab] = useState('compare');

  const currentRiskBase = Number(settings?.risk_per_trade || 50);
  const stats = status?.today_stats || {
    total_trades: 0,
    wins: 0,
    losses: 0,
    win_rate: 0,
    realized_pnl: 0,
    net_r: 0,
    open_count: 0,
    open_positions: [],
    closed_trades: []
  };

  const scoutDirectives = stats?.scout_directives || null;
  const isAutoAI = stats?.is_auto_ai ?? !!settings?.auto_profile_ia;
  const activeStrategy = stats?.active_strategy || {
    entry_type: settings?.use_ce_50 !== false ? "50% Consequent Encroachment (CE)" : "Borda do FVG",
    breakeven: settings?.breakeven_enabled !== false ? "ATIVO (1.2R)" : "DESLIGADO"
  };

  const handleBacktestClick = () => {
    onRunBacktest(selectedDays, selectedAsset);
  };

  const applyRecommendedProfile = (recommended) => {
    let profileKey = 'tatico';
    if (recommended.includes('GUARDIAN')) profileKey = 'guardiao';
    else if (recommended.includes('SNIPER')) profileKey = 'sniper';
    onUpdateSettings({ profile: profileKey });
    setShowReportModal(false);
  };

  return (
    <div className="space-y-3.5 relative">
      {/* 1. CARD CONTA FTMO */}
      <div className="bg-zinc-900/90 border border-zinc-800 p-4 rounded-2xl flex items-center justify-between shadow-xl">
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
          <span className="text-[10px] text-zinc-500 font-mono block">EQUITY</span>
          <strong className="text-sm font-black text-zinc-100 font-mono">${status?.account_equity || '0.00'}</strong>
        </div>
      </div>

      {/* 2. MODO OPERACIONAL E ESTRATÉGIA NO COMANDO */}
      <div className="bg-gradient-to-r from-zinc-900 via-zinc-900/90 to-zinc-950 border border-zinc-800 p-3.5 rounded-2xl shadow-lg space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu size={15} className={isAutoAI ? "text-violet-400" : "text-blue-400"} />
            <span className="text-[11px] font-mono font-bold text-zinc-200 uppercase">
              Modo Operacional
            </span>
          </div>
          <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
            isAutoAI 
              ? 'bg-violet-500/20 text-violet-300 border-violet-500/40' 
              : 'bg-zinc-800 text-zinc-300 border-zinc-700'
          }`}>
            {isAutoAI ? '🤖 IA / SCOUT AUTO' : '👤 MANUAL'}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2 text-[10px] font-mono bg-zinc-950/70 p-2.5 rounded-xl border border-zinc-800/60">
          <div>
            <span className="text-zinc-500 block">Entrada FVG:</span>
            <strong className="text-zinc-200 font-semibold">{activeStrategy.entry_type}</strong>
          </div>
          <div>
            <span className="text-zinc-500 block">Break-Even Live:</span>
            <strong className={activeStrategy.breakeven.includes("ATIVO") ? "text-emerald-400 font-semibold" : "text-zinc-400"}>
              {activeStrategy.breakeven}
            </strong>
          </div>
        </div>
      </div>

      {/* 3. RADAR DO STRATEGY SCOUT */}
      <div className="bg-zinc-900/90 border border-zinc-800 p-4 rounded-2xl shadow-xl space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Radar size={15} className="text-amber-400 animate-pulse" />
            <h4 className="text-xs font-bold text-zinc-200 uppercase font-mono">Strategy Scout (Diretrizes)</h4>
          </div>
          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-amber-300 border border-amber-500/20">
            Auto-Calibrador
          </span>
        </div>

        {scoutDirectives ? (
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-zinc-950 p-2.5 rounded-xl border border-zinc-800/80 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-zinc-300 font-mono">NASDAQ</span>
                <span className={`text-[8px] font-mono font-bold px-1.5 py-0.2 rounded border ${
                  scoutDirectives.NASDAQ?.should_trade 
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                    : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                }`}>
                  {scoutDirectives.NASDAQ?.should_trade ? 'AUTORIZADO' : 'STAND-BY'}
                </span>
              </div>
              <div className="text-[10px] font-mono text-zinc-400">
                Perfil: <strong className="text-zinc-200">{scoutDirectives.NASDAQ?.recommended_profile?.toUpperCase()}</strong>
              </div>
              <div className="text-[9px] font-mono text-zinc-500 flex justify-between">
                <span>Score: <strong className="text-zinc-300">{scoutDirectives.NASDAQ?.prop_score}</strong></span>
                <span>WinRate: <strong className="text-zinc-300">{scoutDirectives.NASDAQ?.win_rate}%</strong></span>
              </div>
            </div>

            <div className="bg-zinc-950 p-2.5 rounded-xl border border-zinc-800/80 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold text-zinc-300 font-mono">XAUUSD (GOLD)</span>
                <span className={`text-[8px] font-mono font-bold px-1.5 py-0.2 rounded border ${
                  scoutDirectives.GOLD?.should_trade 
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                    : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                }`}>
                  {scoutDirectives.GOLD?.should_trade ? 'AUTORIZADO' : 'STAND-BY'}
                </span>
              </div>
              <div className="text-[10px] font-mono text-zinc-400">
                Perfil: <strong className="text-zinc-200">{scoutDirectives.GOLD?.recommended_profile?.toUpperCase()}</strong>
              </div>
              <div className="text-[9px] font-mono text-zinc-500 flex justify-between">
                <span>Score: <strong className="text-zinc-300">{scoutDirectives.GOLD?.prop_score}</strong></span>
                <span>WinRate: <strong className="text-zinc-300">{scoutDirectives.GOLD?.win_rate}%</strong></span>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-3 bg-zinc-950/60 rounded-xl text-center text-[10px] font-mono text-zinc-500">
            Strategy Scout calibrando permutações institucionais...
          </div>
        )}
      </div>

      {/* 4. PLACAR PNL & SALDO */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-zinc-900/90 border border-zinc-800 p-3.5 rounded-2xl shadow-lg">
          <span className="text-[10px] font-mono text-zinc-500 uppercase block">Account Balance</span>
          <strong className="text-base font-bold text-zinc-200 font-mono block mt-1">
            ${status?.account_balance || '0.00'}
          </strong>
        </div>

        <div className="bg-zinc-900/90 border border-zinc-800 p-3.5 rounded-2xl shadow-lg">
          <span className="text-[10px] font-mono text-zinc-500 uppercase block">Session PNL (Equity - Bal)</span>
          <strong className={`text-base font-black font-mono block mt-1 ${pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {pnl >= 0 ? `+$${pnl.toFixed(2)}` : `-$${Math.abs(pnl).toFixed(2)}`}
          </strong>
        </div>
      </div>

      {/* 5. CONTADORES REAIS COM NET R */}
      <div className="bg-zinc-900/90 border border-zinc-800 p-4 rounded-2xl shadow-xl space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity size={15} className="text-emerald-400" />
            <h4 className="text-xs font-bold text-zinc-200 uppercase font-mono">Today's Live Performance</h4>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">
            {stats.total_trades} Closed Deals
          </span>
        </div>

        <div className="grid grid-cols-4 gap-2 text-center">
          <div className="bg-zinc-950 p-2 rounded-xl border border-zinc-800/80">
            <span className="text-[8px] font-mono text-zinc-500 block uppercase">W / L</span>
            <strong className="text-xs font-bold font-mono text-zinc-200 mt-0.5 block">
              <span className="text-emerald-400">{stats.wins}W</span> / <span className="text-rose-400">{stats.losses}L</span>
            </strong>
          </div>

          <div className="bg-zinc-950 p-2 rounded-xl border border-zinc-800/80">
            <span className="text-[8px] font-mono text-zinc-500 block uppercase">Win Rate</span>
            <strong className="text-xs font-bold font-mono text-zinc-100 mt-0.5 block">
              {stats.win_rate}%
            </strong>
          </div>

          <div className="bg-zinc-950 p-2 rounded-xl border border-zinc-800/80">
            <span className="text-[8px] font-mono text-zinc-500 block uppercase">Realized PnL</span>
            <strong className={`text-xs font-black font-mono mt-0.5 block ${stats.realized_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
              {stats.realized_pnl >= 0 ? `+$${stats.realized_pnl.toFixed(2)}` : `-$${Math.abs(stats.realized_pnl).toFixed(2)}`}
            </strong>
          </div>

          <div className="bg-zinc-950 p-2 rounded-xl border border-zinc-800/80">
            <span className="text-[8px] font-mono text-amber-400 block uppercase font-bold">Net R (R:R)</span>
            <strong className={`text-xs font-black font-mono mt-0.5 block ${stats.net_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
              {stats.net_r >= 0 ? `+${stats.net_r}R` : `${stats.net_r}R`}
            </strong>
          </div>
        </div>

        {/* POSIÇÕES ABERTAS AGORA */}
        <div>
          <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider block mb-1.5">
            Active Positions ({stats.open_count})
          </span>
          {stats.open_positions && stats.open_positions.length > 0 ? (
            <div className="space-y-1.5">
              {stats.open_positions.map((pos) => (
                <div key={pos.ticket} className="bg-zinc-950 border border-zinc-800 p-2.5 rounded-xl flex items-center justify-between text-[11px] font-mono">
                  <div className="flex items-center gap-2">
                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${pos.type === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                      {pos.type}
                    </span>
                    <strong className="text-zinc-200">{pos.symbol}</strong>
                    <span className="text-zinc-500">({pos.volume} lots)</span>
                  </div>
                  <div className="text-right">
                    <span className={`font-bold ${pos.profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {pos.profit >= 0 ? `+$${pos.profit.toFixed(2)}` : `-$${Math.abs(pos.profit).toFixed(2)}`}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-2.5 bg-zinc-950/60 border border-zinc-800/60 rounded-xl text-center text-[10px] font-mono text-zinc-500">
              Nenhuma posição aberta no momento...
            </div>
          )}
        </div>

        {/* ÚLTIMOS TRADES */}
        {stats.closed_trades && stats.closed_trades.length > 0 && (
          <div>
            <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider block mb-1.5">
              Recent Closed Deals
            </span>
            <div className="space-y-1 max-h-28 overflow-y-auto no-scrollbar pr-1">
              {stats.closed_trades.map((deal) => (
                <div key={deal.ticket} className="bg-zinc-950/80 border border-zinc-800/50 p-2 rounded-lg flex items-center justify-between text-[10px] font-mono">
                  <div className="flex items-center gap-1.5">
                    <Clock size={10} className="text-zinc-500" />
                    <span className="text-zinc-400">{deal.time}</span>
                    <strong className="text-zinc-300">{deal.symbol}</strong>
                    <span className={deal.type === 'BUY' ? 'text-emerald-400' : 'text-rose-400'}>({deal.type})</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-[9px] font-bold ${deal.r_multiple >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {deal.r_multiple >= 0 ? `+${deal.r_multiple}R` : `${deal.r_multiple}R`}
                    </span>
                    <strong className={deal.profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                      {deal.profit >= 0 ? `+$${deal.profit.toFixed(2)}` : `-$${Math.abs(deal.profit).toFixed(2)}`}
                    </strong>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 6. SANDBOX BACKTEST */}
      <div className="bg-gradient-to-br from-zinc-900 to-zinc-950 border border-zinc-800/80 p-4 rounded-2xl space-y-3 shadow-xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles size={15} className="text-amber-400" />
            <h4 className="text-xs font-bold text-zinc-200 uppercase font-mono">Sandbox Backtest (A/B Test)</h4>
          </div>
          {latestBacktest && !isBacktestLoading && (
            <button
              onClick={() => setShowReportModal(true)}
              className="text-[10px] font-mono font-bold text-violet-400 hover:text-violet-300 underline flex items-center gap-1">
              Ver Relatório A/B <ArrowRight size={10} />
            </button>
          )}
        </div>

        <div>
          <span className="text-[10px] font-mono text-zinc-400 block mb-1.5 uppercase">Ativo</span>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => setSelectedAsset('US100')}
              className={`py-1.5 rounded-xl text-xs font-mono font-bold border transition-all ${
                selectedAsset === 'US100'
                  ? 'bg-violet-500/10 border-violet-500/40 text-violet-300'
                  : 'bg-zinc-950 border-zinc-800/80 text-zinc-500 hover:text-zinc-300'
              }`}>
              NASDAQ (US100)
            </button>
            <button
              onClick={() => setSelectedAsset('XAUUSD')}
              className={`py-1.5 rounded-xl text-xs font-mono font-bold border transition-all ${
                selectedAsset === 'XAUUSD'
                  ? 'bg-amber-500/10 border-amber-500/40 text-amber-300'
                  : 'bg-zinc-950 border-zinc-800/80 text-zinc-500 hover:text-zinc-300'
              }`}>
              GOLD (XAUUSD)
            </button>
          </div>
        </div>

        <div>
          <span className="text-[10px] font-mono text-zinc-400 block mb-1.5 uppercase">Janela de Teste</span>
          <div className="grid grid-cols-4 gap-1.5">
            {[1, 2, 3, 5].map((d) => (
              <button
                key={d}
                onClick={() => setSelectedDays(d)}
                className={`py-1 rounded-lg text-xs font-mono font-bold border transition-all ${
                  selectedDays === d
                    ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                    : 'bg-zinc-950 border-zinc-800/80 text-zinc-500 hover:text-zinc-300'
                }`}>
                {d}D
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleBacktestClick}
          disabled={isBacktestLoading}
          className="w-full py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-xs font-mono font-bold text-amber-300 border border-zinc-700 transition-all flex items-center justify-center gap-2 shadow-lg">
          {isBacktestLoading ? (
            <>
              <Loader2 size={14} className="animate-spin text-amber-400" />
              <span>Simulando A/B (Com e Sem BE) para {selectedAsset}...</span>
            </>
          ) : (
            <>
              <BarChart3 size={14} />
              <span>Rodar Backtest A/B ({selectedAsset} - {selectedDays}D)</span>
            </>
          )}
        </button>
      </div>

      {/* 7. TRAVA DE EMERGÊNCIA */}
      <button
        onClick={() => setShowEmergencyModal(true)}
        className="w-full py-3 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 text-rose-300 rounded-xl text-xs font-bold font-mono uppercase tracking-wider flex items-center justify-center gap-2 transition-all">
        <Power size={14} /> Trava de Emergência (Zerar Tudo)
      </button>

      {/* 8. MODAL DO BACKTEST COMPLETO (SEM BARRA LATERAL FEIA) */}
      {showReportModal && (
        <div className="fixed inset-0 bg-black/85 backdrop-blur-sm z-50 flex items-center justify-center p-3 sm:p-4">
          <div className="bg-zinc-900 border border-zinc-800 w-full max-w-lg rounded-2xl p-5 shadow-2xl relative animate-in fade-in zoom-in-95 duration-150 space-y-4 max-h-[92vh] overflow-y-auto no-scrollbar">
            <button
              onClick={() => setShowReportModal(false)}
              className="absolute top-4 right-4 text-zinc-500 hover:text-zinc-200">
              <X size={18} />
            </button>

            {isBacktestLoading ? (
              <div className="py-12 flex flex-col items-center justify-center text-center space-y-3">
                <Loader2 size={36} className="animate-spin text-amber-400" />
                <div>
                  <h3 className="text-sm font-bold text-zinc-100 font-mono">Executando Simulação A/B Completa</h3>
                  <p className="text-[11px] text-zinc-400 font-mono mt-1">
                    Analisando retestes, spreads e proteções de Break-Even...
                  </p>
                </div>
              </div>
            ) : latestBacktest ? (
              <>
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-xl">
                    <Trophy size={22} />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-zinc-100 font-mono uppercase">
                      {latestBacktest.symbol} Relatório Completo A/B
                    </h3>
                    <span className="text-[10px] text-zinc-400 font-mono">
                      {latestBacktest.days}D • {latestBacktest.setups} Setups • Risco: ${latestBacktest.base_risk || currentRiskBase}
                    </span>
                  </div>
                </div>

                {latestBacktest.strategy_info && (
                  <div className="bg-zinc-950 p-2.5 rounded-xl border border-zinc-800/80 grid grid-cols-3 gap-2 text-[9px] font-mono text-zinc-400">
                    <div>
                      <span className="text-zinc-500 block">Entrada:</span>
                      <strong className="text-zinc-200">{latestBacktest.strategy_info.entry}</strong>
                    </div>
                    <div>
                      <span className="text-zinc-500 block">Sessões:</span>
                      <strong className="text-zinc-200">{latestBacktest.strategy_info.sessions}</strong>
                    </div>
                    <div>
                      <span className="text-zinc-500 block">Visão:</span>
                      <strong className="text-emerald-400">{latestBacktest.strategy_info.cv_filter}</strong>
                    </div>
                  </div>
                )}

                {/* TABS COMPARATIVAS */}
                <div className="grid grid-cols-3 gap-1 bg-zinc-950 p-1 rounded-xl border border-zinc-800 text-[10px] font-mono font-bold">
                  <button
                    onClick={() => setBacktestViewTab('compare')}
                    className={`py-1.5 rounded-lg transition-all ${
                      backtestViewTab === 'compare' ? 'bg-zinc-800 text-zinc-100 shadow' : 'text-zinc-500 hover:text-zinc-300'
                    }`}>
                    Lado a Lado (A/B)
                  </button>
                  <button
                    onClick={() => setBacktestViewTab('with_be')}
                    className={`py-1.5 rounded-lg transition-all ${
                      backtestViewTab === 'with_be' ? 'bg-zinc-800 text-emerald-400 shadow' : 'text-zinc-500 hover:text-zinc-300'
                    }`}>
                    Com Break-Even
                  </button>
                  <button
                    onClick={() => setBacktestViewTab('no_be')}
                    className={`py-1.5 rounded-lg transition-all ${
                      backtestViewTab === 'no_be' ? 'bg-zinc-800 text-blue-400 shadow' : 'text-zinc-500 hover:text-zinc-300'
                    }`}>
                    Sem Break-Even
                  </button>
                </div>

                {/* VISÃO COMPARATIVA */}
                {backtestViewTab === 'compare' && (
                  <div className="space-y-2">
                    {[
                      { key: 'guardiao', label: 'GUARDIAN (1:1.5)', color: 'text-emerald-400' },
                      { key: 'tatico', label: 'TACTICAL (1:2.5)', color: 'text-blue-400' },
                      { key: 'sniper', label: 'SNIPER (1:4.0)', color: 'text-amber-400' },
                    ].map(({ key, label, color }) => {
                      const withBeData = latestBacktest.with_be?.[key] || latestBacktest[key];
                      const noBeData = latestBacktest.without_be?.[key] || latestBacktest[key];
                      return (
                        <div key={key} className="bg-zinc-950 p-3 rounded-xl border border-zinc-800/80 space-y-2">
                          <div className="flex items-center justify-between border-b border-zinc-800/60 pb-1">
                            <strong className={`text-xs font-mono font-bold ${color}`}>{label}</strong>
                            <span className="text-[9px] font-mono text-zinc-500">Comparação R:R</span>
                          </div>

                          <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
                            <div className="bg-zinc-900/60 p-2 rounded-lg border border-zinc-800/50">
                              <span className="text-[9px] text-emerald-400 font-bold block mb-1">COM BREAK-EVEN</span>
                              <div className="space-y-0.5 text-zinc-400">
                                <div>Win: <strong className="text-zinc-200">{withBeData.rate}%</strong> ({withBeData.wins}W / {withBeData.losses}L)</div>
                                {withBeData.be_count && <div>Saídas BE: <strong className="text-zinc-300">{withBeData.be_count}</strong></div>}
                                <div>Net R: <strong className={withBeData.net_r >= 0 ? "text-emerald-400" : "text-rose-400"}>{withBeData.net_r >= 0 ? `+${withBeData.net_r}R` : `${withBeData.net_r}R`}</strong></div>
                                <div>PnL: <strong className={withBeData.pnl >= 0 ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>${withBeData.pnl}</strong></div>
                              </div>
                            </div>

                            <div className="bg-zinc-900/60 p-2 rounded-lg border border-zinc-800/50">
                              <span className="text-[9px] text-blue-400 font-bold block mb-1">SEM BREAK-EVEN</span>
                              <div className="space-y-0.5 text-zinc-400">
                                <div>Win: <strong className="text-zinc-200">{noBeData.rate}%</strong> ({noBeData.wins}W / {noBeData.losses}L)</div>
                                <div>Net R: <strong className={noBeData.net_r >= 0 ? "text-emerald-400" : "text-rose-400"}>{noBeData.net_r >= 0 ? `+${noBeData.net_r}R` : `${noBeData.net_r}R`}</strong></div>
                                <div>PnL: <strong className={noBeData.pnl >= 0 ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>${noBeData.pnl}</strong></div>
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* VISÃO INDIVIDUAL */}
                {backtestViewTab !== 'compare' && (
                  <div className="space-y-2">
                    {['guardiao', 'tatico', 'sniper'].map((pKey) => {
                      const currentDataset = backtestViewTab === 'with_be' 
                        ? (latestBacktest.with_be?.[pKey] || latestBacktest[pKey]) 
                        : (latestBacktest.without_be?.[pKey] || latestBacktest[pKey]);
                      const title = pKey === 'guardiao' ? 'GUARDIAN (1:1.5)' : pKey === 'tatico' ? 'TACTICAL (1:2.5)' : 'SNIPER (1:4.0)';
                      return (
                        <div key={pKey} className="bg-zinc-950 p-3 rounded-xl border border-zinc-800/80 flex items-center justify-between text-xs font-mono">
                          <div>
                            <strong className="text-zinc-200 block">{title}</strong>
                            <span className="text-[10px] text-zinc-500">
                              {currentDataset.wins}W / {currentDataset.losses}L {currentDataset.be_count ? `• ${currentDataset.be_count} BEs` : ''}
                            </span>
                          </div>
                          <div className="text-right">
                            <span className="text-[11px] font-bold text-zinc-300 block">{currentDataset.rate}% Win</span>
                            <strong className={`text-xs font-black ${currentDataset.pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                              {currentDataset.net_r >= 0 ? `+${currentDataset.net_r}R` : `${currentDataset.net_r}R`} (${currentDataset.pnl})
                            </strong>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                <div className="bg-zinc-950 p-3 rounded-xl border border-zinc-800/80 flex items-center justify-between">
                  <div>
                    <span className="text-[9px] text-zinc-500 font-mono uppercase block">Melhor Estrutura Global</span>
                    <strong className="text-xs font-bold text-emerald-400 font-mono">
                      {latestBacktest.recommended}
                    </strong>
                  </div>
                  <button
                    onClick={() => applyRecommendedProfile(latestBacktest.recommended)}
                    className="px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-bold font-mono transition-all flex items-center gap-1.5 shadow-md">
                    <CheckCircle2 size={14} /> Aplicar Perfil
                  </button>
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}

      {/* 9. MODAL EMERGÊNCIA */}
      {showEmergencyModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 w-full max-w-sm rounded-2xl p-5 shadow-2xl relative animate-in fade-in zoom-in-95 duration-150">
            <button
              onClick={() => setShowEmergencyModal(false)}
              className="absolute top-4 right-4 text-zinc-500 hover:text-zinc-200">
              <X size={18} />
            </button>

            <div className="flex items-center gap-3 mb-3">
              <div className="p-2.5 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl">
                <AlertTriangle size={22} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-zinc-100 font-mono">Trava de Emergência</h3>
                <span className="text-[10px] text-zinc-400 font-mono">Execução Imediata</span>
              </div>
            </div>

            <p className="text-xs text-zinc-300 mb-5 leading-relaxed bg-zinc-950/60 p-3 rounded-xl border border-zinc-800/60">
              Esta ação cancelará todas as ordens pendentes e liquidará todas as posições abertas no MetaTrader 5 imediatamente.
            </p>

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setShowEmergencyModal(false)}
                className="py-2.5 rounded-xl border border-zinc-800 bg-zinc-800/60 hover:bg-zinc-800 text-xs font-bold text-zinc-300">
                Cancelar
              </button>
              <button
                onClick={() => {
                  setShowEmergencyModal(false);
                  onEmergencyStop();
                }}
                className="py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-xs font-bold text-white shadow-lg shadow-rose-900/50">
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}