# strategy_scout.py — Agente de Inteligência Walk-Forward com Histórico Cronológico
import time
import threading
import MetaTrader5 as mt5
from datetime import datetime

from mt5_core import FVGDetector, InstitutionalSessionFilter, VisionLiquidityAnalyzer

class StrategyScout:
    def __init__(self, engine, supabase_sync, eval_interval_seconds=3600):
        self.engine = engine
        self.sync = supabase_sync
        self.interval = eval_interval_seconds
        self.is_running = False
        self.thread = None
        
        self.active_directives = {
            "NASDAQ": {"use_ce_50": True, "require_sweep": False, "recommended_profile": "tatico", "prop_score": 0.0, "should_trade": True},
            "GOLD": {"use_ce_50": True, "require_sweep": False, "recommended_profile": "tatico", "prop_score": 0.0, "should_trade": True}
        }

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            print("🔭 [STRATEGY SCOUT] Processo paralelo iniciado com sucesso.")

    def _run_loop(self):
        time.sleep(5)
        while self.is_running:
            try:
                self.run_full_evaluation()
            except Exception as e:
                print(f"⚠️ [STRATEGY SCOUT] Falha na rodada de calibração: {e}")

            time.sleep(self.interval)

    def run_full_evaluation(self, days=2, base_risk=50.0):
        for category in ["NASDAQ", "GOLD"]:
            symbol = self.engine.resolve_symbol(category)
            if not symbol:
                continue

            best_directive = self._evaluate_symbol_matrix(symbol, days, base_risk)
            if best_directive:
                self.active_directives[category] = best_directive
                status_trade = "AUTORIZADO" if best_directive["should_trade"] else "STAND-BY"
                msg = (
                    f"DIRETRIZ {category}: {best_directive['recommended_profile'].upper()} [{status_trade}] | "
                    f"50%_CE={best_directive['use_ce_50']} | Sweep={best_directive['require_sweep']} | "
                    f"Score={best_directive['prop_score']:.1f} (WinRate: {best_directive['win_rate']}%)"
                )
                print(f"🎯 [SCOUT RECOMMENDATION] {msg}")
                self.sync.add_log(symbol, msg, "SUCCESS" if best_directive["should_trade"] else "WARN")

    def _evaluate_symbol_matrix(self, symbol, days, base_risk):
        total_m5 = int(days) * 240
        total_m1 = int(days) * 1440

        df_m5 = self.engine.get_candles(symbol, mt5.TIMEFRAME_M5, total_m5)
        df_m1 = self.engine.get_candles(symbol, mt5.TIMEFRAME_M1, total_m1)

        if df_m5 is None or df_m1 is None:
            return None

        is_nasdaq = "US100" in symbol or "NAS" in symbol or "USTEC" in symbol
        min_stop_points = 5.0 if is_nasdaq else 1.2
        max_risk = 30.0 if is_nasdaq else 4.5

        detector = FVGDetector()
        vision = VisionLiquidityAnalyzer()
        
        # USA TODOS OS SETUPS CRONOLÓGICOS (Fim do descarte indevido)
        fvgs = detector.find_all_historical_fvgs(df_m5, symbol)

        m1_highs = df_m1['high'].values
        m1_lows = df_m1['low'].values
        m1_times = df_m1['time'].values

        combinations = [
            {"use_ce_50": True, "require_sweep": True},
            {"use_ce_50": True, "require_sweep": False},
            {"use_ce_50": False, "require_sweep": True},
            {"use_ce_50": False, "require_sweep": False},
        ]

        profiles = ["guardiao", "tatico", "sniper"]
        best_candidate = None
        highest_prop_score = -999.0

        for comb in combinations:
            for prof in profiles:
                mult = 1.5 if prof == "guardiao" else (2.5 if prof == "tatico" else 4.0)
                wins, losses, be_exits = 0, 0, 0
                max_consec_losses = 0
                current_consec_losses = 0

                for f in fvgs:
                    if not InstitutionalSessionFilter.is_session_active(symbol, f['raw_time']):
                        continue

                    if comb["require_sweep"] and not f.get("has_sweep", False):
                        continue

                    direction = "BUY" if f['type'] == 'BULLISH' else "SELL"
                    entry = f['ce_50'] if comb["use_ce_50"] else (f['top'] if direction == "BUY" else f['bottom'])

                    raw_dist = abs(entry - (f['bottom'] if direction == "BUY" else f['top']))
                    risk = min(max(raw_dist + (1.2 if is_nasdaq else 0.4), min_stop_points), max_risk)

                    tp = entry + (risk * mult) if direction == "BUY" else entry - (risk * mult)
                    sl = entry - risk if direction == "BUY" else entry + risk

                    # Avalia a visão considerando apenas o histórico até o nascimento daquele setup
                    f_idx = f['index']
                    df_context = df_m5.iloc[:f_idx+1]
                    path_ok, _ = vision.validate_liquidity_path(df_context, direction, entry, tp)
                    if not path_ok:
                        continue

                    start_idx = 0
                    for idx in range(len(m1_times)):
                        if m1_times[idx] >= f['raw_time']:
                            start_idx = idx + 1
                            break

                    if start_idx == 0 or start_idx >= len(m1_times): continue

                    sim_h = m1_highs[start_idx : min(start_idx + 120, len(m1_highs))]
                    sim_l = m1_lows[start_idx : min(start_idx + 120, len(m1_lows))]

                    triggered = False
                    win, loss, hit_be = False, False, False

                    for h, l in zip(sim_h, sim_l):
                        if not triggered:
                            if direction == "BUY" and l <= entry: triggered = True
                            elif direction == "SELL" and h >= entry: triggered = True
                            if not triggered: continue

                        if not hit_be:
                            if direction == "BUY" and h >= (entry + risk * 1.2): hit_be = True
                            elif direction == "SELL" and l <= (entry - risk * 1.2): hit_be = True

                        if direction == "BUY":
                            if hit_be and l <= entry: be_exits += 1; break
                            elif not hit_be and l <= sl: loss = True; break
                            elif h >= tp: win = True; break
                        else:
                            if hit_be and h >= entry: be_exits += 1; break
                            elif not hit_be and h >= sl: loss = True; break
                            elif l <= tp: win = True; break

                    if triggered:
                        if win:
                            wins += 1
                            current_consec_losses = 0
                        elif loss:
                            losses += 1
                            current_consec_losses += 1
                            max_consec_losses = max(max_consec_losses, current_consec_losses)

                total_resolved = wins + losses
                if total_resolved < 3:
                    continue

                win_rate = (wins / total_resolved) * 100.0 if total_resolved > 0 else 0.0
                net_r = (wins * mult) - (losses * 1.0)
                profit_factor = (wins * mult) / (losses * 1.0) if losses > 0 else 2.5

                drawdown_penalty = max_consec_losses * 1.5
                prop_score = (profit_factor * (win_rate / 100.0) * 10.0) - drawdown_penalty

                if prop_score > highest_prop_score:
                    highest_prop_score = prop_score
                    best_candidate = {
                        "use_ce_50": comb["use_ce_50"],
                        "require_sweep": comb["require_sweep"],
                        "recommended_profile": prof,
                        "prop_score": round(prop_score, 1),
                        "win_rate": int(win_rate),
                        "trades": total_resolved + be_exits,
                        "net_r": round(net_r, 1),
                        "should_trade": prop_score >= 0.0
                    }

        return best_candidate

    def get_directive(self, category):
        return self.active_directives.get(category, {
            "use_ce_50": True, "require_sweep": False, "recommended_profile": "tatico", "should_trade": True
        })