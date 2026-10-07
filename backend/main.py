import time
import MetaTrader5 as mt5
from mt5_core import MT5Engine, FVGDetector
from risk_manager import RiskManager
from ai_groq import LumiGroqAgent
from supabase_client import SupabaseSync

# Ativos Monitorados
ATIVOS_MONITORADOS = ["US100.cash", "XAUUSD"]

def send_limit_order(symbol, action, entry_price, sl, tp, lot_size):
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
        "magic": 777999,
        "comment": "LUMI FVG AI",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }
    result = mt5.order_send(request)
    return result.retcode == mt5.TRADE_RETCODE_DONE

def get_m15_trend(engine, symbol):
    df_m15 = engine.get_candles(symbol, mt5.TIMEFRAME_M15, 20)
    if df_m15 is None: return "NEUTRAL"
    current_price = df_m15.iloc[-1]['close']
    past_price = df_m15.iloc[0]['close']
    return "UPTREND" if current_price > past_price else "DOWNTREND"

def main():
    print("=======================================")
    print("🚀 LUMI COPILOT HFT - ONLINE")
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

    sync.add_log(None, "Copiloto inicializado no notebook", "INFO")

    try:
        while True:
            # 1. Sincroniza configurações remotas do PWA (celular) a cada 4 segundos
            agora = time.time()
            if agora - last_hb >= 4.0:
                last_hb = agora
                sync.send_heartbeat(current_profile)
                remote = sync.check_remote_settings()
                if remote and remote.get("profile") != current_profile:
                    current_profile = remote.get("profile")
                    sync.add_log(None, f"Perfil alterado via celular para: {current_profile.upper()}", "WARN")

            # 2. Varredura nos ativos
            for symbol in ATIVOS_MONITORADOS:
                df_m5 = engine.get_candles(symbol, mt5.TIMEFRAME_M5, 30)
                df_m1 = engine.get_candles(symbol, mt5.TIMEFRAME_M1, 15)
                if df_m5 is None or df_m1 is None: continue

                fvgs = fvg_detector.find_unmitigated_fvgs(df_m5, symbol)
                atr_m1 = risk_manager.calculate_atr(df_m1)
                m15_trend = get_m15_trend(engine, symbol)

                for fvg in fvgs:
                    fvg_id = f"{symbol}_{fvg['type']}_{fvg['time_formed']}"
                    if fvg_id not in processed_fvgs:
                        sync.add_log(symbol, f"FVG {fvg['type']} detectado em {fvg['bottom']}. Consultando IA...", "INFO")
                        
                        base_price = fvg['top'] if fvg['type'] == 'BULLISH' else fvg['bottom']
                        ai = ia_agent.validate_fvg_trade(symbol, fvg['type'], base_price, m15_trend, atr_m1, current_profile)
                        
                        if ai.get("autorizado", False):
                            direction = "BUY" if ai["acao"] == "BUY_LIMIT" else "SELL"
                            params = risk_manager.get_trade_parameters(current_profile, fvg, atr_m1, symbol, direction)
                            lot = risk_manager.calculate_lot_size(symbol, params["risk_points"])
                            
                            sucesso = send_limit_order(symbol, ai["acao"], params["entry"], params["sl"], params["tp"], lot)
                            if sucesso:
                                sync.add_log(symbol, f"🎯 ORDEM ARMADA: {ai['acao']} {lot} lotes em {params['entry']}", "SUCCESS")
                            else:
                                sync.add_log(symbol, f"❌ Erro ao enviar ordem no MT5", "DANGER")
                        else:
                            sync.add_log(symbol, f"IA rejeitou: {ai['motivo']}", "WARN")

                        processed_fvgs.append(fvg_id)

            time.sleep(4)

    except KeyboardInterrupt:
        print("\nEncerrando...")
    finally:
        engine.stop()

if __name__ == "__main__":
    main()