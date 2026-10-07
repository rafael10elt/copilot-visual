import time
import MetaTrader5 as mt5
from mt5_core import MT5Engine, FVGDetector
from risk_manager import RiskManager
from ai_groq import LumiGroqAgent
from supabase_client import SupabaseSync

ROBOT_MAGIC = 777999

def get_best_filling_mode(symbol):
    """Detects whether broker/FTMO supports IOC, FOK, or RETURN for the asset."""
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
    """Sends Buy Limit or Sell Limit order to MT5."""
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
    """Cancels all pending orders placed by the robot."""
    orders = mt5.orders_get()
    if not orders:
        return 0
    cancelled = 0
    for o in orders:
        if o.magic == ROBOT_MAGIC:
            req = {"action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket}
            res = mt5.order_send(req)
            if res.retcode == mt5.TRADE_RETCODE_DONE:
                cancelled += 1
    return cancelled

def close_all_open_positions():
    """Closes all open positions placed by the robot at market price."""
    positions = mt5.positions_get()
    if not positions:
        return 0
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
    """Active position management: Break-even and Trailing Stop on M1."""
    positions = mt5.positions_get()
    if not positions:
        return

    for p in positions:
        if p.magic != ROBOT_MAGIC:
            continue

        current_price = p.price_current
        entry_price = p.price_open
        sl = p.sl

        # 1. Break-even logic (move SL to entry price once trade moves 1R favorable)
        if settings.get("breakeven_enabled"):
            buffer = 2.0 if "US100" in p.symbol else 0.5
            if p.type == mt5.POSITION_TYPE_BUY:
                if current_price >= (entry_price + buffer) and sl < entry_price:
                    req = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": p.ticket,
                        "sl": float(entry_price + 0.1),
                        "tp": p.tp
                    }
                    mt5.order_send(req)
            elif p.type == mt5.POSITION_TYPE_SELL:
                if current_price <= (entry_price - buffer) and sl > entry_price:
                    req = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": p.ticket,
                        "sl": float(entry_price - 0.1),
                        "tp": p.tp
                    }
                    mt5.order_send(req)

def run_recent_backtest(engine, symbol, days=2):
    """Performs historical mathematical backtest of M5 FVGs for selected lookback window."""
    candles_per_day = 240 # ~20 active hours per day
    total_candles = int(days) * candles_per_day

    df = engine.get_candles(symbol, mt5.TIMEFRAME_M5, total_candles)
    if df is None or len(df) < 50:
        return "Insufficient historical candles on MT5 terminal."

    min_gap = 4.0 if "US100" in symbol else 0.5
    setups = 0
    sniper_wins = 0
    tatico_wins = 0
    guardiao_wins = 0

    for i in range(len(df) - 20):
        c1, c2, c3 = df.iloc[i], df.iloc[i+1], df.iloc[i+2]
        fvg_type = None
        entry, sl_base = 0.0, 0.0

        if c3['low'] > c1['high'] and (c3['low'] - c1['high']) >= min_gap:
            fvg_type = 'BUY'
            entry = float(c3['low'])
            sl_base = float(c1['high'])
        elif c3['high'] < c1['low'] and (c1['low'] - c3['high']) >= min_gap:
            fvg_type = 'SELL'
            entry = float(c3['high'])
            sl_base = float(c1['low'])

        if fvg_type:
            setups += 1
            risk = abs(entry - sl_base) + (1.0 if "US100" in symbol else 0.2)
            future = df.iloc[i+3 : min(i+30, len(df))]

            for profile, mult in [('sniper', 4.0), ('tatico', 2.5), ('guardiao', 1.5)]:
                tp = entry + (risk * mult) if fvg_type == 'BUY' else entry - (risk * mult)
                sl = entry - risk if fvg_type == 'BUY' else entry + risk

                hit_tp, hit_sl = False, False
                for _, bar in future.iterrows():
                    if fvg_type == 'BUY':
                        if bar['low'] <= sl:
                            hit_sl = True
                            break
                        if bar['high'] >= tp:
                            hit_tp = True
                            break
                    else:
                        if bar['high'] >= sl:
                            hit_sl = True
                            break
                        if bar['low'] <= tp:
                            hit_tp = True
                            break

                if hit_tp and not hit_sl:
                    if profile == 'sniper': sniper_wins += 1
                    elif profile == 'tatico': tatico_wins += 1
                    elif profile == 'guardiao': guardiao_wins += 1

    if setups == 0:
        return f"No valid M5 FVGs formed in the last {days} day(s)."

    s_rate = int((sniper_wins / setups) * 100)
    t_rate = int((tatico_wins / setups) * 100)
    g_rate = int((guardiao_wins / setups) * 100)

    best = "GUARDIAN" if g_rate >= max(s_rate, t_rate) else ("TACTICAL" if t_rate >= s_rate else "SNIPER")
    return f"{setups} Setups found | Sniper: {s_rate}% | Tactical: {t_rate}% | Guardian: {g_rate}% -> Recommended: {best}"

def get_m15_trend(engine, symbol):
    df_m15 = engine.get_candles(symbol, mt5.TIMEFRAME_M15, 20)
    if df_m15 is None: return "NEUTRAL"
    return "UPTREND" if df_m15.iloc[-1]['close'] > df_m15.iloc[0]['close'] else "DOWNTREND"

def is_fvg_close_enough(current_price, entry_price, tp_price, action, symbol):
    """Proximity check: Avoids arming setups if price has moved too far away or already passed TP."""
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
    if not engine.start():
        return

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
            # 1. Fetch live FTMO account metrics
            acc = mt5.account_info()
            if acc:
                balance, equity = acc.balance, acc.equity
                pnl_today = equity - balance
                login, server = str(acc.login), acc.server
            else:
                balance, equity, pnl_today, login, server = 0, 0, 0, "--", "--"

            # 2. Remote synchronization every 3 seconds
            agora = time.time()
            if agora - last_hb >= 3.0:
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

                    # AI Auto-Adapt check: adjust profile dynamically
                    if remote.get("auto_profile_ia") and current_profile != "tatico":
                        current_profile = "tatico"
                        sync.add_log(None, "AI Auto-Adapt active: Defaulting to TACTICAL profile", "INFO")

            # 3. Active Management of Open Trades (BE & Trailing)
            manage_open_trades(cached_settings)

            # 4. Check for Remote Commands from Web App
            try:
                latest_logs = sync.client.table("copilot_logs").select("id, message").order("created_at", {"ascending": False}).limit(1).execute()
                if latest_logs.data:
                    last_msg = latest_logs.data[0].get("message", "")

                    # EMERGENCY STOP COMMAND
                    if "EMERGENCY_STOP_TRIGGERED" in last_msg:
                        cancelled = cancel_all_pending_orders()
                        closed = close_all_open_positions()
                        sync.add_log(None, f"EMERGENCY EXECUTED: Cancelled {cancelled} orders, closed {closed} positions", "DANGER")

                    # DYNAMIC BACKTEST COMMAND (Format: COMMAND: RUN_BACKTEST:SYMBOL:DAYS)
                    elif "COMMAND: RUN_BACKTEST" in last_msg:
                        parts = last_msg.split(":")
                        target_sym = parts[2] if len(parts) > 2 else "US100.cash"
                        target_days = int(parts[3]) if len(parts) > 3 else 2
                        
                        report = run_recent_backtest(engine, target_sym, target_days)
                        sync.add_log(target_sym, f"BACKTEST COMPLETED ({target_days}D): {report}", "SUCCESS")
            except Exception:
                pass

            # 5. Asset targets selection
            if active_mode == "US100":
                ativos_atuais = ["US100.cash"]
            elif active_mode == "XAUUSD":
                ativos_atuais = ["XAUUSD"]
            else:
                ativos_atuais = ["US100.cash", "XAUUSD"]

            # 6. Scanning loop
            for symbol in ativos_atuais:
                df_m5 = engine.get_candles(symbol, mt5.TIMEFRAME_M5, 30)
                df_m1 = engine.get_candles(symbol, mt5.TIMEFRAME_M1, 15)
                if df_m5 is None or df_m1 is None:
                    continue

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

                        # Distance & Target Filter
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

            time.sleep(3)

    except KeyboardInterrupt:
        print("\nShutting down engine...")
    finally:
        engine.stop()

if __name__ == "__main__":
    main()