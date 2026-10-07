import time
import MetaTrader5 as mt5
from mt5_core import MT5Engine, FVGDetector
from risk_manager import RiskManager
from ai_groq import LumiGroqAgent
from supabase_client import SupabaseSync

def get_best_filling_mode(symbol):
    """Detecta se a FTMO aceita FOK, IOC ou RETURN para o ativo"""
    info = mt5.symbol_info(symbol)
    if not info: return mt5.ORDER_FILLING_IOC
    modes = info.filling_mode
    if modes & mt5.ORDER_FILLING_IOC: return mt5.ORDER_FILLING_IOC
    if modes & mt5.ORDER_FILLING_FOK: return mt5.ORDER_FILLING_FOK
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
        "magic": 777999,
        "comment": "LUMI FVG AI",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Erro MT5 em {symbol}: Retcode {result.retcode} ({result.comment})")
        return False
    return True

def get_m15_trend(engine, symbol):
    df_m15 = engine.get_candles(symbol, mt5.TIMEFRAME_M15, 20)
    if df_m15 is None: return "NEUTRAL"
    current_price = df_m15.iloc[-1]['close']
    past_price = df_m15.iloc[0]['close']
    return "UPTREND" if current_price > past_price else "DOWNTREND"

def is_fvg_close_enough(current_price, entry_price, tp_price, action, symbol):
    """FILTRO DE DISTÂNCIA: Não arma se o preço já fugiu ou já bateu o TP"""
    distancia = abs(current_price - entry_price)
    
    # Distância máxima aceitável para armar a ordem (em pontos)
    max_dist = 25.0 if "US100" in symbol else 3.5 # 25 pts na Nasdaq, 3.5 dólares no Ouro
    
    if distancia > max_dist:
        return False, f"Muito distante do preço atual ({distancia:.2f} pts de gap)"
        
    # Se o preço já rompeu além do Take Profit, a oportunidade já passou
    if action == "SELL_LIMIT" and current_price <= tp_price:
        return False, "Movimento já aconteceu (preço abaixo do TP)"
    if action == "BUY_LIMIT" and current_price >= tp_price:
        return False, "Movimento já aconteceu (preço acima do TP)"
        
    return True, "Distância ideal"

def main():
    print("=======================================")
    print("🚀 LUMI COPILOT HFT - PRO (FTMO EDITION)")
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

    sync.add_log(None, "Copiloto conectado ao MT5", "INFO")

    try:
        while True:
            # 1. Puxa dados da conta FTMO em tempo real
            acc = mt5.account_info()
            if acc:
                balance = acc.balance
                equity = acc.equity
                pnl_today = equity - balance
                login = str(acc.login)
                server = acc.server
            else:
                balance, equity, pnl_today, login, server = 0, 0, 0, "--", "--"

            # 2. Sincroniza configurações remotas do Celular a cada 3s
            agora = time.time()
            if agora - last_hb >= 3.0:
                last_hb = agora
                sync.send_heartbeat(current_profile, pnl_today, login, balance, equity, server)
                
                remote = sync.check_remote_settings()
                if remote:
                    if remote.get("profile") and remote.get("profile") != current_profile:
                        current_profile = remote.get("profile")
                        sync.add_log(None, f"Perfil alterado para: {current_profile.upper()}", "WARN")
                    
                    if remote.get("risk_per_trade"):
                        risk_manager.risk_per_trade_usd = float(remote.get("risk_per_trade"))
                    if remote.get("max_daily_loss"):
                        risk_manager.max_daily_loss_usd = float(remote.get("max_daily_loss"))
                    if remote.get("active_symbol_mode"):
                        active_mode = remote.get("active_symbol_mode")

            # 3. Define quais ativos operar conforme seleção do celular
            if active_mode == "US100":
                ativos_atuais = ["US100.cash"]
            elif active_mode == "XAUUSD":
                ativos_atuais = ["XAUUSD"]
            else:
                ativos_atuais = ["US100.cash", "XAUUSD"]

            # 4. Varredura nos ativos
            for symbol in ativos_atuais:
                df_m5 = engine.get_candles(symbol, mt5.TIMEFRAME_M5, 30)
                df_m1 = engine.get_candles(symbol, mt5.TIMEFRAME_M1, 15)
                if df_m5 is None or df_m1 is None: continue

                preco_atual = df_m1.iloc[-1]['close']
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
                        
                        # FILTRO: Verifica se não está longe demais
                        valido, motivo_dist = is_fvg_close_enough(preco_atual, params["entry"], params["tp"], action_candidate, symbol)
                        if not valido:
                            processed_fvgs.append(fvg_id)
                            sync.add_log(symbol, f"Ignorado FVG {fvg['type']}: {motivo_dist}", "WARN")
                            continue

                        sync.add_log(symbol, f"FVG {fvg['type']} próximo ({params['entry']}). Consultando IA...", "INFO")
                        ai = ia_agent.validate_fvg_trade(symbol, fvg['type'], base_price, m15_trend, atr_m1, current_profile)
                        
                        if ai.get("autorizado", False):
                            lot = risk_manager.calculate_lot_size(symbol, params["risk_points"])
                            sucesso = send_limit_order(symbol, ai["acao"], params["entry"], params["sl"], params["tp"], lot)
                            if sucesso:
                                sync.add_log(symbol, f"🎯 ORDEM ARMADA: {ai['acao']} {lot} lotes em {params['entry']}", "SUCCESS")
                            else:
                                sync.add_log(symbol, f"❌ Erro ao enviar ordem no MT5", "DANGER")
                        else:
                            sync.add_log(symbol, f"IA rejeitou: {ai['motivo']}", "WARN")

                        processed_fvgs.append(fvg_id)

            time.sleep(3)

    except KeyboardInterrupt:
        print("\nEncerrando...")
    finally:
        engine.stop()

if __name__ == "__main__":
    main()