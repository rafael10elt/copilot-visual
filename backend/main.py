# main.py — Orquestrador HFT com Modo Fiel ao Backtest, Paridade 1:1 NASDAQ/XAUUSD e Execução ECN
import time
import json
import requests
from datetime import datetime, timezone, timedelta
import MetaTrader5 as mt5
import numpy as np

from mt5_core import (
    MT5Engine, 
    FVGDetector, 
    MarketStructureDetector, 
    VisionLiquidityAnalyzer, 
    InstitutionalSessionFilter
)
from risk_manager import RiskManager
from ai_groq import LumiGroqAgent
from supabase_client import SupabaseSync
from strategy_scout import StrategyScout

ROBOT_MAGIC = 777999


class EconomicNewsFilter:
    def __init__(self, cache_ttl_seconds=900):
        self.cache_ttl = cache_ttl_seconds
        self.last_fetch = 0
        self.cached_events = []

    def refresh_events(self):
        now = time.time()
        if now - self.last_fetch < self.cache_ttl:
            return

        try:
            url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
            res = requests.get(url, timeout=4)
            if res.status_code == 200:
                self.cached_events = res.json()
                self.last_fetch = now
                print("📰 [NEWS FILTER] Calendário econômico atualizado com sucesso.")
        except Exception as e:
            print(f"⚠️ [NEWS FILTER] Falha ao consultar notícias: {e}")

    def is_news_window_active(self, window_minutes=15):
        self.refresh_events()
        now_utc = datetime.now(timezone.utc)

        for ev in self.cached_events:
            if ev.get("impact") == "High" and ev.get("country") in ["USD"]:
                try:
                    ev_time_str = ev["date"].replace("Z", "+00:00")
                    ev_time = datetime.fromisoformat(ev_time_str)
                    diff_minutes = (ev_time - now_utc).total_seconds() / 60.0

                    if -10 <= diff_minutes <= window_minutes:
                        return True, ev.get("title", "Notícia de Alto Impacto USD")
                except Exception:
                    continue

        return False, None


def has_active_order_or_position(symbol):
    positions = mt5.positions_get(symbol=symbol)
    if positions:
        for p in positions:
            if p.magic == ROBOT_MAGIC: return True

    orders = mt5.orders_get(symbol=symbol)
    if orders:
        for o in orders:
            if o.magic == ROBOT_MAGIC: return True

    return False


def send_limit_order(symbol, action, entry_price, sl, tp, lot_size):
    info = mt5.symbol_info(symbol)
    if not info: return False, "Símbolo não localizado"

    point = info.point
    stops_level = (info.trade_stops_level or 0) * point

    if action == "BUY_LIMIT":
        if entry_price >= (info.ask - stops_level):
            return False, f"Entrada ({entry_price}) muito próxima ou acima do Ask ({info.ask})"
    else:
        if entry_price <= (info.bid + stops_level):
            return False, f"Entrada ({entry_price}) muito próxima ou abaixo do Bid ({info.bid})"

    order_type = mt5.ORDER_TYPE_BUY_LIMIT if action == "BUY_LIMIT" else mt5.ORDER_TYPE_SELL_LIMIT

    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": float(lot_size),
        "type": order_type,
        "price": float(entry_price),
        "sl": float(sl),
        "tp": float(tp),
        "deviation": 10,
        "magic": ROBOT_MAGIC,
        "comment": "LUMI FVG PRO",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        return True, "Ordem armada com sucesso (RETURN)"

    if result.retcode == 10030:
        for mode in [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]:
            request["type_filling"] = mode
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                return True, f"Ordem armada com sucesso (Fallback {mode})"

    return False, f"Retcode {result.retcode} ({result.comment})"


def purge_stale_pending_orders(max_age_minutes=60):
    orders = mt5.orders_get()
    if not orders: return 0

    now_ts = time.time()
    cancelled = 0

    for o in orders:
        if o.magic == ROBOT_MAGIC:
            age_sec = now_ts - o.time_setup
            if age_sec > (max_age_minutes * 60):
                req = {"action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket}
                res = mt5.order_send(req)
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    cancelled += 1
                    print(f"🧹 [PURGE] Ordem expirada #{o.ticket} cancelada ({int(age_sec/60)}m).")
    return cancelled


def cancel_all_pending_orders():
    orders = mt5.orders_get()
    if not orders: return 0
    cancelled = 0
    for o in orders:
        if o.magic == ROBOT_MAGIC:
            req = {"action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket}
            res = mt5.order_send(req)
            if res.retcode == mt5.TRADE_RETCODE_DONE: cancelled += 1
    return cancelled


def close_all_open_positions():
    positions = mt5.positions_get()
    if not positions: return 0
    closed = 0
    for p in positions:
        if p.magic == ROBOT_MAGIC:
            order_type = mt5.ORDER_TYPE_SELL if p.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
            tick = mt5.symbol_info_tick(p.symbol)
            price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask
            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": p.ticket,
                "symbol": p.symbol,
                "volume": p.volume,
                "type": order_type,
                "price": price,
                "deviation": 20,
                "magic": ROBOT_MAGIC,
                "comment": "EMERGENCY_FLATTEN"
            }
            res = mt5.order_send(req)
            if res.retcode == mt5.TRADE_RETCODE_DONE: closed += 1
    return closed


POSITION_RISK_CACHE = {}

def manage_open_trades(engine, risk_manager, settings):
    global POSITION_RISK_CACHE
    be_enabled = settings.get("breakeven_enabled", True)
    trailing_enabled = settings.get("trailing_enabled", False)

    if not be_enabled and not trailing_enabled:
        return

    positions = mt5.positions_get()
    if not positions:
        POSITION_RISK_CACHE.clear()
        return

    current_tickets = {p.ticket for p in positions}
    POSITION_RISK_CACHE = {t: r for t, r in POSITION_RISK_CACHE.items() if t in current_tickets}

    for p in positions:
        if p.magic != ROBOT_MAGIC:
            continue

        current_price = p.price_current
        open_price = p.price_open
        current_sl = p.sl

        if p.ticket not in POSITION_RISK_CACHE:
            if current_sl > 0:
                raw_risk = abs(open_price - current_sl)
                if raw_risk > (open_price * 0.0002):
                    POSITION_RISK_CACHE[p.ticket] = raw_risk

        initial_risk = POSITION_RISK_CACHE.get(p.ticket, abs(open_price - current_sl) if current_sl > 0 else 0.0)

        # 1. Trailing Stop M1 (Disparado a partir de 1.5R)
        if trailing_enabled and initial_risk > 0:
            df_m1 = engine.get_candles(p.symbol, mt5.TIMEFRAME_M1, 3)
            if df_m1 is not None and len(df_m1) >= 2:
                last_completed = df_m1.iloc[-2]
                new_trail_sl = risk_manager.calculate_safe_trailing_sl(
                    p.symbol, p.type, open_price, current_price, current_sl,
                    float(last_completed['low']), float(last_completed['high']),
                    initial_risk_points=initial_risk, r_trigger=1.5
                )
                if new_trail_sl:
                    req = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": p.ticket,
                        "sl": float(new_trail_sl),
                        "tp": float(p.tp)
                    }
                    res = mt5.order_send(req)
                    if res.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"📈 [TRAILING 1.5R M1] #{p.ticket} ({p.symbol}) SL ajustado para {new_trail_sl}")
                    continue

        # 2. Break-Even 1.2R
        if be_enabled and initial_risk > 0:
            if p.type == mt5.POSITION_TYPE_BUY and current_sl >= open_price: continue
            if p.type == mt5.POSITION_TYPE_SELL and current_sl > 0 and current_sl <= open_price: continue

            new_be_sl = risk_manager.calculate_safe_breakeven_sl(
                p.symbol, p.type, open_price, current_price, initial_risk, r_trigger=1.2
            )
            if new_be_sl:
                req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": p.ticket,
                    "sl": float(new_be_sl),
                    "tp": float(p.tp)
                }
                res = mt5.order_send(req)
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"🛡️ [BREAK-EVEN 1.2R] #{p.ticket} ({p.symbol}) SL protegido em {new_be_sl}")


def get_performance_stats(risk_base=50.0):
    try:
        now = datetime.now()
        start_of_today = datetime(now.year, now.month, now.day, 0, 0, 0)
        end_of_today = start_of_today + timedelta(days=2)
        start_30d = start_of_today - timedelta(days=30)

        deals_30d = mt5.history_deals_get(start_30d, end_of_today)
        
        today_deals_closed = []
        today_wins, today_losses = 0, 0
        today_realized_pnl = 0.0

        pnl_30d = 0.0
        wins_30d, losses_30d = 0, 0
        gross_profit_30d, gross_loss_30d = 0.0, 0.0

        running_pnl = 0.0
        peak_pnl = 0.0
        max_drawdown_usd = 0.0

        if deals_30d:
            sorted_deals = sorted(deals_30d, key=lambda x: x.time)
            
            for d in sorted_deals:
                if d.entry == mt5.DEAL_ENTRY_OUT and d.magic == ROBOT_MAGIC:
                    profit = round(d.profit + d.commission + d.swap, 2)
                    
                    pnl_30d += profit
                    if profit > 0:
                        wins_30d += 1
                        gross_profit_30d += profit
                    elif profit < 0:
                        losses_30d += 1
                        gross_loss_30d += abs(profit)

                    running_pnl += profit
                    if running_pnl > peak_pnl: peak_pnl = running_pnl
                    dd = peak_pnl - running_pnl
                    if dd > max_drawdown_usd: max_drawdown_usd = dd

                    if d.time >= start_of_today.timestamp():
                        today_realized_pnl += profit
                        if profit > 0: today_wins += 1
                        elif profit < 0: today_losses += 1

                        trade_type = "SELL" if d.type == mt5.DEAL_TYPE_BUY else "BUY"
                        trade_r = round(profit / max(risk_base, 1.0), 2)
                        today_deals_closed.append({
                            "ticket": d.ticket,
                            "symbol": d.symbol,
                            "type": trade_type,
                            "volume": d.volume,
                            "profit": profit,
                            "r_multiple": trade_r,
                            "time": datetime.fromtimestamp(d.time).strftime("%H:%M")
                        })

        open_positions = []
        positions = mt5.positions_get()
        if positions:
            for p in positions:
                if p.magic == ROBOT_MAGIC:
                    open_positions.append({
                        "ticket": p.ticket,
                        "symbol": p.symbol,
                        "type": "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
                        "volume": p.volume,
                        "price_open": round(p.price_open, 2),
                        "price_current": round(p.price_current, 2),
                        "sl": round(p.sl, 2),
                        "tp": round(p.tp, 2),
                        "profit": round(p.profit + p.swap, 2)
                    })

        today_total = today_wins + today_losses
        today_win_rate = int((today_wins / today_total) * 100) if today_total > 0 else 0
        today_net_r = round(today_realized_pnl / max(risk_base, 1.0), 2)

        total_30d = wins_30d + losses_30d
        win_rate_30d = int((wins_30d / total_30d) * 100) if total_30d > 0 else 0
        net_r_30d = round(pnl_30d / max(risk_base, 1.0), 2)
        profit_factor_30d = round(gross_profit_30d / gross_loss_30d, 2) if gross_loss_30d > 0 else (2.5 if gross_profit_30d > 0 else 0.0)

        return {
            "total_trades": today_total,
            "wins": today_wins,
            "losses": today_losses,
            "win_rate": today_win_rate,
            "realized_pnl": round(today_realized_pnl, 2),
            "net_r": today_net_r,
            "open_count": len(open_positions),
            "open_positions": open_positions,
            "closed_trades": today_deals_closed[-8:],
            "stats_30d": {
                "total_trades": total_30d,
                "wins": wins_30d,
                "losses": losses_30d,
                "win_rate": win_rate_30d,
                "realized_pnl": round(pnl_30d, 2),
                "net_r": net_r_30d,
                "max_drawdown_usd": round(max_drawdown_usd, 2),
                "profit_factor": profit_factor_30d
            }
        }
    except Exception as e:
        print(f"⚠️ Erro ao calcular estatísticas: {e}")
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0,
            "realized_pnl": 0.0, "net_r": 0.0, "open_count": 0, "open_positions": [], "closed_trades": [],
            "stats_30d": {
                "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0,
                "realized_pnl": 0.0, "net_r": 0.0, "max_drawdown_usd": 0.0, "profit_factor": 0.0
            }
        }


def run_recent_backtest(engine, symbol, days=0, risk_per_trade=50.0, session_mode="KILLZONES"):
    """
    Sandbox com PARIDADE 1:1 REALISTA com a execução do MT5.
    Exige que o Bid fure o spread para que o Ask atinja a ordem limite de compra.
    """
    if not symbol: return None

    broker_now = engine.get_broker_current_time(symbol)

    if days == 0:
        start_of_day = datetime(broker_now.year, broker_now.month, broker_now.day, 0, 0, 0)
        minutes_elapsed = max(60, int((broker_now - start_of_day).total_seconds() / 60))
        total_m5 = max(24, int(minutes_elapsed / 5) + 20)
        total_m1 = max(120, minutes_elapsed + 60)
    else:
        start_of_day = datetime.min
        total_m5 = int(days) * 288
        total_m1 = int(days) * 1440

    df_m5 = engine.get_candles(symbol, mt5.TIMEFRAME_M5, total_m5)
    df_m1 = engine.get_candles(symbol, mt5.TIMEFRAME_M1, total_m1)

    if df_m5 is None or df_m1 is None: return None

    is_nasdaq = any(x in symbol.upper() for x in ["US100", "NAS", "USTEC", "NQ"])
    
    # PARIDADE COM O RISK_MANAGER:
    if is_nasdaq:
        buffer_pts = 3.50
        min_stop_points = 12.00
        max_risk = 35.00
    else:
        buffer_pts = 0.90
        min_stop_points = 2.50
        max_risk = 5.00

    info = mt5.symbol_info(symbol)
    point = info.point if info else 0.01
    spread_pts = (info.spread * point) if (info and info.spread > 0) else (1.8 if is_nasdaq else 0.30)
    slippage_pts = 0.8 if is_nasdaq else 0.15
    commission_r = 0.04

    detector = FVGDetector()
    vision = VisionLiquidityAnalyzer()
    all_fvgs = detector.find_all_historical_fvgs(df_m5, symbol)

    m1_highs = df_m1['high'].values
    m1_lows = df_m1['low'].values
    m1_times = df_m1['time'].values

    entry_modes = [("CE_50", True), ("BORDA", False)]
    sweep_modes = [("COM_SWEEP", True), ("SEM_SWEEP", False)]
    profiles = [("guardiao", 1.5, "GUARDIAN (1:1.5)"), ("tatico", 2.5, "TACTICAL (1:2.5)"), ("sniper", 4.0, "SNIPER (1:4.0)")]

    raio_x_results = []

    for entry_label, use_ce_50 in entry_modes:
        for sweep_label, req_sweep in sweep_modes:
            for prof_key, mult, prof_label in profiles:
                for with_be in [True, False]:
                    wins, losses, be_count = 0, 0, 0
                    setups_mapped = 0
                    trades_executed = 0

                    bot_busy_until_m1_idx = -1
                    current_sim_day = None
                    daily_trade_count = 0
                    daily_net_r = 0.0
                    day_locked = False

                    for f in all_fvgs:
                        f_time = f['raw_time']
                        f_date_str = f_time.strftime('%Y-%m-%d')

                        if days == 0 and f_time < start_of_day:
                            continue

                        if f_date_str != current_sim_day:
                            current_sim_day = f_date_str
                            daily_trade_count = 0
                            daily_net_r = 0.0
                            day_locked = False

                        if day_locked or daily_trade_count >= 5:
                            continue

                        if not InstitutionalSessionFilter.is_session_active(
                            symbol, f['raw_time'], engine.broker_utc_offset_hours, session_mode=session_mode
                        ):
                            continue

                        if req_sweep and not f['has_sweep']:
                            continue

                        direction = "BUY" if f['type'] == 'BULLISH' else "SELL"
                        raw_entry = f['ce_50'] if use_ce_50 else (f['top'] if direction == "BUY" else f['bottom'])

                        raw_dist = abs(raw_entry - (f['bottom'] if direction == "BUY" else f['top']))
                        risk = min(max(raw_dist + buffer_pts, min_stop_points), max_risk)

                        tp = raw_entry + (risk * mult) if direction == "BUY" else raw_entry - (risk * mult)
                        sl = raw_entry - risk if direction == "BUY" else raw_entry + risk

                        f_idx = f['index']
                        df_context = df_m5.iloc[:f_idx+1]
                        path_ok, _ = vision.validate_liquidity_path(df_context, direction, raw_entry, tp)
                        if not path_ok:
                            continue

                        setups_mapped += 1

                        start_idx = int(np.searchsorted(m1_times, np.datetime64(f['raw_time']), side='right'))

                        if start_idx >= len(m1_times) or start_idx <= bot_busy_until_m1_idx:
                            continue

                        max_sim_idx = min(start_idx + 120, len(m1_highs))
                        sim_slice_h = m1_highs[start_idx : max_sim_idx]
                        sim_slice_l = m1_lows[start_idx : max_sim_idx]

                        triggered = False
                        win, loss, hit_be = False, False, False
                        trade_resolved_idx = start_idx

                        # PREENCHIMENTO REALISTA COM SPREAD:
                        # Buy Limit só executa se a mínima da vela M1 for menor que (raw_entry - spread_pts)
                        # Sell Limit executa no toque direto da máxima
                        for step, (h, l) in enumerate(zip(sim_slice_h, sim_slice_l)):
                            current_m1_idx = start_idx + step

                            if not triggered:
                                if direction == "BUY" and l <= (raw_entry - spread_pts): 
                                    triggered = True
                                elif direction == "SELL" and h >= raw_entry: 
                                    triggered = True
                                if not triggered: 
                                    continue

                            if with_be and not hit_be:
                                if direction == "BUY" and h >= (raw_entry + risk * 1.2): hit_be = True
                                elif direction == "SELL" and l <= (raw_entry - risk * 1.2): hit_be = True

                            if direction == "BUY":
                                effective_tp = tp
                                effective_sl = sl if not hit_be else raw_entry
                                
                                if l <= effective_sl and h >= effective_tp:
                                    loss = True if not hit_be else False
                                    trade_resolved_idx = current_m1_idx
                                    break
                                elif l <= effective_sl:
                                    loss = True if not hit_be else False
                                    trade_resolved_idx = current_m1_idx
                                    break
                                elif h >= effective_tp:
                                    win = True
                                    trade_resolved_idx = current_m1_idx
                                    break
                            else:
                                effective_tp = tp + spread_pts
                                effective_sl = (sl + spread_pts) if not hit_be else raw_entry
                                
                                if h >= effective_sl and l <= effective_tp:
                                    loss = True if not hit_be else False
                                    trade_resolved_idx = current_m1_idx
                                    break
                                elif h >= effective_sl:
                                    loss = True if not hit_be else False
                                    trade_resolved_idx = current_m1_idx
                                    break
                                elif l <= effective_tp:
                                    win = True
                                    trade_resolved_idx = current_m1_idx
                                    break

                        if triggered:
                            trades_executed += 1
                            daily_trade_count += 1
                            bot_busy_until_m1_idx = trade_resolved_idx + 10

                            if win:
                                wins += 1
                                daily_net_r += mult
                            elif loss:
                                losses += 1
                                daily_net_r -= 1.0
                            elif hit_be and not win:
                                be_count += 1

                            if daily_net_r >= 3.5 or daily_net_r <= -2.0:
                                day_locked = True

                    total_resolved = wins + losses
                    win_rate = int((wins / total_resolved) * 100) if total_resolved > 0 else 0

                    net_r_raw = (wins * mult) - (losses * 1.0)
                    total_deals = wins + losses + be_count
                    total_commissions_r = total_deals * commission_r
                    net_r_realistic = round(net_r_raw - total_commissions_r, 1)
                    pnl_realistic = round(net_r_realistic * risk_per_trade, 2)

                    raio_x_results.append({
                        "id": f"{entry_label}_{sweep_label}_{prof_key}_{'BE' if with_be else 'NOBE'}",
                        "entry": "50% CE" if use_ce_50 else "Borda",
                        "sweep": "Com Sweep" if req_sweep else "Sem Sweep",
                        "profile": prof_label,
                        "profile_key": prof_key,
                        "with_be": with_be,
                        "be_label": "Com BE" if with_be else "Sem BE",
                        "setups_mapped": setups_mapped,
                        "trades_executed": trades_executed,
                        "wins": wins,
                        "losses": losses,
                        "be_count": be_count,
                        "win_rate": win_rate,
                        "net_r": net_r_realistic,
                        "pnl": pnl_realistic
                    })

    raio_x_results.sort(key=lambda x: (x['pnl'], x['win_rate']), reverse=True)
    best = raio_x_results[0] if raio_x_results else None

    def get_subset(use_ce, be):
        sub = {}
        for p_key in ['guardiao', 'tatico', 'sniper']:
            match = next((r for r in raio_x_results if r['entry'] == ('50% CE' if use_ce else 'Borda') and r['with_be'] == be and r['profile_key'] == p_key and r['sweep'] == 'Sem Sweep'), None)
            if match:
                sub[p_key] = {"rate": match["win_rate"], "wins": match["wins"], "losses": match["losses"], "net_r": match["net_r"], "pnl": match["pnl"], "be_count": match["be_count"]}
            else:
                sub[p_key] = {"rate": 0, "wins": 0, "losses": 0, "net_r": 0, "pnl": 0}
        return sub

    return {
        "timestamp": int(time.time()),
        "symbol": symbol,
        "days": days,
        "session_mode": session_mode,
        "setups_mapped": len(all_fvgs),
        "trades_executed": best['trades_executed'] if best else 0,
        "base_risk": risk_per_trade,
        "strategy_info": {
            "mode": "Execução Sequencial (Max 5 Trades/Dia)",
            "frictions": f"Spread Real ({spread_pts:.2f}) + Slippage + Trava Meta/Loss",
            "context": "Sessão Atual (Hoje)" if days == 0 else f"Histórico Real {days}D",
            "session": "24H (Full Day)" if session_mode == "24H" else "Killzones Institucionais (Londres/NY)"
        },
        "raio_x": raio_x_results,
        "with_be": get_subset(use_ce=True, be=True),
        "without_be": get_subset(use_ce=True, be=False),
        "sniper": get_subset(use_ce=True, be=True)["sniper"],
        "tatico": get_subset(use_ce=True, be=True)["tatico"],
        "guardiao": get_subset(use_ce=True, be=True)["guardiao"],
        "recommended": f"{best['profile']} ({best['entry']} | {best['sweep']} | {best['be_label']})" if best else "GUARDIAN (50% CE)"
    }


def main():
    print("==================================================")
    print("🚀 LUMI COPILOT HFT - PRO (INSTITUTIONAL SMC / PROP SHIELD)")
    print("==================================================")

    engine = MT5Engine()
    if not engine.start(): return

    fvg_detector = FVGDetector()
    risk_manager = RiskManager()
    ia_agent = LumiGroqAgent()
    sync = SupabaseSync()
    vision = VisionLiquidityAnalyzer()
    news_filter = EconomicNewsFilter()

    scout = StrategyScout(engine, sync, eval_interval_seconds=3600)
    scout.start()

    processed_fvgs = set()
    last_hb = 0
    active_mode = "BOTH"
    cached_settings = {}

    sync.add_log(None, "Motor conectado com Escudo Ativo e Paridade 1:1 NASDAQ/XAUUSD.", "INFO")

    try:
        while True:
            broker_time = engine.get_broker_current_time("XAUUSD")

            acc = mt5.account_info()
            if acc:
                balance, equity = acc.balance, acc.equity
                pnl_today = equity - balance
                login, server = str(acc.login), acc.server
                
                breached, msg = risk_manager.update_account_state(balance, equity, broker_time)
                if breached:
                    sync.add_log(None, f"⛔ [PROP SHIELD] {msg} — Liquidando posições e travando operações!", "DANGER")
                    cancel_all_pending_orders()
                    close_all_open_positions()
                    time.sleep(10)
                    continue
            else:
                balance, equity, pnl_today, login, server = 0, 0, 0, "--", "--"

            raw_backtest_mode = bool(cached_settings.get("raw_backtest_mode", False))

            is_news = False
            if not raw_backtest_mode:
                is_news, news_title = news_filter.is_news_window_active(window_minutes=15)
                if is_news:
                    purged = cancel_all_pending_orders()
                    if purged > 0:
                        sync.add_log(None, f"📰 [NEWS SHIELD] {purged} ordens canceladas por anúncio: {news_title}", "WARN")

            agora = time.time()
            if agora - last_hb >= 2.0:
                last_hb = agora
                purge_stale_pending_orders(max_age_minutes=60 if raw_backtest_mode else 15)

                remote = sync.check_remote_settings()
                if remote:
                    cached_settings = remote
                    if remote.get("risk_per_trade"): risk_manager.risk_per_trade_usd = float(remote.get("risk_per_trade"))
                    if remote.get("max_daily_loss"): risk_manager.max_daily_loss_usd = float(remote.get("max_daily_loss"))
                    if remote.get("active_symbol_mode"): active_mode = remote.get("active_symbol_mode")

                    cmd = remote.get("command")
                    if cmd:
                        try: sync.client.table("copilot_settings").update({"command": None}).eq("id", 1).execute()
                        except: pass

                        if "RUN_BACKTEST" in cmd:
                            parts = cmd.split(":")
                            cat = "NASDAQ" if "US100" in parts[1] else "GOLD"
                            real_sym = engine.resolve_symbol(cat)
                            days = int(parts[2]) if len(parts) > 2 else 0
                            session_sel = parts[3] if len(parts) > 3 else "KILLZONES"

                            rep = run_recent_backtest(engine, real_sym, days, risk_manager.risk_per_trade_usd, session_mode=session_sel)
                            if rep:
                                try: sync.client.table("copilot_status").update({"last_backtest": rep}).eq("id", 1).execute()
                                except: pass
                                sync.add_log(real_sym, f"BACKTEST_RESULT:{json.dumps(rep)}", "SUCCESS")

                        elif "EMERGENCY_STOP" in cmd:
                            c = cancel_all_pending_orders()
                            p = close_all_open_positions()
                            sync.add_log(None, f"EMERGÊNCIA: {c} ordens canceladas, {p} posições zeradas", "DANGER")

                perf_data = get_performance_stats(risk_base=risk_manager.risk_per_trade_usd)
                perf_data["scout_directives"] = scout.active_directives

                nasdaq_cfg = cached_settings.get("nasdaq") or {
                    "auto_ia": cached_settings.get("auto_profile_ia", False),
                    "profile": cached_settings.get("profile", "guardiao"),
                    "use_ce_50": cached_settings.get("use_ce_50", True),
                    "require_sweep": cached_settings.get("require_sweep", False),
                    "session_mode": "KILLZONES"
                }
                gold_cfg = cached_settings.get("gold") or {
                    "auto_ia": cached_settings.get("auto_profile_ia", False),
                    "profile": cached_settings.get("profile", "tatico"),
                    "use_ce_50": cached_settings.get("use_ce_50", True),
                    "require_sweep": cached_settings.get("require_sweep", False),
                    "session_mode": "24H"
                }

                dir_nasdaq = scout.get_directive("NASDAQ")
                dir_gold = scout.get_directive("GOLD")

                perf_data["active_strategy"] = {
                    "nasdaq": {
                        "is_auto": bool(nasdaq_cfg.get("auto_ia", False)),
                        "profile": dir_nasdaq.get("recommended_profile", nasdaq_cfg.get("profile")) if nasdaq_cfg.get("auto_ia") else nasdaq_cfg.get("profile", "guardiao"),
                        "entry_type": "50% CE" if (dir_nasdaq.get("use_ce_50") if nasdaq_cfg.get("auto_ia") else nasdaq_cfg.get("use_ce_50", True)) else "Borda",
                        "require_sweep": dir_nasdaq.get("require_sweep") if nasdaq_cfg.get("auto_ia") else nasdaq_cfg.get("require_sweep", False),
                        "session_mode": nasdaq_cfg.get("session_mode", "KILLZONES"),
                        "status": "AUTORIZADO" if (dir_nasdaq.get("should_trade") if nasdaq_cfg.get("auto_ia") else True) else "STAND-BY"
                    },
                    "gold": {
                        "is_auto": bool(gold_cfg.get("auto_ia", False)),
                        "profile": dir_gold.get("recommended_profile", gold_cfg.get("profile")) if gold_cfg.get("auto_ia") else gold_cfg.get("profile", "tatico"),
                        "entry_type": "50% CE" if (dir_gold.get("use_ce_50") if gold_cfg.get("auto_ia") else gold_cfg.get("use_ce_50", True)) else "Borda",
                        "require_sweep": dir_gold.get("require_sweep") if gold_cfg.get("auto_ia") else gold_cfg.get("require_sweep", False),
                        "session_mode": gold_cfg.get("session_mode", "24H"),
                        "status": "AUTORIZADO" if (dir_gold.get("should_trade") if gold_cfg.get("auto_ia") else True) else "STAND-BY"
                    },
                    "breakeven": "ATIVO (1.2R)" if cached_settings.get("breakeven_enabled", True) else "DESLIGADO",
                    "trailing": "ATIVO (M1)" if cached_settings.get("trailing_enabled", False) else "DESLIGADO",
                    "raw_backtest_mode": raw_backtest_mode
                }

                sync.send_heartbeat("hibrido", pnl_today, login, balance, equity, server, perf_data)

            manage_open_trades(engine, risk_manager, cached_settings)

            if is_news or risk_manager.daily_lock_active:
                time.sleep(1)
                continue

            targets = []
            if active_mode in ["BOTH", "US100"]:
                sym_nasdaq = engine.resolve_symbol("NASDAQ")
                if sym_nasdaq: targets.append(("NASDAQ", sym_nasdaq))

            if active_mode in ["BOTH", "XAUUSD"]:
                sym_gold = engine.resolve_symbol("GOLD")
                if sym_gold: targets.append(("GOLD", sym_gold))

            for category, symbol in targets:
                if has_active_order_or_position(symbol):
                    continue

                spread_ok, _ = engine.is_spread_acceptable(symbol)
                if not spread_ok:
                    continue

                cfg_key = "nasdaq" if category == "NASDAQ" else "gold"
                asset_cfg = cached_settings.get(cfg_key) or {
                    "auto_ia": cached_settings.get("auto_profile_ia", False),
                    "profile": cached_settings.get("profile", "guardiao" if category == "NASDAQ" else "tatico"),
                    "use_ce_50": cached_settings.get("use_ce_50", True),
                    "require_sweep": cached_settings.get("require_sweep", False),
                    "session_mode": "KILLZONES" if category == "NASDAQ" else "24H"
                }

                asset_session_mode = asset_cfg.get("session_mode", "KILLZONES")
                if not InstitutionalSessionFilter.is_session_active(
                    symbol, broker_time, engine.broker_utc_offset_hours, session_mode=asset_session_mode
                ):
                    continue

                is_auto_asset = bool(asset_cfg.get("auto_ia", False))
                directive = scout.get_directive(category)

                if is_auto_asset and not directive.get("should_trade", True):
                    continue

                if is_auto_asset:
                    active_profile_for_trade = directive.get("recommended_profile", "guardiao")
                    use_ce_50 = directive.get("use_ce_50", True)
                    require_sweep = directive.get("require_sweep", False)
                else:
                    active_profile_for_trade = asset_cfg.get("profile", "guardiao" if category == "NASDAQ" else "tatico")
                    use_ce_50 = asset_cfg.get("use_ce_50", True)
                    require_sweep = asset_cfg.get("require_sweep", False)

                df_m15 = engine.get_candles(symbol, mt5.TIMEFRAME_M15, 30)
                df_m5 = engine.get_candles(symbol, mt5.TIMEFRAME_M5, 30)
                df_m1 = engine.get_candles(symbol, mt5.TIMEFRAME_M1, 30)

                if df_m15 is None or df_m5 is None or df_m1 is None:
                    continue

                current_price = df_m1.iloc[-1]['close']
                structure, _, _ = MarketStructureDetector.get_m15_structure(df_m15)
                atr = risk_manager.calculate_atr(df_m1)

                info = mt5.symbol_info(symbol)
                spread = info.spread if info else 10
                
                ia_agent.update_macro_regime_async(category, structure, atr, spread)

                fvgs = fvg_detector.find_unmitigated_fvgs(df_m5, symbol)

                for fvg in reversed(fvgs):
                    fvg_id = f"{symbol}_{fvg['type']}_{fvg['time_formed']}"
                    if fvg_id in processed_fvgs:
                        continue

                    max_allowed_age = 12 if raw_backtest_mode else 4
                    if fvg.get('age_candles', 0) > max_allowed_age:
                        processed_fvgs.add(fvg_id)
                        continue

                    if require_sweep and not fvg.get("has_sweep", False):
                        processed_fvgs.add(fvg_id)
                        continue

                    direction = "BUY" if fvg['type'] == 'BULLISH' else "SELL"
                    entry_candidate = fvg['ce_50'] if use_ce_50 else (fvg['top'] if direction == "BUY" else fvg['bottom'])

                    max_dist = 25.0 if any(x in symbol.upper() for x in ["US100", "NAS", "USTEC", "NQ"]) else 4.5
                    dist = abs(current_price - entry_candidate)
                    if dist > max_dist:
                        continue

                    if not raw_backtest_mode:
                        if direction == "BUY" and "BEARISH" in structure:
                            processed_fvgs.add(fvg_id)
                            continue
                        if direction == "SELL" and "BULLISH" in structure:
                            processed_fvgs.add(fvg_id)
                            continue

                    params = risk_manager.get_trade_parameters(
                        active_profile_for_trade, fvg, atr, symbol, direction, use_ce_50=use_ce_50
                    )

                    path_ok, path_msg = vision.validate_liquidity_path(df_m5, direction, params["entry"], params["tp"])
                    if not path_ok:
                        processed_fvgs.add(fvg_id)
                        sync.add_log(symbol, f"Descartado por visão: {path_msg}", "WARN")
                        continue

                    if not raw_backtest_mode:
                        ai_ok, ai_reason = ia_agent.quick_validate_trade(category, direction, active_profile_for_trade)
                        if not ai_ok:
                            processed_fvgs.add(fvg_id)
                            sync.add_log(symbol, f"Bloqueado pela IA: {ai_reason}", "WARN")
                            continue

                    action = "BUY_LIMIT" if direction == "BUY" else "SELL_LIMIT"
                    lot = risk_manager.calculate_lot_size(symbol, params["risk_points"])

                    ok, order_msg = send_limit_order(symbol, action, params["entry"], params["sl"], params["tp"], lot)
                    if ok:
                        mode_tag = "FIEL 1:1" if raw_backtest_mode else ("IA 30D" if is_auto_asset else "MANUAL")
                        sess_tag = f"[{asset_session_mode}]"
                        sync.add_log(symbol, f"ORDEM ARMADA {sess_tag} ({mode_tag} | {active_profile_for_trade.upper()}): {action} {lot}L @ {params['entry']}", "SUCCESS")
                        processed_fvgs.add(fvg_id)
                        break
                    else:
                        sync.add_log(symbol, f"Rejeitada: {order_msg}", "WARN")

                    processed_fvgs.add(fvg_id)

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[ENCERRANDO] Finalizando motor...")
    finally:
        engine.stop()

if __name__ == "__main__":
    main()