import React, { useState, useEffect, useRef } from 'react';
import { createClient } from '@supabase/supabase-js';
import { Zap, LayoutDashboard, Sliders, ScrollText, Volume2, VolumeX } from 'lucide-react';
import Dashboard from './components/Dashboard';
import ControlPanel from './components/ControlPanel';
import LiveLogs from './components/LiveLogs';

const SUPABASE_URL = "https://wvyllpbqtahxrqsjjzgp.supabase.co";
const SUPABASE_ANON = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind2eWxscGJxdGFoeHJxc2pqemdwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTEyMzU3NzEsImV4cCI6MjEwNjgxMTc3MX0.7qIsu2oZermD9uPA8ggSfNZuKDZH-_ifs2jJjeTX6XM";
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON);

export default function App() {
  const [tab, setTab] = useState('dashboard');
  const [status, setStatus] = useState({ is_online: false, pnl_today: 0, current_profile: 'tatico' });
  const [settings, setSettings] = useState(null);
  const [logs, setLogs] = useState([]);
  const [soundEnabled, setSoundEnabled] = useState(false);

  // Estados do Modal e Backtest
  const [latestBacktest, setLatestBacktest] = useState(null);
  const [showReportModal, setShowReportModal] = useState(false);
  const [isBacktestLoading, setIsBacktestLoading] = useState(false);
  const pollTimerRef = useRef(null);

  useEffect(() => {
    supabase.from('copilot_status').select('*').eq('id', 1).single()
      .then(r => r.data && setStatus(r.data));

    supabase.from('copilot_settings').select('*').eq('id', 1).single()
      .then(r => r.data && setSettings(r.data));

    supabase.from('copilot_logs').select('*').order('created_at', { ascending: false }).limit(40)
      .then(r => {
        if (r.data) {
          setLogs(r.data);
          const reportLog = r.data.find(l => l.message && l.message.startsWith('BACKTEST_RESULT:'));
          if (reportLog) {
            try {
              const parsed = JSON.parse(reportLog.message.replace('BACKTEST_RESULT:', ''));
              setLatestBacktest(parsed);
            } catch {}
          }
        }
      });

    const channel = supabase.channel('copilot_realtime_sync')
      .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'copilot_status' }, p => setStatus(p.new))
      .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'copilot_settings' }, p => setSettings(p.new))
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'copilot_logs' }, p => {
        setLogs(prev => [p.new, ...prev.slice(0, 45)]);

        // Se chegar o resultado do Backtest via Realtime
        if (p.new.message && p.new.message.startsWith('BACKTEST_RESULT:')) {
          try {
            const parsed = JSON.parse(p.new.message.replace('BACKTEST_RESULT:', ''));
            setLatestBacktest(parsed);
            setIsBacktestLoading(false);
            setShowReportModal(true);
            if (pollTimerRef.current) clearInterval(pollTimerRef.current);
          } catch {}
        }

        if (soundEnabled && p.new.level === 'SUCCESS') playAlertSound();
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, [soundEnabled]);

  const handleUpdateSettings = async (newFields) => {
    setSettings(prev => ({ ...prev, ...newFields }));
    await supabase.from('copilot_settings').update(newFields).eq('id', 1);
  };

  const handleEmergencyStop = async () => {
    await supabase.from('copilot_logs').insert({
      message: "EMERGENCY_STOP_TRIGGERED: Cancelling orders and flattening positions",
      level: "DANGER"
    });
  };

  const handleRunBacktest = async (days = 2, asset = 'US100') => {
    const symbolTarget = asset === 'US100' ? 'US100.cash' : 'XAUUSD';
    
    // Abre o modal de imediato em modo de carregamento
    setIsBacktestLoading(true);
    setShowReportModal(true);

    await supabase.from('copilot_logs').insert({
      symbol: symbolTarget,
      message: `COMMAND: RUN_BACKTEST:${symbolTarget}:${days}`,
      level: "INFO"
    });

    // Fallback: faz polling a cada 1.5s durante 8s para garantir a resposta caso o websocket falhe
    let attempts = 0;
    if (pollTimerRef.current) clearInterval(pollTimerRef.current);

    pollTimerRef.current = setInterval(async () => {
      attempts++;
      const { data } = await supabase.from('copilot_logs')
        .select('*')
        .like('message', 'BACKTEST_RESULT:%')
        .order('created_at', { ascending: false })
        .limit(1);

      if (data && data.length > 0) {
        try {
          const parsed = JSON.parse(data[0].message.replace('BACKTEST_RESULT:', ''));
          setLatestBacktest(parsed);
          setIsBacktestLoading(false);
          clearInterval(pollTimerRef.current);
        } catch {}
      }

      if (attempts > 6) {
        setIsBacktestLoading(false);
        clearInterval(pollTimerRef.current);
      }
    }, 1500);
  };

  const handleClearLogs = async () => {
    await supabase.from('copilot_logs').delete().gt('id', 0);
    setLogs([]);
  };

  const playAlertSound = () => {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.setValueAtTime(880, ctx.currentTime);
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
      osc.start();
      osc.stop(ctx.currentTime + 0.3);
    } catch {}
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col items-center p-3 sm:p-6 antialiased select-none font-sans">
      <header className="w-full max-w-md bg-zinc-900/90 border border-zinc-800 rounded-2xl p-3.5 mb-3 flex items-center justify-between shadow-xl">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-violet-500/10 border border-violet-500/20 text-violet-400 rounded-xl">
            <Zap size={18} />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-wide">COPILOT VISUAL</h1>
            <span className="text-[10px] text-zinc-400 font-mono">HFT FVG • Institutional</span>
          </div>
        </div>

        <button
          onClick={() => setSoundEnabled(!soundEnabled)}
          className={`p-2 rounded-xl border transition-colors ${
            soundEnabled ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-zinc-800 text-zinc-400 border-zinc-700'
          }`}>
          {soundEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
        </button>
      </header>

      <nav className="w-full max-w-md grid grid-cols-3 gap-1.5 p-1 bg-zinc-900 border border-zinc-800 rounded-xl mb-4 text-xs font-bold font-mono">
        <button
          onClick={() => setTab('dashboard')}
          className={`py-2 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
            tab === 'dashboard' ? 'bg-zinc-800 text-zinc-100 shadow' : 'text-zinc-500 hover:text-zinc-300'
          }`}>
          <LayoutDashboard size={14} /> Overview
        </button>
        <button
          onClick={() => setTab('controls')}
          className={`py-2 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
            tab === 'controls' ? 'bg-zinc-800 text-zinc-100 shadow' : 'text-zinc-500 hover:text-zinc-300'
          }`}>
          <Sliders size={14} /> Profiles
        </button>
        <button
          onClick={() => setTab('logs')}
          className={`py-2 rounded-lg flex items-center justify-center gap-1.5 transition-all ${
            tab === 'logs' ? 'bg-zinc-800 text-zinc-100 shadow' : 'text-zinc-500 hover:text-zinc-300'
          }`}>
          <ScrollText size={14} /> Feed
        </button>
      </nav>

      <main className="w-full max-w-md flex-1">
        {tab === 'dashboard' && (
          <Dashboard
            status={status}
            settings={settings}
            onEmergencyStop={handleEmergencyStop}
            onRunBacktest={handleRunBacktest}
            onUpdateSettings={handleUpdateSettings}
            latestBacktest={latestBacktest}
            showReportModal={showReportModal}
            setShowReportModal={setShowReportModal}
            isBacktestLoading={isBacktestLoading}
          />
        )}
        {tab === 'controls' && (
          <ControlPanel
            settings={settings}
            onUpdateSettings={handleUpdateSettings}
          />
        )}
        {tab === 'logs' && (
          <LiveLogs
            logs={logs}
            onClear={handleClearLogs}
          />
        )}
      </main>
    </div>
  );
}