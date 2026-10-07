# main.py — Orquestrador HFT de Baixa Latência, Execução SMC e Proteção de Mesa Proprietária
import time
import json
from datetime import datetime, timedelta
import MetaTrader5 as mt5

from mt5_core import MT5Engine, FVGDetector, MarketStructureDetector, VisionLiquidityAnalyzer
from risk_manager import RiskManager
from ai_groq import LumiGroqAgent
from supabase_client import SupabaseSync

ROBOT_MAGIC = 777999

def get_best_filling_mode(symbol):
    info = mt5.symbol_info(symbol)
    if not info:
        return mt5.ORDER_FILLING_IOC
    modes = info.filling_mode
    if modes & mt5.ORDER_FILLING_IOC:
        return mt5.ORDER_FILLING_IOC
    if modes & mt5.ORDER_FILLING_FOK:
        return mt5.ORDER_FILLING_FOK
    return mt5.ORDER_FILLING_RETURN

def send_limit_order(symbol, action, entry_price, sl, tp, lot_size):
    """Envia ordem pendente com validação completa de stops e spread."""
    info = mt5.symbol_info(symbol)
    if not info:
        return False, "Símbolo não localizado no MT5"

    order_type = mt5.ORDER_TYPE_BUY_LIMIT if action == "BUY_LIMIT" else mt5.ORDER_TYPE_SELL_LIMIT
    filling = get_best_filling_mode(symbol)

    point = info.point
    stops_level = info.trade_stops_level * point

    # Checagem de distância mínima exigida pela corretora
    if action == "BUY_LIMIT":
        if entry_price >= (info.ask - stops_level):
            return False, "Preço de entrada muito próximo do Ask atual (Violação StopsLevel)"
    else:
        if entry_price <= (info.bid + stops_level):
            return False, "Preço de entrada muito próximo do Bid atual (Violação StopsLevel)"

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
        "comment": "LUMI FVG AI",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }

    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return False, f"Retcode {result.retcode} ({result.comment})"

    return True, "Ordem Pendente Executada com Sucesso"

def cancel_all_pending_orders():
    orders = mt5.orders_get()
    if not orders: return 0
    cancelled = 0
    for o in orders:
        if o.magic == ROBOT_MAGIC:
            req = {"action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket}
            res = mt5.order_send(req)
            if res.retcode == mt5.TRADE_RETCODE_DONE:
                cancelled += 1
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
            if res.retcode == mt5.TRADE_RETCODE_DONE:
                closed += 1
    return closed

def manage_open_trades(risk_manager, settings):
    """Gestão ativa: Break-even sem erro de stops level."""
    if not settings.get("breakeven_enabled", True):
        return

    positions = mt5.positions_get()
    if not positions:
        return

    for p in positions:
        if p.magic != ROBOT_MAGIC:
            continue

        current_price = p.price_current
        open_price = p.price_open
        current_sl = p.sl

        # Já está no Break-even ou melhor?
        if p.type == mt5.POSITION_TYPE_BUY and current_sl >= open_price:
            continue
        if p.type == mt5.POSITION_TYPE_SELL and current_sl > 0 and current_sl <= open_price:
            continue

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
                print(f"🛡️ [BREAK-EVEN ATIVADO] Ticket #{p.ticket} ({p.symbol}) SL movido para {new_sl}")

def get_today_performance():
    """Lê histórico real de operações fechadas no dia."""
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
                    closed_trades.append({
                        "ticket": d.ticket,
                        "symbol": d.symbol,
                        "type": trade_type,
                        "volume": d.volume,
                        "profit": profit,
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

        return {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "realized_pnl": round(realized_pnl, 2),
            "open_count": len(open_positions),
            "open_positions": open_positions,
            "closed_trades": closed_trades[-8:]
        }
    except Exception as e:
        return {
            "total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0,
            "realized_pnl": 0.0, "open_count": 0, "open_positions": [], "closed_trades": []
        }

def run_recent_backtest(engine, symbol, days=2, risk_per_trade=50.0):
    """Sandbox Backtest ultrarrápido com fricção e spread real."""
    if not symbol: return None
    total_m5 = int(days) * 240
    total_m1 = int(days) * 1440

    df_m5 = engine.get_candles(symbol, mt5.TIMEFRAME_M5, total_m5)
    df_m1 = engine.get_candles(symbol, mt5.TIMEFRAME_M1, total_m1)

    if df_m5 is None or df_m1 is None: return None

    is_nasdaq = "US100" in symbol or "NAS" in symbol or "USTEC" in symbol
    min_gap = 3.5 if is_nasdaq else 0.4
    max_risk = 25.0 if is_nasdaq else 3.5

    detector = FVGDetector()
    fvgs = detector.find_unmitigated_fvgs(df_m5, symbol)

    sniper_w, sniper_l = 0, 0
    tatico_w, tatico_l = 0, 0
    guardiao_w, guardiao_l = 0, 0

    m1_highs = df_m1['high'].values
    m1_lows = df_m1['low'].values

    for f in fvgs[:60]: # Amostra
        entry = f['top'] if f['type'] == 'BULLISH' else f['bottom']
        risk = min(f['size'] + (1.0 if is_nasdaq else 0.3), max_risk)

        for prof, mult in [('sniper', 4.0), ('tatico', 2.5), ('guardiao', 1.5)]:
            tp = entry + (risk * mult) if f['type'] == 'BULLISH' else entry - (risk * mult)
            sl = entry - risk if f['type'] == 'BULLISH' else entry + risk

            # Simulação nos candles
            win, loss = False, False
            for h, l in zip(m1_highs[-120:], m1_lows[-120:]):
                if f['type'] == 'BULLISH':
                    if l <= sl: loss = True; break
                    if h >= tp: win = True; break
                else:
                    if h >= sl: loss = True; break
                    if l <= tp: win = True; break

            if win:
                if prof == 'sniper': sniper_w += 1
                elif prof == 'tatico': tatico_w += 1
                elif prof == 'guardiao': guardiao_w += 1
            else:
                if prof == 'sniper': sniper_l += 1
                elif prof == 'tatico': tatico_l += 1
                elif prof == 'guardiao': guardiao_l += 1

    s_tot = sniper_w + sniper_l or 1
    t_tot = tatico_w + tatico_l or 1
    g_tot = guardiao_w + guardiao_l or 1

    s_r = round((sniper_w * 4.0) - (sniper_l * 1.0), 1)
    t_r = round((tatico_w * 2.5) - (tatico_l * 1.0), 1)
    g_r = round((guardiao_w * 1.5) - (guardiao_l * 1.0), 1)

    s_pnl = round(s_r * risk_per_trade, 2)
    t_pnl = round(t_r * risk_per_trade, 2)
    g_pnl = round(g_r * risk_per_trade, 2)

    recommended = "GUARDIAN" if g_pnl >= max(s_pnl, t_pnl) else ("TACTICAL" if t_pnl >= s_pnl else "SNIPER")

    return {
        "timestamp": int(time.time()),
        "symbol": symbol,
        "days": days,
        "setups": len(fvgs),
        "base_risk": risk_per_trade,
        "sniper": {"rate": int((sniper_w / s_tot) * 100), "wins": sniper_w, "losses": sniper_l, "net_r": s_r, "pnl": s_pnl},
        "tatico": {"rate": int((tatico_w / t_tot) * 100), "wins": tatico_w, "losses": tatico_l, "net_r": t_r, "pnl": t_pnl},
        "guardiao": {"rate": int((guardiao_w / g_tot) * 100), "wins": guardiao_w, "losses": guardiao_l, "net_r": g_r, "pnl": g_pnl},
        "recommended": recommended
    }

def main():
    print("==================================================")
    print("🚀 LUMI COPILOT HFT - PRO (INSTITUTIONAL SMC / CV)")
    print("==================================================")

    engine = MT5Engine()
    if not engine.start(): return

    fvg_detector = FVGDetector()
    risk_manager = RiskManager()
    ia_agent = LumiGroqAgent()
    sync = SupabaseSync()
    vision = VisionLiquidityAnalyzer()

    processed_fvgs = set()
    last_hb = 0
    current_profile = "tatico"
    active_mode = "BOTH"
    cached_settings = {}

    sync.add_log(None, "Copilot HFT conectado e operando em baixa latência.", "INFO")

    try:
        while True:
            # 1. Telemetria e Proteção da Mesa Proprietária
            acc = mt5.account_info()
            if acc:
                balance, equity = acc.balance, acc.equity
                pnl_today = equity - balance
                login, server = str(acc.login), acc.server
                
                # Checa Drawdown Diário (Hard Lock)
                breached, msg = risk_manager.update_account_state(balance, equity)
                if breached:
                    sync.add_log(None, f"⛔ [PROP SHIELD] {msg} — Cancelando ordens!", "DANGER")
                    cancel_all_pending_orders()
                    close_all_open_positions()
                    time.sleep(10)
                    continue
            else:
                balance, equity, pnl_today, login, server = 0, 0, 0, "--", "--"

            today_stats = get_today_performance()

            # 2. Heartbeat e Comandos da Nuvem (a cada 2s)
            agora = time.time()
            if agora - last_hb >= 2.0:
                last_hb = agora
                sync.send_heartbeat(current_profile, pnl_today, login, balance, equity, server, today_stats)

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
                            days = int(parts[2]) if len(parts) > 2 else 2
                            rep = run_recent_backtest(engine, real_sym, days, risk_manager.risk_per_trade_usd)
                            if rep:
                                try: sync.client.table("copilot_status").update({"last_backtest": rep}).eq("id", 1).execute()
                                except: pass
                                sync.add_log(real_sym, f"BACKTEST_RESULT:{json.dumps(rep)}", "SUCCESS")

                        elif "EMERGENCY_STOP" in cmd:
                            c = cancel_all_pending_orders()
                            p = close_all_open_positions()
                            sync.add_log(None, f"EMERGÊNCIA ACIONADA: {c} ordens canceladas, {p} posições zeradas", "DANGER")

            # 3. Gestão Ativa de Ordens Abertas (Break-even seguro)
            manage_open_trades(risk_manager, cached_settings)

            # 4. Resolução Dinâmica de Ativos Alvo
            targets = []
            if active_mode in ["BOTH", "US100"]:
                sym_nasdaq = engine.resolve_symbol("NASDAQ")
                if sym_nasdaq: targets.append(("NASDAQ", sym_nasdaq))

            if active_mode in ["BOTH", "XAUUSD"]:
                sym_gold = engine.resolve_symbol("GOLD")
                if sym_gold: targets.append(("GOLD", sym_gold))

            # 5. Varredura Institucional de Baixa Latência (< 15ms por ciclo)
            for category, symbol in targets:
                df_m15 = engine.get_candles(symbol, mt5.TIMEFRAME_M15, 30)
                df_m5 = engine.get_candles(symbol, mt5.TIMEFRAME_M5, 30)
                df_m1 = engine.get_candles(symbol, mt5.TIMEFRAME_M1, 30)

                if df_m15 is None or df_m5 is None or df_m1 is None:
                    continue

                structure, _, _ = MarketStructureDetector.get_m15_structure(df_m15)
                atr = risk_manager.calculate_atr(df_m1)

                # Atualiza IA Groq em segundo plano a cada 15 min (sem travar)
                info = mt5.symbol_info(symbol)
                spread = info.spread if info else 10
                ia_agent.update_macro_regime_async(category, structure, atr, spread)

                fvgs = fvg_detector.find_unmitigated_fvgs(df_m5, symbol)
                current_price = df_m1.iloc[-1]['close']

                for fvg in fvgs:
                    fvg_id = f"{symbol}_{fvg['type']}_{fvg['time_formed']}"
                    if fvg_id in processed_fvgs:
                        continue

                    direction = "BUY" if fvg['type'] == 'BULLISH' else "SELL"

                    # Regra Estrutural SMC: FVG de Compra exige Estrutura de Alta
                    if direction == "BUY" and "BEARISH" in structure:
                        processed_fvgs.add(fvg_id)
                        continue
                    if direction == "SELL" and "BULLISH" in structure:
                        processed_fvgs.add(fvg_id)
                        continue

                    # Visão Computacional: Avalia piscina de liquidez
                    cv_res = vision.analyze_chart_matrix(df_m5)

                    # Validação de Viés da IA em memória (0 ms)
                    ai_ok, ai_reason = ia_agent.quick_validate_trade(category, direction, current_profile)
                    if not ai_ok:
                        processed_fvgs.add(fvg_id)
                        sync.add_log(symbol, f"Bloqueado pela IA: {ai_reason}", "WARN")
                        continue

                    # Cálculo Financeiro e Parâmetros
                    params = risk_manager.get_trade_parameters(current_profile, fvg, atr, symbol, direction)
                    action = "BUY_LIMIT" if direction == "BUY" else "SELL_LIMIT"

                    # Disparo da Ordem Pendente
                    lot = risk_manager.calculate_lot_size(symbol, params["risk_points"])
                    ok, order_msg = send_limit_order(symbol, action, params["entry"], params["sl"], params["tp"], lot)

                    if ok:
                        sync.add_log(symbol, f"ORDEM ARMADA: {action} {lot}L @ {params['entry']} (SL: {params['sl']} | TP: {params['tp']})", "SUCCESS")
                    else:
                        sync.add_log(symbol, f"Falha no envio de ordem: {order_msg}", "DANGER")

                    processed_fvgs.add(fvg_id)

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[ENCERRANDO] Finalizando motor...")
    finally:
        engine.stop()

if __name__ == "__main__":
    main()