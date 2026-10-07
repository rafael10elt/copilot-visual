# main.py — Orquestrador HFT com Expectativa Realista Rígida de Mesa Proprietária
import time
import json
from datetime import datetime, timedelta
import MetaTrader5 as mt5

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

def get_best_filling_mode(symbol):
    info = mt5.symbol_info(symbol)
    if not info: return mt5.ORDER_FILLING_IOC
    modes = info.filling_mode
    if modes & mt5.ORDER_FILLING_IOC: return mt5.ORDER_FILLING_IOC
    if modes & mt5.ORDER_FILLING_FOK: return mt5.ORDER_FILLING_FOK
    return mt5.ORDER_FILLING_RETURN

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
    stops_level = info.trade_stops_level * point

    if action == "BUY_LIMIT":
        if entry_price >= (info.ask - stops_level):
            return False, f"Entrada ({entry_price}) inválida para BUY_LIMIT (Ask: {info.ask})"
    else:
        if entry_price <= (info.bid + stops_level):
            return False, f"Entrada ({entry_price}) inválida para SELL_LIMIT (Bid: {info.bid})"

    order_type = mt5.ORDER_TYPE_BUY_LIMIT if action == "BUY_LIMIT" else mt5.ORDER_TYPE_SELL_LIMIT
    filling = get_best_filling_mode(symbol)

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
        "type_filling": filling,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return False, f"Retcode {result.retcode} ({result.comment})"

    return True, "Ordem armada com sucesso"

def purge_stale_pending_orders(max_age_minutes=15):
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
                    print(f"🧹 [PURGE] Ordem #{o.ticket} cancelada ({int(age_sec/60)}m).")
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

def manage_open_trades(risk_manager, settings):
    if not settings.get("breakeven_enabled", True): return
    positions = mt5.positions_get()
    if not positions: return

    for p in positions:
        if p.magic != ROBOT_MAGIC: continue

        current_price = p.price_current
        open_price = p.price_open
        current_sl = p.sl

        if p.type == mt5.POSITION_TYPE_BUY and current_sl >= open_price: continue
        if p.type == mt5.POSITION_TYPE_SELL and current_sl > 0 and current_sl <= open_price: continue

        new_sl = risk_manager.calculate_safe_breakeven_sl(p.symbol, p.type, open_price, current_price)
        if new_sl:
            req = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": p.ticket,
                "sl": float(new_sl),
                "tp": float(p.tp)
            }
            res = mt5.order_send(req)
            if res.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"🛡️ [BREAK-EVEN] #{p.ticket} ({p.symbol}) SL ajustado para {new_sl}")

def get_today_performance(risk_base=50.0):
    try:
        now = datetime.now()
        start_of_day = datetime(now.year, now.month, now.day, 0, 0, 0)
        end_of_day = start_of_day + timedelta(days=2)

        deals = mt5.history_deals_get(start_of_day, end_of_day)
        closed_trades = []
        wins, losses = 0, 0
        realized_pnl = 0.0

        if deals:
            for d in deals:
                if d.entry == mt5.DEAL_ENTRY_OUT and d.magic == ROBOT_MAGIC:
                    profit = round(d.profit + d.commission + d.swap, 2)
                    realized_pnl += profit
                    if profit > 0: wins += 1
                    elif profit < 0: losses += 1

                    trade_type = "SELL" if d.type == mt5.DEAL_TYPE_BUY else "BUY"
                    trade_r = round(profit / max(risk_base, 1.0), 2)
                    closed_trades.append({
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

        total = wins + losses
        win_rate = int((wins / total) * 100) if total > 0 else 0
        net_r_total = round(realized_pnl / max(risk_base, 1.0), 2)

        return {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "realized_pnl": round(realized_pnl, 2),
            "net_r": net_r_total,
            "open_count": len(open_positions),
            "open_positions": open_positions,
            "closed_trades": closed_trades[-8:]
        }
    except Exception:
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0,
            "realized_pnl": 0.0, "net_r": 0.0, "open_count": 0, "open_positions": [], "closed_trades": []
        }

def run_recent_backtest(engine, symbol, days=0, risk_per_trade=50.0):
    """
    BACKTEST DE EXPECTATIVA REALISTA RIGOROSA:
    1. Execução Sequencial Estrita (Zero sobreposição).
    2. Teto Operacional: Máximo 4 a 5 trades por sessão/dia.
    3. Trava de Meta Diária (+3.0R) e Trava de Perda Diária (-2.0R).
    4. Penetração Estrita de Spread para preenchimento.
    5. Pessimismo Intrabar em caso de conflito no mesmo candle.
    """
    if not symbol: return None

    tick_ref = mt5.symbol_info_tick(symbol)
    broker_now = datetime.fromtimestamp(tick_ref.time) if tick_ref else datetime.now()

    if days == 0:
        start_of_day = datetime(broker_now.year, broker_now.month, broker_now.day, 0, 0, 0)
        minutes_elapsed = max(60, int((broker_now - start_of_day).total_seconds() / 60))
        total_m5 = max(24, int(minutes_elapsed / 5) + 20)
        total_m1 = max(120, minutes_elapsed + 60)
    else:
        start_of_day = datetime.min
        total_m5 = int(days) * 240
        total_m1 = int(days) * 1440

    df_m5 = engine.get_candles(symbol, mt5.TIMEFRAME_M5, total_m5)
    df_m1 = engine.get_candles(symbol, mt5.TIMEFRAME_M1, total_m1)

    if df_m5 is None or df_m1 is None: return None

    is_nasdaq = "US100" in symbol or "NAS" in symbol or "USTEC" in symbol
    min_stop_points = 5.0 if is_nasdaq else 1.2
    max_risk = 30.0 if is_nasdaq else 4.5

    info = mt5.symbol_info(symbol)
    point = info.point if info else 0.01
    spread_pts = (info.spread * point) if (info and info.spread > 0) else (1.5 if is_nasdaq else 0.25)
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

                        # Controle de Virada de Dia
                        if f_date_str != current_sim_day:
                            current_sim_day = f_date_str
                            daily_trade_count = 0
                            daily_net_r = 0.0
                            day_locked = False

                        # TRAVA INSTITUCIONAL DE MESA: Se atingiu meta diária (+3.5R) ou limite (-2R), descansa o restante do dia
                        if day_locked or daily_trade_count >= 5:
                            continue

                        if req_sweep and not f['has_sweep']:
                            continue

                        direction = "BUY" if f['type'] == 'BULLISH' else "SELL"
                        raw_entry = f['ce_50'] if use_ce_50 else (f['top'] if direction == "BUY" else f['bottom'])

                        raw_dist = abs(raw_entry - (f['bottom'] if direction == "BUY" else f['top']))
                        risk = min(max(raw_dist + (1.2 if is_nasdaq else 0.4), min_stop_points), max_risk)

                        tp = raw_entry + (risk * mult) if direction == "BUY" else raw_entry - (risk * mult)
                        sl = raw_entry - risk if direction == "BUY" else raw_entry + risk

                        f_idx = f['index']
                        df_context = df_m5.iloc[:f_idx+1]
                        path_ok, _ = vision.validate_liquidity_path(df_context, direction, raw_entry, tp)
                        if not path_ok:
                            continue

                        setups_mapped += 1

                        start_idx = 0
                        for idx in range(len(m1_times)):
                            if m1_times[idx] >= f['raw_time']:
                                start_idx = idx + 1
                                break

                        if start_idx == 0 or start_idx >= len(m1_times): 
                            continue

                        # Trava Sequencial
                        if start_idx <= bot_busy_until_m1_idx:
                            continue

                        max_sim_idx = min(start_idx + 120, len(m1_highs))
                        sim_slice_h = m1_highs[start_idx : max_sim_idx]
                        sim_slice_l = m1_lows[start_idx : max_sim_idx]

                        triggered = False
                        win, loss, hit_be = False, False, False
                        trade_resolved_idx = start_idx

                        # PREENCHIMENTO ESTRITO COM FRICÇÃO REAL
                        # Para entrar numa compra Limit, o preço precisa ter caído abaixo do spread
                        strict_fill_penetration = spread_pts * 0.4
                        if direction == "BUY":
                            effective_entry = raw_entry + spread_pts + slippage_pts
                            effective_tp = tp
                            effective_sl = sl
                        else:
                            effective_entry = raw_entry - slippage_pts
                            effective_tp = tp + spread_pts
                            effective_sl = sl + spread_pts

                        for step, (h, l) in enumerate(zip(sim_slice_h, sim_slice_l)):
                            current_m1_idx = start_idx + step

                            if not triggered:
                                if direction == "BUY" and l <= (raw_entry - strict_fill_penetration): 
                                    triggered = True
                                elif direction == "SELL" and h >= (raw_entry + strict_fill_penetration): 
                                    triggered = True
                                if not triggered: 
                                    continue

                            # Lógica Break-Even
                            if with_be and not hit_be:
                                if direction == "BUY" and h >= (effective_entry + risk * 1.2): hit_be = True
                                elif direction == "SELL" and l <= (effective_entry - risk * 1.2): hit_be = True

                            # PESSIMISMO INTRABAR: Se tocou ambos no mesmo candle, assume STOP
                            if direction == "BUY":
                                hit_tp = (h >= effective_tp)
                                hit_sl = (l <= effective_sl) if not hit_be else (l <= effective_entry)
                                
                                if hit_sl and hit_tp:
                                    loss = True if not hit_be else False
                                    trade_resolved_idx = current_m1_idx
                                    break
                                elif hit_sl:
                                    loss = True if not hit_be else False
                                    trade_resolved_idx = current_m1_idx
                                    break
                                elif hit_tp:
                                    win = True
                                    trade_resolved_idx = current_m1_idx
                                    break
                            else:
                                hit_tp = (l <= effective_tp)
                                hit_sl = (h >= effective_sl) if not hit_be else (h >= effective_entry)
                                
                                if hit_sl and hit_tp:
                                    loss = True if not hit_be else False
                                    trade_resolved_idx = current_m1_idx
                                    break
                                elif hit_sl:
                                    loss = True if not hit_be else False
                                    trade_resolved_idx = current_m1_idx
                                    break
                                elif hit_tp:
                                    win = True
                                    trade_resolved_idx = current_m1_idx
                                    break

                        if triggered:
                            trades_executed += 1
                            daily_trade_count += 1
                            # Cooldown institucional de 10 minutos após o encerramento do trade
                            bot_busy_until_m1_idx = trade_resolved_idx + 10

                            if win:
                                wins += 1
                                daily_net_r += mult
                            elif loss:
                                losses += 1
                                daily_net_r -= 1.0
                            elif hit_be and not win:
                                be_count += 1

                            # Trava de Meta / Limite do Dia
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
        "setups_mapped": len(all_fvgs),
        "trades_executed": best['trades_executed'] if best else 0,
        "base_risk": risk_per_trade,
        "strategy_info": {
            "mode": "Execução Sequencial (Max 5 Trades/Dia)",
            "frictions": f"Spread ({spread_pts:.2f}) + Slippage + Trava Meta/Loss",
            "context": "Sessão Atual (Hoje)" if days == 0 else f"Histórico Real {days}D"
        },
        "raio_x": raio_x_results,
        "with_be": get_subset(use_ce=True, be=True),
        "without_be": get_subset(use_ce=True, be=False),
        "sniper": get_subset(use_ce=True, be=True)["sniper"],
        "tatico": get_subset(use_ce=True, be=True)["tatico"],
        "guardiao": get_subset(use_ce=True, be=True)["guardiao"],
        "recommended": f"{best['profile']} ({best['entry']} | {best['sweep']} | {best['be_label']})" if best else "TACTICAL (50% CE)"
    }

def main():
    print("==================================================")
    print("🚀 LUMI COPILOT HFT - PRO (INSTITUTIONAL SMC / SCOUT)")
    print("==================================================")

    engine = MT5Engine()
    if not engine.start(): return

    fvg_detector = FVGDetector()
    risk_manager = RiskManager()
    ia_agent = LumiGroqAgent()
    sync = SupabaseSync()
    vision = VisionLiquidityAnalyzer()

    scout = StrategyScout(engine, sync, eval_interval_seconds=3600)
    scout.start()

    processed_fvgs = set()
    last_hb = 0
    current_profile = "tatico"
    active_mode = "BOTH"
    cached_settings = {}

    sync.add_log(None, "Motor conectado com Expectativa Realista Rígida.", "INFO")

    try:
        while True:
            tick_ref = mt5.symbol_info_tick("XAUUSD") or mt5.symbol_info_tick("US100.cash")
            broker_time = datetime.fromtimestamp(tick_ref.time) if tick_ref else datetime.now()

            # 1. Telemetria e Escudo de Mesa
            acc = mt5.account_info()
            if acc:
                balance, equity = acc.balance, acc.equity
                pnl_today = equity - balance
                login, server = str(acc.login), acc.server
                
                breached, msg = risk_manager.update_account_state(balance, equity, broker_time)
                if breached:
                    sync.add_log(None, f"⛔ [PROP SHIELD] {msg} — Travando operações!", "DANGER")
                    cancel_all_pending_orders()
                    close_all_open_positions()
                    time.sleep(10)
                    continue
            else:
                balance, equity, pnl_today, login, server = 0, 0, 0, "--", "--"

            # 2. Sincronização a cada 2s
            agora = time.time()
            if agora - last_hb >= 2.0:
                last_hb = agora
                purge_stale_pending_orders(max_age_minutes=15)

                remote = sync.check_remote_settings()
                if remote:
                    cached_settings = remote
                    if remote.get("profile"): current_profile = remote.get("profile")
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

                            rep = run_recent_backtest(engine, real_sym, days, risk_manager.risk_per_trade_usd)
                            if rep:
                                try: sync.client.table("copilot_status").update({"last_backtest": rep}).eq("id", 1).execute()
                                except: pass
                                sync.add_log(real_sym, f"BACKTEST_RESULT:{json.dumps(rep)}", "SUCCESS")

                        elif "EMERGENCY_STOP" in cmd:
                            c = cancel_all_pending_orders()
                            p = close_all_open_positions()
                            sync.add_log(None, f"EMERGÊNCIA: {c} ordens canceladas, {p} posições zeradas", "DANGER")

                today_stats = get_today_performance(risk_base=risk_manager.risk_per_trade_usd)
                today_stats["scout_directives"] = scout.active_directives
                today_stats["is_auto_ai"] = bool(cached_settings.get("auto_profile_ia", False))
                today_stats["active_strategy"] = {
                    "entry_type": "50% Consequent Encroachment (CE)" if cached_settings.get("use_ce_50", True) else "Borda do FVG",
                    "breakeven": "ATIVO (1.2R)" if cached_settings.get("breakeven_enabled", True) else "DESLIGADO",
                    "trailing": "ATIVO" if cached_settings.get("trailing_enabled", False) else "DESLIGADO"
                }

                sync.send_heartbeat(current_profile, pnl_today, login, balance, equity, server, today_stats)

            # 3. Gestão de Posições Abertas
            manage_open_trades(risk_manager, cached_settings)

            # 4. Ativos Alvos
            targets = []
            if active_mode in ["BOTH", "US100"]:
                sym_nasdaq = engine.resolve_symbol("NASDAQ")
                if sym_nasdaq: targets.append(("NASDAQ", sym_nasdaq))

            if active_mode in ["BOTH", "XAUUSD"]:
                sym_gold = engine.resolve_symbol("GOLD")
                if sym_gold: targets.append(("GOLD", sym_gold))

            # 5. Varredura Operacional Institucional
            for category, symbol in targets:
                if has_active_order_or_position(symbol):
                    continue

                use_sess = cached_settings.get("use_session_filter", True)
                if use_sess and not InstitutionalSessionFilter.is_session_active(symbol, broker_time):
                    continue

                is_auto = cached_settings.get("auto_profile_ia", False)
                directive = scout.get_directive(category)

                if is_auto and not directive.get("should_trade", True):
                    continue

                active_profile_for_trade = directive.get("recommended_profile", current_profile) if is_auto else current_profile
                use_ce_50 = directive.get("use_ce_50", True) if is_auto else cached_settings.get("use_ce_50", True)
                require_sweep = directive.get("require_sweep", False) if is_auto else cached_settings.get("require_sweep", False)

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

                    if fvg.get('age_candles', 0) > 3:
                        processed_fvgs.add(fvg_id)
                        continue

                    if require_sweep and not fvg.get("has_sweep", False):
                        processed_fvgs.add(fvg_id)
                        continue

                    direction = "BUY" if fvg['type'] == 'BULLISH' else "SELL"
                    entry_candidate = fvg['ce_50'] if use_ce_50 else (fvg['top'] if direction == "BUY" else fvg['bottom'])

                    max_dist = 22.0 if "US100" in symbol or "NAS" in symbol else 3.5
                    dist = abs(current_price - entry_candidate)
                    if dist > max_dist:
                        processed_fvgs.add(fvg_id)
                        continue

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

                    ai_ok, ai_reason = ia_agent.quick_validate_trade(category, direction, active_profile_for_trade)
                    if not ai_ok:
                        processed_fvgs.add(fvg_id)
                        sync.add_log(symbol, f"Bloqueado pela IA: {ai_reason}", "WARN")
                        continue

                    action = "BUY_LIMIT" if direction == "BUY" else "SELL_LIMIT"
                    lot = risk_manager.calculate_lot_size(symbol, params["risk_points"])

                    ok, order_msg = send_limit_order(symbol, action, params["entry"], params["sl"], params["tp"], lot)
                    if ok:
                        sync.add_log(symbol, f"ORDEM ARMADA ({'IA' if is_auto else 'MANUAL'} | {active_profile_for_trade.upper()}): {action} {lot}L @ {params['entry']}", "SUCCESS")
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