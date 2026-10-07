import time
import json
import MetaTrader5 as mt5
from mt5_core import MT5Engine, FVGDetector
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
        "comment": "LUMI FVG AI",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ MT5 Order Error on {symbol}: Retcode {result.retcode} ({result.comment})")
        return False
    return True

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
                "deviation": 15,
                "magic": ROBOT_MAGIC,
                "comment": "EMERGENCY_FLATTEN"
            }
            res = mt5.order_send(req)
            if res.retcode == mt5.TRADE_RETCODE_DONE:
                closed += 1
    return closed

def manage_open_trades(settings):
    positions = mt5.positions_get()
    if not positions: return

    for p in positions:
        if p.magic != ROBOT_MAGIC: continue

        current_price = p.price_current
        entry_price = p.price_open
        sl = p.sl

        if settings.get("breakeven_enabled"):
            buffer = 2.0 if "US100" in p.symbol else 0.5
            if p.type == mt5.POSITION_TYPE_BUY:
                if current_price >= (entry_price + buffer) and sl < entry_price:
                    req = {"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": float(entry_price + 0.1), "tp": p.tp}
                    mt5.order_send(req)
            elif p.type == mt5.POSITION_TYPE_SELL:
                if current_price <= (entry_price - buffer) and sl > entry_price:
                    req = {"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": float(entry_price - 0.1), "tp": p.tp}
                    mt5.order_send(req)

def run_recent_backtest(engine, symbol, days=2, risk_per_trade=50.0):
    """
    BACKTEST QUANTITATIVO ULTRA-REALISTA (Com Fricção de Spread, Concorrência Real e Teto de Stop)
    """
    print(f"\n📊 [BACKTEST] Running institutional-grade M1 scan for {symbol} ({days}D)...")

    total_m5 = int(days) * 240
    df_m5 = engine.get_candles(symbol, mt5.TIMEFRAME_M5, total_m5)

    total_m1 = int(days) * 1440
    df_m1 = engine.get_candles(symbol, mt5.TIMEFRAME_M1, total_m1)

    if df_m5 is None or df_m1 is None or len(df_m5) < 20 or len(df_m1) < 100:
        print(f"⚠️ [BACKTEST] Insufficient candles for {symbol}.")
        return None

    m1_highs = df_m1['high'].values
    m1_lows = df_m1['low'].values
    m1_times = df_m1['time'].values

    m5_highs = df_m5['high'].values
    m5_lows = df_m5['low'].values
    m5_times = df_m5['time'].values

    # Parâmetros de Fricção e Tetos Institucionais
    is_nasdaq = "US100" in symbol
    min_gap = 4.0 if is_nasdaq else 0.5
    max_allowed_risk = 25.0 if is_nasdaq else 3.5  # Teto de Stop Loss (Scalp puro)
    spread_friction = 1.2 if is_nasdaq else 0.25   # Fricção real de Spread + Comissão FTMO

    setups = 0
    sniper_wins, sniper_losses = 0, 0
    tatico_wins, tatico_losses = 0, 0
    guardiao_wins, guardiao_losses = 0, 0

    # Ponteiro para simular ocupação de posição real (não empilha trades enquanto estiver posicionado)
    in_trade_until_idx = {
        'sniper': 0,
        'tatico': 0,
        'guardiao': 0
    }

    for i in range(len(df_m5) - 10):
        c1_high, c1_low = m5_highs[i], m5_lows[i]
        c3_high, c3_low = m5_highs[i+2], m5_lows[i+2]
        fvg_time = m5_times[i+2]

        is_buy = c3_low > c1_high and (c3_low - c1_high) >= min_gap
        is_sell = c3_high < c1_low and (c1_low - c3_high) >= min_gap

        if not (is_buy or is_sell):
            continue

        # Sincroniza o momento exato no M1
        m1_start_idx = 0
        for idx in range(len(m1_times) - 60):
            if m1_times[idx] >= fvg_time:
                m1_start_idx = idx
                break

        if m1_start_idx == 0:
            continue

        # Aplica o Teto Máximo de Stop Loss
        raw_risk = abs(c3_low - c1_high) if is_buy else abs(c1_low - c3_high)
        if raw_risk > (max_allowed_risk * 1.5):
            continue  # Descarta anomalias causadas por velas gigantes de notícia

        capped_risk = min(raw_risk + spread_friction, max_allowed_risk)
        setups += 1

        sim_highs = m1_highs[m1_start_idx : min(m1_start_idx + 60, len(m1_highs))]
        sim_lows = m1_lows[m1_start_idx : min(m1_start_idx + 60, len(m1_lows))]

        for profile, mult in [('sniper', 4.0), ('tatico', 2.5), ('guardiao', 1.5)]:
            # Se a simulação já estiver com um trade aberto neste perfil, pula (evita simultaneidade irreal)
            if m1_start_idx < in_trade_until_idx[profile]:
                continue

            entry = c3_low if is_buy else c3_high
            risk = capped_risk
            
            # Adiciona o spread no alvo e stop
            tp = entry + (risk * mult) if is_buy else entry - (risk * mult)
            sl = entry - risk if is_buy else entry + risk

            win, loss = False, False
            bars_taken = 0

            for h, l in zip(sim_highs, sim_lows):
                bars_taken += 1
                if is_buy:
                    if l <= sl:
                        loss = True
                        break
                    if h >= tp:
                        win = True
                        break
                else:
                    if h >= sl:
                        loss = True
                        break
                    if l <= tp:
                        win = True
                        break

            # Registra até quando o trade ficou aberto
            in_trade_until_idx[profile] = m1_start_idx + bars_taken

            if win:
                if profile == 'sniper': sniper_wins += 1
                elif profile == 'tatico': tatico_wins += 1
                elif profile == 'guardiao': guardiao_wins += 1
            elif loss:
                if profile == 'sniper': sniper_losses += 1
                elif profile == 'tatico': tatico_losses += 1
                elif profile == 'guardiao': guardiao_losses += 1

    if setups == 0:
        setups = 1

    # Cálculos Quantitativos Finais
    total_trades_s = sniper_wins + sniper_losses or 1
    total_trades_t = tatico_wins + tatico_losses or 1
    total_trades_g = guardiao_wins + guardiao_losses or 1

    s_rate = int((sniper_wins / total_trades_s) * 100)
    t_rate = int((tatico_wins / total_trades_t) * 100)
    g_rate = int((guardiao_wins / total_trades_g) * 100)

    s_net_r = round((sniper_wins * 4.0) - (sniper_losses * 1.0), 1)
    t_net_r = round((tatico_wins * 2.5) - (tatico_losses * 1.0), 1)
    g_net_r = round((guardiao_wins * 1.5) - (guardiao_losses * 1.0), 1)

    s_pnl = round(s_net_r * risk_per_trade, 2)
    t_pnl = round(t_net_r * risk_per_trade, 2)
    g_pnl = round(g_net_r * risk_per_trade, 2)

    if g_pnl >= max(s_pnl, t_pnl):
        recommended = "GUARDIAN"
    elif t_pnl >= s_pnl:
        recommended = "TACTICAL"
    else:
        recommended = "SNIPER"

    report = {
        "timestamp": int(time.time()),
        "symbol": symbol,
        "days": days,
        "setups": setups,
        "base_risk": risk_per_trade,
        "sniper": {
            "rate": s_rate,
            "wins": sniper_wins,
            "losses": sniper_losses,
            "net_r": s_net_r,
            "pnl": s_pnl
        },
        "tatico": {
            "rate": t_rate,
            "wins": tatico_wins,
            "losses": tatico_losses,
            "net_r": t_net_r,
            "pnl": t_pnl
        },
        "guardiao": {
            "rate": g_rate,
            "wins": guardiao_wins,
            "losses": guardiao_losses,
            "net_r": g_net_r,
            "pnl": g_pnl
        },
        "recommended": recommended
    }
    print(f"✅ [REALISTIC BACKTEST] Trades simulados com atrito de spread e concorrência real finalizados.")
    return report

def get_m15_trend(engine, symbol):
    df_m15 = engine.get_candles(symbol, mt5.TIMEFRAME_M15, 20)
    if df_m15 is None: return "NEUTRAL"
    return "UPTREND" if df_m15.iloc[-1]['close'] > df_m15.iloc[0]['close'] else "DOWNTREND"

def is_fvg_close_enough(current_price, entry_price, tp_price, action, symbol):
    dist = abs(current_price - entry_price)
    max_dist = 25.0 if "US100" in symbol else 3.5

    if dist > max_dist:
        return False, f"Too far from current market ({dist:.2f} pts gap)"

    if action == "SELL_LIMIT" and current_price <= tp_price:
        return False, "Target expansion already occurred (Price below TP)"
    if action == "BUY_LIMIT" and current_price >= tp_price:
        return False, "Target expansion already occurred (Price above TP)"

    return True, "Valid proximity"

def main():
    print("=======================================")
    print("🚀 LUMI COPILOT HFT - PRO (INSTITUTIONAL)")
    print("=======================================")

    engine = MT5Engine()
    if not engine.start(): return

    fvg_detector = FVGDetector()
    risk_manager = RiskManager()
    ia_agent = LumiGroqAgent()
    sync = SupabaseSync()

    processed_fvgs = []
    last_hb = 0
    current_profile = "tatico"
    active_mode = "BOTH"
    cached_settings = {}

    sync.add_log(None, "Copilot engine connected to MT5 terminal", "INFO")

    try:
        while True:
            # 1. Puxa métricas da FTMO
            acc = mt5.account_info()
            if acc:
                balance, equity = acc.balance, acc.equity
                pnl_today = equity - balance
                login, server = str(acc.login), acc.server
            else:
                balance, equity, pnl_today, login, server = 0, 0, 0, "--", "--"

            # 2. Sincronização e Leitura de Comandos
            agora = time.time()
            if agora - last_hb >= 2.0:
                last_hb = agora
                sync.send_heartbeat(current_profile, pnl_today, login, balance, equity, server)

                remote = sync.check_remote_settings()
                if remote:
                    cached_settings = remote
                    if remote.get("profile") and remote.get("profile") != current_profile:
                        current_profile = remote.get("profile")
                        sync.add_log(None, f"Profile switched to: {current_profile.upper()}", "WARN")

                    if remote.get("risk_per_trade"):
                        risk_manager.risk_per_trade_usd = float(remote.get("risk_per_trade"))
                    if remote.get("max_daily_loss"):
                        risk_manager.max_daily_loss_usd = float(remote.get("max_daily_loss"))
                    if remote.get("active_symbol_mode"):
                        active_mode = remote.get("active_symbol_mode")

                    # CANAL DIRETO DE COMANDO
                    cmd = remote.get("command")
                    if cmd:
                        print(f"📥 [DIRECT COMMAND RECEIVED] {cmd}")
                        try:
                            sync.client.table("copilot_settings").update({"command": None}).eq("id", 1).execute()
                        except: pass

                        if "RUN_BACKTEST" in cmd:
                            parts = cmd.split(":")
                            target_sym = parts[1] if len(parts) > 1 else "US100.cash"
                            target_days = int(parts[2]) if len(parts) > 2 else 2
                            user_risk = float(remote.get("risk_per_trade") or 50.0)

                            report = run_recent_backtest(engine, target_sym, target_days, user_risk)
                            if report:
                                try:
                                    sync.client.table("copilot_status").update({"last_backtest": report}).eq("id", 1).execute()
                                except Exception as e:
                                    print(f"Erro ao salvar backtest: {e}")
                                sync.add_log(target_sym, f"BACKTEST_RESULT:{json.dumps(report)}", "SUCCESS")
                            else:
                                sync.add_log(target_sym, "BACKTEST FAILED: Insufficient candles", "DANGER")

                        elif "EMERGENCY_STOP" in cmd:
                            c = cancel_all_pending_orders()
                            p = close_all_open_positions()
                            sync.add_log(None, f"EMERGENCY EXECUTED: Cancelled {c} orders, closed {p} positions", "DANGER")

            # 3. Gestão Ativa de Ordens (BE & Trailing)
            manage_open_trades(cached_settings)

            # 4. Ativos Ativos
            if active_mode == "US100":
                ativos_atuais = ["US100.cash"]
            elif active_mode == "XAUUSD":
                ativos_atuais = ["XAUUSD"]
            else:
                ativos_atuais = ["US100.cash", "XAUUSD"]

            # 5. Varredura Operacional
            for symbol in ativos_atuais:
                df_m5 = engine.get_candles(symbol, mt5.TIMEFRAME_M5, 30)
                df_m1 = engine.get_candles(symbol, mt5.TIMEFRAME_M1, 15)
                if df_m5 is None or df_m1 is None: continue

                current_price = df_m1.iloc[-1]['close']
                fvgs = fvg_detector.find_unmitigated_fvgs(df_m5, symbol)
                atr_m1 = risk_manager.calculate_atr(df_m1)
                m15_trend = get_m15_trend(engine, symbol)

                for fvg in fvgs:
                    fvg_id = f"{symbol}_{fvg['type']}_{fvg['time_formed']}"
                    if fvg_id not in processed_fvgs:
                        base_price = fvg['top'] if fvg['type'] == 'BULLISH' else fvg['bottom']
                        action_candidate = "BUY_LIMIT" if fvg['type'] == 'BULLISH' else "SELL_LIMIT"
                        direction = "BUY" if fvg['type'] == 'BULLISH' else "SELL"

                        params = risk_manager.get_trade_parameters(current_profile, fvg, atr_m1, symbol, direction)

                        valid, dist_msg = is_fvg_close_enough(current_price, params["entry"], params["tp"], action_candidate, symbol)
                        if not valid:
                            processed_fvgs.append(fvg_id)
                            sync.add_log(symbol, f"Ignored {fvg['type']} FVG: {dist_msg}", "WARN")
                            continue

                        sync.add_log(symbol, f"Valid proximity for {fvg['type']} FVG at {params['entry']}. Consulting AI...", "INFO")
                        ai = ia_agent.validate_fvg_trade(symbol, fvg['type'], base_price, m15_trend, atr_m1, current_profile)

                        if ai.get("autorizado", False):
                            lot = risk_manager.calculate_lot_size(symbol, params["risk_points"])
                            success = send_limit_order(symbol, ai["acao"], params["entry"], params["sl"], params["tp"], lot)
                            if success:
                                sync.add_log(symbol, f"ORDER ARMED: {ai['acao']} {lot} lots at {params['entry']}", "SUCCESS")
                            else:
                                sync.add_log(symbol, f"Execution failed in MT5 terminal", "DANGER")
                        else:
                            sync.add_log(symbol, f"AI Rejected setup: {ai['motivo']}", "WARN")

                        processed_fvgs.append(fvg_id)

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nShutting down engine...")
    finally:
        engine.stop()

if __name__ == "__main__":
    main()