import React, { useState } from 'react';
import { UserCheck, Power, Sparkles, BarChart3, AlertTriangle, X, CheckCircle2, Trophy, ArrowRight, Loader2, ArrowUpRight, ArrowDownRight, Activity, Clock } from 'lucide-react';

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
  const [selectedDays, setSelectedDays] = useState(2);

  const currentRiskBase = Number(settings?.risk_per_trade || 50);
  const stats = status?.today_stats || {
    total_trades: 0,
    wins: 0,
    losses: 0,
    win_rate: 0,
    realized_pnl: 0,
    open_count: 0,
    open_positions: [],
    closed_trades: []
  };

  const handleBacktestClick = () => {
    onRunBacktest(selectedDays, selectedAsset);
  };

  const applyRecommendedProfile = (recommended) => {
    const profileKey = recommended === 'GUARDIAN' ? 'guardiao' : recommended === 'SNIPER' ? 'sniper' : 'tatico';
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

      {/* 2. PLACAR PNL & SALDO */}
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

      {/* 3. CONTADORES REAIS DO DIA (HOJE NA FTMO) */}
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

        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="bg-zinc-950 p-2.5 rounded-xl border border-zinc-800/80">
            <span className="text-[9px] font-mono text-zinc-500 block uppercase">Win / Loss</span>
            <strong className="text-xs font-bold font-mono text-zinc-200 mt-0.5 block">
              <span className="text-emerald-400">{stats.wins}W</span> / <span className="text-rose-400">{stats.losses}L</span>
            </strong>
          </div>

          <div className="bg-zinc-950 p-2.5 rounded-xl border border-zinc-800/80">
            <span className="text-[9px] font-mono text-zinc-500 block uppercase">Win Rate</span>
            <strong className="text-xs font-bold font-mono text-zinc-100 mt-0.5 block">
              {stats.win_rate}%
            </strong>
          </div>

          <div className="bg-zinc-950 p-2.5 rounded-xl border border-zinc-800/80">
            <span className="text-[9px] font-mono text-zinc-500 block uppercase">Realized PnL</span>
            <strong className={`text-xs font-black font-mono mt-0.5 block ${stats.realized_pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
              {stats.realized_pnl >= 0 ? `+$${stats.realized_pnl.toFixed(2)}` : `-$${Math.abs(stats.realized_pnl).toFixed(2)}`}
            </strong>
          </div>
        </div>

        {/* POSIÇÕES ABERTAS AGORA (AO VIVO) */}
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
              No open positions. Monitoring market for fresh FVGs...
            </div>
          )}
        </div>

        {/* ÚLTIMOS TRADES FECHADOS HOJE */}
        {stats.closed_trades && stats.closed_trades.length > 0 && (
          <div>
            <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider block mb-1.5">
              Recent Closed Trades Today
            </span>
            <div className="space-y-1 max-h-28 overflow-y-auto pr-1">
              {stats.closed_trades.map((deal) => (
                <div key={deal.ticket} className="bg-zinc-950/80 border border-zinc-800/50 p-2 rounded-lg flex items-center justify-between text-[10px] font-mono">
                  <div className="flex items-center gap-1.5">
                    <Clock size={10} className="text-zinc-500" />
                    <span className="text-zinc-400">{deal.time}</span>
                    <strong className="text-zinc-300">{deal.symbol}</strong>
                    <span className={deal.type === 'BUY' ? 'text-emerald-400' : 'text-rose-400'}>({deal.type})</span>
                  </div>
                  <strong className={deal.profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                    {deal.profit >= 0 ? `+$${deal.profit.toFixed(2)}` : `-$${Math.abs(deal.profit).toFixed(2)}`}
                  </strong>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 4. SANDBOX BACKTEST */}
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
              View Latest Report <ArrowRight size={10} />
            </button>
          )}
        </div>

        <div>
          <span className="text-[10px] font-mono text-zinc-400 block mb-1.5 uppercase">Target Asset</span>
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
          <span className="text-[10px] font-mono text-zinc-400 block mb-1.5 uppercase">Lookback Window (M5 ➔ M1 Execution)</span>
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
              <span>Scanning M1 Execution for {selectedAsset} ({selectedDays}D)...</span>
            </>
          ) : (
            <>
              <BarChart3 size={14} />
              <span>Run {selectedAsset} Backtest ({selectedDays}D)</span>
            </>
          )}
        </button>
      </div>

      {/* 5. BOTÃO TRAVA DE EMERGÊNCIA */}
      <button
        onClick={() => setShowEmergencyModal(true)}
        className="w-full py-3 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 text-rose-300 rounded-xl text-xs font-bold font-mono uppercase tracking-wider flex items-center justify-center gap-2 transition-all">
        <Power size={14} /> Emergency Stop (Flatten & Cancel)
      </button>

      {/* 6. MODAL DO BACKTEST */}
      {showReportModal && (
        <div className="fixed inset-0 bg-black/85 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 w-full max-w-md rounded-2xl p-5 shadow-2xl relative animate-in fade-in zoom-in-95 duration-150 space-y-4">
            <button
              onClick={() => setShowReportModal(false)}
              className="absolute top-4 right-4 text-zinc-500 hover:text-zinc-200">
              <X size={18} />
            </button>

            {isBacktestLoading ? (
              <div className="py-10 flex flex-col items-center justify-center text-center space-y-3">
                <Loader2 size={36} className="animate-spin text-amber-400" />
                <div>
                  <h3 className="text-sm font-bold text-zinc-100 font-mono">Simulating M1 Scalping Execution</h3>
                  <p className="text-[11px] text-zinc-400 font-mono mt-1">
                    Analyzing candle-by-candle touch, Stop Loss and Target expansions...
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
                      {latestBacktest.symbol} Backtest Report
                    </h3>
                    <span className="text-[10px] text-zinc-400 font-mono">
                      {latestBacktest.days} Days Window • {latestBacktest.setups} Setups Formed • Base Risk: ${latestBacktest.base_risk || currentRiskBase}
                    </span>
                  </div>
                </div>

                <div className="space-y-2.5">
                  {latestBacktest.sniper && (
                    <div className={`p-3 rounded-xl border ${
                      latestBacktest.recommended === 'SNIPER'
                        ? 'bg-amber-500/10 border-amber-500/50 shadow-lg shadow-amber-950/30'
                        : 'bg-zinc-950 border-zinc-800/80'
                    }`}>
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-2">
                          <strong className="text-xs font-bold font-mono text-amber-300">SNIPER (1:4 R:R)</strong>
                          {latestBacktest.recommended === 'SNIPER' && (
                            <span className="text-[9px] bg-amber-500/20 text-amber-300 px-1.5 py-0.2 rounded font-bold font-mono">
                              BEST PNL
                            </span>
                          )}
                        </div>
                        <span className="text-xs font-black font-mono text-zinc-200">
                          {latestBacktest.sniper.rate}% Win
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-3 gap-2 text-[10px] font-mono text-zinc-400 bg-zinc-900/60 p-2 rounded-lg border border-zinc-800/60">
                        <div>
                          <span className="text-zinc-500 block">W / L</span>
                          <strong className="text-zinc-200">{latestBacktest.sniper.wins}W / {latestBacktest.sniper.losses}L</strong>
                        </div>
                        <div>
                          <span className="text-zinc-500 block">Net R</span>
                          <strong className={latestBacktest.sniper.net_r >= 0 ? "text-emerald-400" : "text-rose-400"}>
                            {latestBacktest.sniper.net_r >= 0 ? `+${latestBacktest.sniper.net_r}R` : `${latestBacktest.sniper.net_r}R`}
                          </strong>
                        </div>
                        <div className="text-right">
                          <span className="text-zinc-500 block">Est. PNL</span>
                          <strong className={`text-xs font-black ${latestBacktest.sniper.pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                            {latestBacktest.sniper.pnl >= 0 ? `+$${latestBacktest.sniper.pnl}` : `-$${Math.abs(latestBacktest.sniper.pnl)}`}
                          </strong>
                        </div>
                      </div>
                    </div>
                  )}

                  {latestBacktest.tatico && (
                    <div className={`p-3 rounded-xl border ${
                      latestBacktest.recommended === 'TACTICAL'
                        ? 'bg-blue-500/10 border-blue-500/50 shadow-lg shadow-blue-950/30'
                        : 'bg-zinc-950 border-zinc-800/80'
                    }`}>
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-2">
                          <strong className="text-xs font-bold font-mono text-blue-300">TACTICAL (1:2.5 R:R)</strong>
                          {latestBacktest.recommended === 'TACTICAL' && (
                            <span className="text-[9px] bg-blue-500/20 text-blue-300 px-1.5 py-0.2 rounded font-bold font-mono">
                              BEST PNL
                            </span>
                          )}
                        </div>
                        <span className="text-xs font-black font-mono text-zinc-200">
                          {latestBacktest.tatico.rate}% Win
                        </span>
                      </div>

                      <div className="grid grid-cols-3 gap-2 text-[10px] font-mono text-zinc-400 bg-zinc-900/60 p-2 rounded-lg border border-zinc-800/60">
                        <div>
                          <span className="text-zinc-500 block">W / L</span>
                          <strong className="text-zinc-200">{latestBacktest.tatico.wins}W / {latestBacktest.tatico.losses}L</strong>
                        </div>
                        <div>
                          <span className="text-zinc-500 block">Net R</span>
                          <strong className={latestBacktest.tatico.net_r >= 0 ? "text-emerald-400" : "text-rose-400"}>
                            {latestBacktest.tatico.net_r >= 0 ? `+${latestBacktest.tatico.net_r}R` : `${latestBacktest.tatico.net_r}R`}
                          </strong>
                        </div>
                        <div className="text-right">
                          <span className="text-zinc-500 block">Est. PNL</span>
                          <strong className={`text-xs font-black ${latestBacktest.tatico.pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                            {latestBacktest.tatico.pnl >= 0 ? `+$${latestBacktest.tatico.pnl}` : `-$${Math.abs(latestBacktest.tatico.pnl)}`}
                          </strong>
                        </div>
                      </div>
                    </div>
                  )}

                  {latestBacktest.guardiao && (
                    <div className={`p-3 rounded-xl border ${
                      latestBacktest.recommended === 'GUARDIAN'
                        ? 'bg-emerald-500/10 border-emerald-500/50 shadow-lg shadow-emerald-950/30'
                        : 'bg-zinc-950 border-zinc-800/80'
                    }`}>
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-2">
                          <strong className="text-xs font-bold font-mono text-emerald-300">GUARDIAN (1:1.5 R:R)</strong>
                          {latestBacktest.recommended === 'GUARDIAN' && (
                            <span className="text-[9px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.2 rounded font-bold font-mono">
                              BEST PNL
                            </span>
                          )}
                        </div>
                        <span className="text-xs font-black font-mono text-zinc-200">
                          {latestBacktest.guardiao.rate}% Win
                        </span>
                      </div>

                      <div className="grid grid-cols-3 gap-2 text-[10px] font-mono text-zinc-400 bg-zinc-900/60 p-2 rounded-lg border border-zinc-800/60">
                        <div>
                          <span className="text-zinc-500 block">W / L</span>
                          <strong className="text-zinc-200">{latestBacktest.guardiao.wins}W / {latestBacktest.guardiao.losses}L</strong>
                        </div>
                        <div>
                          <span className="text-zinc-500 block">Net R</span>
                          <strong className={latestBacktest.guardiao.net_r >= 0 ? "text-emerald-400" : "text-rose-400"}>
                            {latestBacktest.guardiao.net_r >= 0 ? `+${latestBacktest.guardiao.net_r}R` : `${latestBacktest.guardiao.net_r}R`}
                          </strong>
                        </div>
                        <div className="text-right">
                          <span className="text-zinc-500 block">Est. PNL</span>
                          <strong className={`text-xs font-black ${latestBacktest.guardiao.pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                            {latestBacktest.guardiao.pnl >= 0 ? `+$${latestBacktest.guardiao.pnl}` : `-$${Math.abs(latestBacktest.guardiao.pnl)}`}
                          </strong>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="bg-zinc-950 p-3 rounded-xl border border-zinc-800/80 flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-zinc-500 font-mono uppercase block">Recommended Choice</span>
                    <strong className="text-xs font-bold text-emerald-400 font-mono">
                      {latestBacktest.recommended} (Max Net PNL)
                    </strong>
                  </div>
                  <button
                    onClick={() => applyRecommendedProfile(latestBacktest.recommended)}
                    className="px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-bold font-mono transition-all flex items-center gap-1.5 shadow-md">
                    <CheckCircle2 size={14} /> Apply Profile
                  </button>
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}

      {/* 7. MODAL EMERGÊNCIA */}
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
                <h3 className="text-sm font-bold text-zinc-100 font-mono">Emergency Stop</h3>
                <span className="text-[10px] text-zinc-400 font-mono">Immediate execution</span>
              </div>
            </div>

            <p className="text-xs text-zinc-300 mb-5 leading-relaxed bg-zinc-950/60 p-3 rounded-xl border border-zinc-800/60">
              This will immediately cancel all pending orders and close all open positions on MetaTrader 5.
            </p>

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setShowEmergencyModal(false)}
                className="py-2.5 rounded-xl border border-zinc-800 bg-zinc-800/60 hover:bg-zinc-800 text-xs font-bold text-zinc-300">
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowEmergencyModal(false);
                  onEmergencyStop();
                }}
                className="py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-xs font-bold text-white shadow-lg shadow-rose-900/50">
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}