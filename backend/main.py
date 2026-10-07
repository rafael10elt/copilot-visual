# main.py — Orquestrador HFT com Modo Manual/IA Flexível e Stop Loss Institucional Calibrado
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

def run_recent_backtest(engine, symbol, days=5, risk_per_trade=50.0, use_ce_50=True, require_sweep=False, use_session_filter=True):
    """
    Backtest Institucional A/B Calibrado:
    Simula e compara lado a lado COM e SEM Break-Even, com espaço para volatilidade.
    """
    if not symbol: return None
    total_m5 = int(days) * 240
    total_m1 = int(days) * 1440

    df_m5 = engine.get_candles(symbol, mt5.TIMEFRAME_M5, total_m5)
    df_m1 = engine.get_candles(symbol, mt5.TIMEFRAME_M1, total_m1)

    if df_m5 is None or df_m1 is None: return None

    is_nasdaq = "US100" in symbol or "NAS" in symbol or "USTEC" in symbol
    min_stop_points = 6.0 if is_nasdaq else 1.2
    max_risk = 30.0 if is_nasdaq else 4.5

    detector = FVGDetector()
    vision = VisionLiquidityAnalyzer()
    fvgs = detector.find_unmitigated_fvgs(df_m5, symbol)

    m1_highs = df_m1['high'].values
    m1_lows = df_m1['low'].values
    m1_times = df_m1['time'].values

    no_be = {
        "sniper": {"wins": 0, "losses": 0},
        "tatico": {"wins": 0, "losses": 0},
        "guardiao": {"wins": 0, "losses": 0}
    }

    with_be = {
        "sniper": {"wins": 0, "losses": 0, "be_count": 0},
        "tatico": {"wins": 0, "losses": 0, "be_count": 0},
        "guardiao": {"wins": 0, "losses": 0, "be_count": 0}
    }

    valid_setups = 0

    for f in fvgs:
        if use_session_filter and not InstitutionalSessionFilter.is_session_active(symbol, f['raw_time']):
            continue

        if require_sweep and not f.get("has_sweep", False):
            continue

        direction = "BUY" if f['type'] == 'BULLISH' else "SELL"
        entry = f['ce_50'] if use_ce_50 else (f['top'] if direction == "BUY" else f['bottom'])

        # Stop Técnico Seguro (não deixa ficar menor que o ruído mínimo do ativo)
        raw_dist = abs(entry - (f['bottom'] if direction == "BUY" else f['top']))
        risk = min(max(raw_dist + (1.5 if is_nasdaq else 0.5), min_stop_points), max_risk)

        tp_tatico = entry + (risk * 2.5) if direction == "BUY" else entry - (risk * 2.5)

        path_ok, _ = vision.validate_liquidity_path(df_m5, direction, entry, tp_tatico)
        if not path_ok:
            continue

        valid_setups += 1

        start_idx = 0
        for idx in range(len(m1_times)):
            if m1_times[idx] >= f['raw_time']:
                start_idx = idx
                break

        if start_idx == 0: continue

        # Janela de resolução de 120 velas M1 (2 horas)
        sim_slice_h = m1_highs[start_idx : min(start_idx + 120, len(m1_highs))]
        sim_slice_l = m1_lows[start_idx : min(start_idx + 120, len(m1_lows))]

        for prof, mult in [('sniper', 4.0), ('tatico', 2.5), ('guardiao', 1.5)]:
            tp = entry + (risk * mult) if direction == "BUY" else entry - (risk * mult)
            sl = entry - risk if direction == "BUY" else entry + risk

            triggered = False
            win_no_be, loss_no_be = False, False
            win_with_be, loss_with_be, hit_be = False, False, False

            for h, l in zip(sim_slice_h, sim_slice_l):
                if not triggered:
                    if direction == "BUY" and l <= entry: triggered = True
                    elif direction == "SELL" and h >= entry: triggered = True
                    if not triggered: continue

                # Trilha Sem Break-Even
                if not (win_no_be or loss_no_be):
                    if direction == "BUY":
                        if l <= sl: loss_no_be = True
                        elif h >= tp: win_no_be = True
                    else:
                        if h >= sl: loss_no_be = True
                        elif l <= tp: win_no_be = True

                # Trilha Com Break-Even (em 1.2R)
                if not (win_with_be or loss_with_be or hit_be):
                    if not hit_be:
                        if direction == "BUY" and h >= (entry + risk * 1.2): hit_be = True
                        elif direction == "SELL" and l <= (entry - risk * 1.2): hit_be = True

                    if direction == "BUY":
                        if hit_be and l <= entry: break
                        elif not hit_be and l <= sl: loss_with_be = True; break
                        elif h >= tp: win_with_be = True; break
                    else:
                        if hit_be and h >= entry: break
                        elif not hit_be and h >= sl: loss_with_be = True; break
                        elif l <= tp: win_with_be = True; break

            if triggered:
                if win_no_be: no_be[prof]["wins"] += 1
                elif loss_no_be: no_be[prof]["losses"] += 1

                if win_with_be: with_be[prof]["wins"] += 1
                elif loss_with_be: with_be[prof]["losses"] += 1
                elif hit_be and not win_with_be: with_be[prof]["be_count"] += 1

    def build_stats(w, l, mult, be_cnt=0):
        tot = w + l
        rate = int((w / tot) * 100) if tot > 0 else 0
        net_r = round((w * mult) - (l * 1.0), 1)
        pnl = round(net_r * risk_per_trade, 2)
        res = {"rate": rate, "wins": w, "losses": l, "net_r": net_r, "pnl": pnl}
        if be_cnt > 0: res["be_count"] = be_cnt
        return res

    report_no_be = {
        "sniper": build_stats(no_be["sniper"]["wins"], no_be["sniper"]["losses"], 4.0),
        "tatico": build_stats(no_be["tatico"]["wins"], no_be["tatico"]["losses"], 2.5),
        "guardiao": build_stats(no_be["guardiao"]["wins"], no_be["guardiao"]["losses"], 1.5)
    }

    report_with_be = {
        "sniper": build_stats(with_be["sniper"]["wins"], with_be["sniper"]["losses"], 4.0, with_be["sniper"]["be_count"]),
        "tatico": build_stats(with_be["tatico"]["wins"], with_be["tatico"]["losses"], 2.5, with_be["tatico"]["be_count"]),
        "guardiao": build_stats(with_be["guardiao"]["wins"], with_be["guardiao"]["losses"], 1.5, with_be["guardiao"]["be_count"])
    }

    best_pnl = -99999
    recommended_mode = "TACTICAL (COM BE)"
    for rep, is_be in [(report_no_be, False), (report_with_be, True)]:
        for p_name in ["guardiao", "tatico", "sniper"]:
            pnl_val = rep[p_name]["pnl"]
            if pnl_val > best_pnl:
                best_pnl = pnl_val
                p_display = "GUARDIAN" if p_name == "guardiao" else ("TACTICAL" if p_name == "tatico" else "SNIPER")
                recommended_mode = f"{p_display} ({'COM BE' if is_be else 'SEM BE'})"

    return {
        "timestamp": int(time.time()),
        "symbol": symbol,
        "days": days,
        "setups": valid_setups,
        "base_risk": risk_per_trade,
        "strategy_info": {
            "entry": "50% Consequent Encroachment" if use_ce_50 else "Borda do FVG",
            "sessions": "Killzones Ativas" if use_session_filter else "24 Horas",
            "cv_filter": "Barreiras de Absorção Ativas"
        },
        "without_be": report_no_be,
        "with_be": report_with_be,
        "sniper": report_with_be["sniper"],
        "tatico": report_with_be["tatico"],
        "guardiao": report_with_be["guardiao"],
        "recommended": recommended_mode
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

    sync.add_log(None, "Motor inicializado com controle manual/IA e Stop calibrado.", "INFO")

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
                            days = int(parts[2]) if len(parts) > 2 else 5

                            is_auto = cached_settings.get("auto_profile_ia", False)
                            scout_dir = scout.get_directive(cat)

                            use_ce = scout_dir.get("use_ce_50", True) if is_auto else cached_settings.get("use_ce_50", True)
                            req_sweep = scout_dir.get("require_sweep", False) if is_auto else cached_settings.get("require_sweep", False)
                            use_sess = cached_settings.get("use_session_filter", True)

                            rep = run_recent_backtest(
                                engine, real_sym, days, risk_manager.risk_per_trade_usd,
                                use_ce_50=use_ce, require_sweep=req_sweep, use_session_filter=use_sess
                            )
                            if rep:
                                try: sync.client.table("copilot_status").update({"last_backtest": rep}).eq("id", 1).execute()
                                except: pass
                                sync.add_log(real_sym, f"BACKTEST_RESULT:{json.dumps(rep)}", "SUCCESS")

                        elif "EMERGENCY_STOP" in cmd:
                            c = cancel_all_pending_orders()
                            p = close_all_open_positions()
                            sync.add_log(None, f"EMERGÊNCIA: {c} ordens canceladas, {p} posições zeradas", "DANGER")

                # Monta estatísticas com Scout & Estratégia Ativa
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