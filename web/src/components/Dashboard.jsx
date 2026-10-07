import React, { useState } from 'react';
import { 
  UserCheck, Power, Sparkles, BarChart3, AlertTriangle, X, 
  CheckCircle2, Trophy, ArrowRight, Loader2, Activity, Clock, 
  Radar, Cpu, Sliders, ShieldCheck, Zap, Crosshair, TableProperties, Target
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
  const [selectedDays, setSelectedDays] = useState(0);
  const [backtestViewTab, setBacktestViewTab] = useState('raio_x');

  const currentRiskBase = Number(settings?.risk_per_trade || 50);
  const propTarget = Number(settings?.prop_target_profit || 8000);

  const stats = status?.today_stats || {
    total_trades: 0,
    wins: 0,
    losses: 0,
    win_rate: 0,
    realized_pnl: 0,
    net_r: 0,
    open_count: 0,
    open_positions: [],
    closed_trades: [],
    stats_30d: {
      total_trades: 0,
      wins: 0,
      losses: 0,
      win_rate: 0,
      realized_pnl: 0,
      net_r: 0,
      max_drawdown_usd: 0,
      profit_factor: 0
    }
  };

  const stats30d = stats.stats_30d || {
    total_trades: 0,
    wins: 0,
    losses: 0,
    win_rate: 0,
    realized_pnl: 0,
    net_r: 0,
    max_drawdown_usd: 0,
    profit_factor: 0
  };

  const progressPct = Math.min(100, Math.max(0, (stats30d.realized_pnl / Math.max(propTarget, 1)) * 100));
  const scoutDirectives = stats?.scout_directives || null;

  const activeStrategy = stats?.active_strategy || {
    nasdaq: {
      is_auto: false,
      profile: settings?.nasdaq?.profile || settings?.profile || 'guardiao',
      entry_type: '50% CE',
      status: 'AUTORIZADO'
    },
    gold: {
      is_auto: false,
      profile: settings?.gold?.profile || settings?.profile || 'tatico',
      entry_type: '50% CE',
      status: 'AUTORIZADO'
    },
    breakeven: settings?.breakeven_enabled !== false ? "ATIVO (1.2R)" : "DESLIGADO",
    trailing: settings?.trailing_enabled ? "ATIVO (M1)" : "DESLIGADO"
  };

  const handleBacktestClick = () => {
    onRunBacktest(selectedDays, selectedAsset);
  };

  const anyIsNasdaq = (sym) => {
    const s = String(sym).toUpperCase();
    return s.includes("US100") || s.includes("NAS") || s.includes("USTEC") || s.includes("NQ");
  };

  const applyCustomStrategy = (item) => {
    const isNasdaq = latestBacktest?.symbol && anyIsNasdaq(latestBacktest.symbol);
    const assetKey = isNasdaq ? 'nasdaq' : 'gold';

    const currentAssetConfig = settings?.[assetKey] || {};
    const updatedAssetConfig = {
      ...currentAssetConfig,
      auto_ia: false,
      profile: item.profile_key,
      use_ce_50: item.entry.includes('50%'),
      require_sweep: item.sweep.includes('Com')
    };

    onUpdateSettings({
      [assetKey]: updatedAssetConfig,
      breakeven_enabled: item.with_be
    });

    setShowReportModal(false);
  };

  const formatDaysLabel = (d) => {
    if (d === 0 || d === "0") return "Sessão Atual (Hoje)";
    return `${d}D`;
  };

  const formatProfileLabel = (p) => {
    if (!p) return 'GUARDIAN (1:1.5)';
    const low = p.toLowerCase();
    if (low === 'guardiao') return 'GUARDIAN (1:1.5)';
    if (low === 'sniper') return 'SNIPER (1:4.0)';
    return 'TACTICAL (1:2.5)';
  };

  return (
    <div className="relative">
      {/* GRID RESPONSIVO: 1 coluna no mobile, 12 colunas no notebook */}
      <div className="space-y-4 lg:space-y-0 lg:grid lg:grid-cols-12 lg:gap-4 xl:gap-5">
        
        {/* ============================================================== */}
        {/* COLUNA ESQUERDA (DADOS & ESTRATÉGIAS) — 7 Colunas em Notebook */}
        {/* ============================================================== */}
        <div className="space-y-4 lg:col-span-7 xl:col-span-7">
          
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
              <span className="text-[10px] text-zinc-500 font-mono block">EQUITY TOTAL</span>
              <strong className="text-base font-black text-zinc-100 font-mono">${status?.account_equity || '0.00'}</strong>
            </div>
          </div>

          {/* 2. CARD META DA MESA & PERFORMANCE 30 DIAS */}
          <div className="bg-gradient-to-br from-zinc-900 via-zinc-900/90 to-zinc-950 border border-zinc-800 p-4 rounded-2xl shadow-xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Target size={16} className="text-emerald-400" />
                <h4 className="text-xs font-bold text-zinc-200 uppercase font-mono">
                  Prop Firm Target (Últimos 30 Dias)
                </h4>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
                Meta: ${propTarget.toLocaleString('pt-BR')}
              </span>
            </div>

            <div>
              <div className="flex justify-between text-[10px] font-mono mb-1">
                <span className="text-zinc-400">
                  Progresso do Desafio: <strong className={stats30d.realized_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}>
                    ${stats30d.realized_pnl.toLocaleString('pt-BR')}
                  </strong>
                </span>
                <span className="text-zinc-300 font-bold">{progressPct.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-zinc-950 h-2.5 rounded-full overflow-hidden border border-zinc-800">
                <div 
                  className="bg-gradient-to-r from-emerald-500 to-teal-400 h-full rounded-full transition-all duration-500"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>

            <div className="grid grid-cols-4 gap-2 pt-1 text-center">
              <div className="bg-zinc-950 p-2 rounded-xl border border-zinc-800/80">
                <span className="text-[8px] font-mono text-zinc-500 block uppercase">Net R (30D)</span>
                <strong className={`text-xs font-bold font-mono mt-0.5 block ${stats30d.net_r >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {stats30d.net_r >= 0 ? `+${stats30d.net_r}R` : `${stats30d.net_r}R`}
                </strong>
              </div>

              <div className="bg-zinc-950 p-2 rounded-xl border border-zinc-800/80">
                <span className="text-[8px] font-mono text-zinc-500 block uppercase">Win Rate (30D)</span>
                <strong className="text-xs font-bold font-mono text-zinc-100 mt-0.5 block">
                  {stats30d.win_rate}%
                </strong>
              </div>

              <div className="bg-zinc-950 p-2 rounded-xl border border-zinc-800/80">
                <span className="text-[8px] font-mono text-zinc-500 block uppercase">Trades (30D)</span>
                <strong className="text-xs font-bold font-mono text-zinc-300 mt-0.5 block">
                  {stats30d.total_trades} ({stats30d.wins}W/{stats30d.losses}L)
                </strong>
              </div>

              <div className="bg-zinc-950 p-2 rounded-xl border border-zinc-800/80">
                <span className="text-[8px] font-mono text-rose-400 block uppercase font-bold">Max DD (30D)</span>
                <strong className="text-xs font-bold font-mono text-rose-400 mt-0.5 block">
                  -${stats30d.max_drawdown_usd.toFixed(2)}
                </strong>
              </div>
            </div>
          </div>

          {/* 3. MODO OPERACIONAL COM VISÃO INDEPENDENTE POR ATIVO */}
          <div className="bg-zinc-900/90 border border-zinc-800 p-4 rounded-2xl shadow-xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu size={15} className="text-violet-400" />
                <h4 className="text-xs font-bold text-zinc-200 uppercase font-mono">
                  Estratégia Operacional em Execução
                </h4>
              </div>
              <span className="text-[10px] font-mono text-zinc-400">
                Break-Even: <strong className={activeStrategy.breakeven.includes("ATIVO") ? "text-emerald-400" : "text-zinc-500"}>{activeStrategy.breakeven}</strong>
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* PAINEL NASDAQ */}
              <div className="bg-zinc-950 p-3.5 rounded-xl border border-zinc-800/80 space-y-2">
                <div className="flex items-center justify-between border-b border-zinc-800/60 pb-1.5">
                  <strong className="text-xs text-zinc-200 font-mono">NASDAQ (US100)</strong>
                  <span className={`text-[8px] font-mono font-bold px-1.5 py-0.5 rounded border ${
                    activeStrategy.nasdaq.is_auto 
                      ? 'bg-violet-500/20 text-violet-300 border-violet-500/40' 
                      : 'bg-zinc-800 text-zinc-300 border-zinc-700'
                  }`}>
                    {activeStrategy.nasdaq.is_auto ? '🤖 AUTO IA (30D)' : '👤 MANUAL'}
                  </span>
                </div>
                
                <div className="space-y-1.5 text-[11px] font-mono">
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Perfil:</span>
                    <strong className="text-emerald-400">{formatProfileLabel(activeStrategy.nasdaq.profile)}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Entrada:</span>
                    <strong className="text-zinc-300">{activeStrategy.nasdaq.entry_type}</strong>
                  </div>
                  <div className="flex justify-between items-center pt-0.5">
                    <span className="text-zinc-500">Status:</span>
                    <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${
                      activeStrategy.nasdaq.status === 'AUTORIZADO'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}>
                      {activeStrategy.nasdaq.status}
                    </span>
                  </div>
                </div>
              </div>

              {/* PAINEL XAUUSD (GOLD) */}
              <div className="bg-zinc-950 p-3.5 rounded-xl border border-zinc-800/80 space-y-2">
                <div className="flex items-center justify-between border-b border-zinc-800/60 pb-1.5">
                  <strong className="text-xs text-zinc-200 font-mono">XAUUSD (GOLD)</strong>
                  <span className={`text-[8px] font-mono font-bold px-1.5 py-0.5 rounded border ${
                    activeStrategy.gold.is_auto 
                      ? 'bg-violet-500/20 text-violet-300 border-violet-500/40' 
                      : 'bg-zinc-800 text-zinc-300 border-zinc-700'
                  }`}>
                    {activeStrategy.gold.is_auto ? '🤖 AUTO IA (30D)' : '👤 MANUAL'}
                  </span>
                </div>

                <div className="space-y-1.5 text-[11px] font-mono">
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Perfil:</span>
                    <strong className="text-blue-400">{formatProfileLabel(activeStrategy.gold.profile)}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Entrada:</span>
                    <strong className="text-zinc-300">{activeStrategy.gold.entry_type}</strong>
                  </div>
                  <div className="flex justify-between items-center pt-0.5">
                    <span className="text-zinc-500">Status:</span>
                    <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${
                      activeStrategy.gold.status === 'AUTORIZADO'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}>
                      {activeStrategy.gold.status}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 4. CONTADORES REAIS DO DIA (TODAY'S PERFORMANCE) */}
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
              <div className="bg-zinc-950 p-2.5 rounded-xl border border-zinc-800/80">
                <span className="text-[8px] font-mono text-zinc-500 block uppercase">W / L</span>
                <strong className="text-xs font-bold font-mono text-zinc-200 mt-0.5 block">
                  <span className="text-emerald-400">{stats.wins}W</span> / <span className="text-rose-400">{stats.losses}L</span>
                </strong>
              </div>

              <div className="bg-zinc-950 p-2.5 rounded-xl border border-zinc-800/80">
                <span className="text-[8px] font-mono text-zinc-500 block uppercase">Win Rate</span>
                <strong className="text-xs font-bold font-mono text-zinc-100 mt-0.5 block">
                  {stats.win_rate}%
                </strong>
              </div>

              <div className="bg-zinc-950 p-2.5 rounded-xl border border-zinc-800/80">
                <span className="text-[8px] font-mono text-zinc-500 block uppercase">Realized PnL</span>
                <strong className={`text-xs font-black font-mono mt-0.5 block ${stats.realized_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                  {stats.realized_pnl >= 0 ? `+$${stats.realized_pnl.toFixed(2)}` : `-$${Math.abs(stats.realized_pnl).toFixed(2)}`}
                </strong>
              </div>

              <div className="bg-zinc-950 p-2.5 rounded-xl border border-zinc-800/80">
                <span className="text-[8px] font-mono text-amber-400 block uppercase font-bold">Net R (Hoje)</span>
                <strong className={`text-xs font-black font-mono mt-0.5 block ${stats.net_r >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                  {stats.net_r >= 0 ? `+${stats.net_r}R` : `${stats.net_r}R`}
                </strong>
              </div>
            </div>

            {/* Posições Ativas */}
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

            {/* Histórico Recente */}
            {stats.closed_trades && stats.closed_trades.length > 0 && (
              <div>
                <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider block mb-1.5">
                  Recent Closed Deals
                </span>
                <div className="space-y-1 max-h-32 overflow-y-auto no-scrollbar pr-1">
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
        </div>

        {/* ============================================================== */}
        {/* COLUNA DIREITA (RADAR, BACKTEST & CONTROLES) — 5 Colunas em Notebook */}
        {/* ============================================================== */}
        <div className="space-y-4 lg:col-span-5 xl:col-span-5">
          
          {/* 5. PLACAR PNL & SALDO DO DIA */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-zinc-900/90 border border-zinc-800 p-3.5 rounded-2xl shadow-lg">
              <span className="text-[10px] font-mono text-zinc-500 uppercase block">Account Balance</span>
              <strong className="text-sm lg:text-base font-bold text-zinc-200 font-mono block mt-1">
                ${status?.account_balance || '0.00'}
              </strong>
            </div>

            <div className="bg-zinc-900/90 border border-zinc-800 p-3.5 rounded-2xl shadow-lg">
              <span className="text-[10px] font-mono text-zinc-500 uppercase block">Session PNL (Hoje)</span>
              <strong className={`text-sm lg:text-base font-black font-mono block mt-1 ${pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {pnl >= 0 ? `+$${pnl.toFixed(2)}` : `-$${Math.abs(pnl).toFixed(2)}`}
              </strong>
            </div>
          </div>

          {/* 6. RADAR DO STRATEGY SCOUT (30D) */}
          <div className="bg-zinc-900/90 border border-zinc-800 p-4 rounded-2xl shadow-xl space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Radar size={15} className="text-amber-400 animate-pulse" />
                <h4 className="text-xs font-bold text-zinc-200 uppercase font-mono">Strategy Scout (30D)</h4>
              </div>
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-amber-300 border border-amber-500/20">
                Radar Institucional
              </span>
            </div>

            {scoutDirectives ? (
              <div className="space-y-2">
                {/* NASDAQ CARD */}
                <div className="bg-zinc-950 p-2.5 rounded-xl border border-zinc-800/80 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-zinc-300 font-mono">NASDAQ (US100)</span>
                    <span className={`text-[8px] font-mono font-bold px-1.5 py-0.2 rounded border ${
                      scoutDirectives.NASDAQ?.should_trade 
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}>
                      {scoutDirectives.NASDAQ?.should_trade ? 'AUTORIZADO' : 'STAND-BY'}
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-zinc-400">
                    Sugerido: <strong className="text-zinc-200">{formatProfileLabel(scoutDirectives.NASDAQ?.recommended_profile)}</strong>
                  </div>
                  <div className="text-[9px] font-mono text-zinc-500 flex justify-between">
                    <span>Score: <strong className="text-zinc-300">{scoutDirectives.NASDAQ?.prop_score}</strong></span>
                    <span>WinRate: <strong className="text-zinc-300">{scoutDirectives.NASDAQ?.win_rate}%</strong></span>
                  </div>
                </div>

                {/* GOLD CARD */}
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
                    Sugerido: <strong className="text-zinc-200">{formatProfileLabel(scoutDirectives.GOLD?.recommended_profile)}</strong>
                  </div>
                  <div className="text-[9px] font-mono text-zinc-500 flex justify-between">
                    <span>Score: <strong className="text-zinc-300">{scoutDirectives.GOLD?.prop_score}</strong></span>
                    <span>WinRate: <strong className="text-zinc-300">{scoutDirectives.GOLD?.win_rate}%</strong></span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-3 bg-zinc-950/60 rounded-xl text-center text-[10px] font-mono text-zinc-500">
                Strategy Scout calibrando permutações de 30 dias...
              </div>
            )}
          </div>

          {/* 7. SANDBOX BACKTEST */}
          <div className="bg-gradient-to-br from-zinc-900 to-zinc-950 border border-zinc-800/80 p-4 rounded-2xl space-y-3 shadow-xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles size={15} className="text-amber-400" />
                <h4 className="text-xs font-bold text-zinc-200 uppercase font-mono">Sandbox Backtest</h4>
              </div>
              {latestBacktest && !isBacktestLoading && (
                <button
                  onClick={() => setShowReportModal(true)}
                  className="text-[10px] font-mono font-bold text-violet-400 hover:text-violet-300 underline flex items-center gap-1">
                  Abrir Relatório <ArrowRight size={10} />
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
              <div className="grid grid-cols-5 gap-1.5">
                {[
                  { label: 'Hoje', val: 0 },
                  { label: '1D', val: 1 },
                  { label: '7D', val: 7 },
                  { label: '15D', val: 15 },
                  { label: '30D', val: 30 }
                ].map(({ label, val }) => (
                  <button
                    key={val}
                    onClick={() => setSelectedDays(val)}
                    className={`py-1 rounded-lg text-xs font-mono font-bold border transition-all ${
                      selectedDays === val
                        ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300 shadow-sm'
                        : 'bg-zinc-950 border-zinc-800/80 text-zinc-500 hover:text-zinc-300'
                    }`}>
                    {label}
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
                  <span>Calculando Execução ({selectedAsset} • {formatDaysLabel(selectedDays)})...</span>
                </>
              ) : (
                <>
                  <BarChart3 size={14} />
                  <span>Executar Sandbox ({selectedAsset} • {formatDaysLabel(selectedDays)})</span>
                </>
              )}
            </button>
          </div>

          {/* 8. TRAVA DE EMERGÊNCIA */}
          <button
            onClick={() => setShowEmergencyModal(true)}
            className="w-full py-3 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 text-rose-300 rounded-xl text-xs font-bold font-mono uppercase tracking-wider flex items-center justify-center gap-2 transition-all">
            <Power size={14} /> Trava de Emergência (Zerar Tudo)
          </button>
        </div>
      </div>

      {/* 9. MODAL DO RELATÓRIO REALISTA EXPANSIVO */}
      {showReportModal && (
        <div className="fixed inset-0 bg-black/85 backdrop-blur-sm z-50 flex items-center justify-center p-2 sm:p-4">
          <div className="bg-zinc-900 border border-zinc-800 w-full max-w-xl lg:max-w-2xl xl:max-w-3xl rounded-2xl p-4 sm:p-6 shadow-2xl relative space-y-4 max-h-[92vh] overflow-y-auto no-scrollbar">
            <button
              onClick={() => setShowReportModal(false)}
              className="absolute top-4 right-4 text-zinc-500 hover:text-zinc-200">
              <X size={18} />
            </button>

            {isBacktestLoading ? (
              <div className="py-12 flex flex-col items-center justify-center text-center space-y-3">
                <Loader2 size={36} className="animate-spin text-amber-400" />
                <div>
                  <h3 className="text-sm font-bold text-zinc-100 font-mono">Processando Execução Realista</h3>
                  <p className="text-[11px] text-zinc-400 font-mono mt-1">
                    Simulando ordens sequenciais, spreads dinâmicos e comissões da mesa...
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
                      {latestBacktest.symbol} Expectativa Realista ({formatDaysLabel(latestBacktest.days)})
                    </h3>
                    <div className="flex items-center gap-2 text-[10px] text-zinc-400 font-mono mt-0.5">
                      <span>Mapeados: <strong className="text-zinc-300">{latestBacktest.setups_mapped}</strong></span>
                      <span>•</span>
                      <span>Executados: <strong className="text-emerald-400 font-bold">{latestBacktest.trades_executed}</strong></span>
                      <span>•</span>
                      <span>Risco: ${latestBacktest.base_risk || currentRiskBase}</span>
                    </div>
                  </div>
                </div>

                <div className="bg-emerald-950/20 border border-emerald-500/30 p-2.5 rounded-xl flex items-center justify-between text-[10px] font-mono text-emerald-300">
                  <div className="flex items-center gap-2">
                    <ShieldCheck size={16} className="text-emerald-400" />
                    <span>Fricções Deduzidas: 1 Trade Sequencial • Cooldown 10m • Spread • Slippage • Taxas FTMO</span>
                  </div>
                  <span className="text-[9px] bg-emerald-500/20 px-1.5 py-0.5 rounded font-bold">100% Real</span>
                </div>

                <div className="grid grid-cols-2 gap-1 bg-zinc-950 p-1 rounded-xl border border-zinc-800 text-[11px] font-mono font-bold">
                  <button
                    onClick={() => setBacktestViewTab('raio_x')}
                    className={`py-1.5 rounded-lg transition-all flex items-center justify-center gap-1.5 ${
                      backtestViewTab === 'raio_x' ? 'bg-zinc-800 text-amber-300 shadow' : 'text-zinc-500 hover:text-zinc-300'
                    }`}>
                    <TableProperties size={13} /> Matriz Realista (Ranking)
                  </button>
                  <button
                    onClick={() => setBacktestViewTab('compare')}
                    className={`py-1.5 rounded-lg transition-all ${
                      backtestViewTab === 'compare' ? 'bg-zinc-800 text-zinc-100 shadow' : 'text-zinc-500 hover:text-zinc-300'
                    }`}>
                    Visão Clássica A/B
                  </button>
                </div>

                {backtestViewTab === 'raio_x' && latestBacktest.raio_x && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-[10px] font-mono text-zinc-400 px-1">
                      <span>Projeção Líquida de Saque em Mesa:</span>
                      <span className="text-amber-400 font-bold">Ordenado por PnL Real</span>
                    </div>

                    <div className="space-y-1.5 max-h-[50vh] overflow-y-auto no-scrollbar pr-1">
                      {latestBacktest.raio_x.map((item, idx) => (
                        <div
                          key={item.id}
                          className={`p-2.5 rounded-xl border text-[11px] font-mono flex items-center justify-between transition-all ${
                            idx === 0
                              ? 'bg-amber-500/10 border-amber-500/40 shadow-sm'
                              : 'bg-zinc-950 border-zinc-800/80 hover:border-zinc-700'
                          }`}>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-1.5 mb-1">
                              {idx === 0 && (
                                <span className="text-[9px] font-black px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                  #1 MELHOR
                                </span>
                              )}
                              <strong className="text-zinc-200">{item.profile}</strong>
                              <span className="text-zinc-500">•</span>
                              <span className="text-zinc-300 font-semibold">{item.entry}</span>
                              <span className="text-zinc-500">•</span>
                              <span className={item.with_be ? 'text-emerald-400' : 'text-blue-400'}>{item.be_label}</span>
                              <span className="text-zinc-500">•</span>
                              <span className="text-zinc-400">{item.sweep}</span>
                            </div>

                            <div className="flex items-center gap-3 text-[10px] text-zinc-400">
                              <span>Trades Reais: <strong className="text-zinc-200">{item.trades_executed}</strong></span>
                              <span>Win: <strong className="text-zinc-200">{item.win_rate}%</strong> ({item.wins}W / {item.losses}L)</span>
                              {item.be_count > 0 && <span>BEs: <strong className="text-zinc-300">{item.be_count}</strong></span>}
                            </div>
                          </div>

                          <div className="text-right flex items-center gap-2.5">
                            <div>
                              <strong className={`block text-xs font-black ${item.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {item.net_r >= 0 ? `+${item.net_r}R` : `${item.net_r}R`}
                              </strong>
                              <span className={`text-[10px] font-bold ${item.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                ${item.pnl}
                              </span>
                            </div>

                            <button
                              onClick={() => applyCustomStrategy(item)}
                              title={`Aplicar apenas no ${latestBacktest.symbol}`}
                              className="px-2 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-[10px] text-zinc-200 font-bold">
                              Usar
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

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
                            <span className="text-[9px] font-mono text-zinc-500">Projeção com Fricção</span>
                          </div>

                          <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
                            <div className="bg-zinc-900/60 p-2 rounded-lg border border-zinc-800/50">
                              <span className="text-[9px] text-emerald-400 font-bold block mb-1">COM BREAK-EVEN</span>
                              <div className="space-y-0.5 text-zinc-400">
                                <div>Win: <strong className="text-zinc-200">{withBeData.rate}%</strong> ({withBeData.wins}W / {withBeData.losses}L)</div>
                                {withBeData.be_count && <div>BEs: <strong className="text-zinc-300">{withBeData.be_count}</strong></div>}
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

                <div className="bg-zinc-950 p-3 rounded-xl border border-zinc-800/80 flex items-center justify-between">
                  <div className="min-w-0 flex-1 pr-2">
                    <span className="text-[9px] text-zinc-500 font-mono uppercase block">Melhor Estrutura Realista</span>
                    <strong className="text-xs font-bold text-amber-300 font-mono block truncate">
                      {latestBacktest.recommended}
                    </strong>
                  </div>
                  {latestBacktest.raio_x && latestBacktest.raio_x[0] && (
                    <button
                      onClick={() => applyCustomStrategy(latestBacktest.raio_x[0])}
                      className="px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-bold font-mono transition-all flex items-center gap-1.5 shadow-md shrink-0">
                      <CheckCircle2 size={14} /> Aplicar #1
                    </button>
                  )}
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}

      {/* 10. MODAL EMERGÊNCIA */}
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