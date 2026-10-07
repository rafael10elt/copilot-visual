# mt5_core.py — Motor de Conexão, Sessões, Detecção de FVG, Liquidity Sweeps e 50% CE
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

class MT5Engine:
    def __init__(self):
        self.connected = False
        self.symbol_cache = {}

    def start(self):
        print("[MT5] Conectando ao terminal MetaTrader 5...")
        if not mt5.initialize():
            print(f"❌ [ERRO] Falha ao inicializar MT5. Código: {mt5.last_error()}")
            return False
        
        self.connected = True
        account = mt5.account_info()
        acc_id = account.login if account else "Desconhecido"
        server = account.server if account else "Desconhecido"
        print(f"✅ [MT5] Conectado! Conta: {acc_id} | Servidor: {server} | Build: {mt5.version()[0]}")
        return True

    def stop(self):
        if self.connected:
            mt5.shutdown()
            self.connected = False
            print("[MT5] Conexão encerrada.")

    def resolve_symbol(self, category):
        if category in self.symbol_cache:
            return self.symbol_cache[category]

        if not self.connected:
            return None

        all_symbols = mt5.symbols_get()
        if not all_symbols:
            return None

        available_names = [s.name for s in all_symbols]

        if category.upper() == 'NASDAQ':
            targets = ["US100.cash", "US100", "NAS100", "NAS100.cash", "USTEC", "USTEC.cash", "NASUSD", "NQ"]
        elif category.upper() == 'GOLD':
            targets = ["XAUUSD", "GOLD", "XAUUSD.cash", "XAUUSD.pro", "XAUUSDm", "XAUUSD.ecn"]
        else:
            targets = [category]

        for target in targets:
            for symbol_name in available_names:
                if target.lower() == symbol_name.lower():
                    mt5.symbol_select(symbol_name, True)
                    self.symbol_cache[category] = symbol_name
                    return symbol_name

        for target in targets:
            for symbol_name in available_names:
                if target.lower() in symbol_name.lower():
                    mt5.symbol_select(symbol_name, True)
                    self.symbol_cache[category] = symbol_name
                    return symbol_name

        return None

    def get_candles(self, symbol, timeframe, num_candles):
        if not self.connected or not symbol:
            return None

        mt5.symbol_select(symbol, True)
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
        
        if rates is None or len(rates) == 0:
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df


class InstitutionalSessionFilter:
    @staticmethod
    def is_session_active(symbol, candle_time):
        hour = candle_time.hour
        is_nasdaq = "US100" in symbol.upper() or "NAS" in symbol.upper() or "USTEC" in symbol.upper()

        if is_nasdaq:
            return 15 <= hour <= 21
        else:
            return 9 <= hour <= 21


class LiquiditySweepDetector:
    """
    Verifica se o FVG se formou IMEDIATAMENTE após uma varredura de liquidez (Sweep).
    Alta probabilidade: captura de fundo anterior antes da compra ou topo antes da venda.
    """
    @staticmethod
    def check_sweep(df, fvg_idx, direction, lookback=8):
        if df is None or fvg_idx < lookback:
            return False, "Histórico insuficiente"

        window = df.iloc[max(0, fvg_idx - lookback) : fvg_idx]
        displacement_candle = df.iloc[fvg_idx]

        if direction == "BUY":
            # Procura se alguma vela recente varreu a mínima da janela e rejeitou com pavio
            prior_low = window['low'].min()
            swept = displacement_candle['low'] <= prior_low and displacement_candle['close'] > displacement_candle['open']
            return swept, "SSL_SWEEP" if swept else "NO_SWEEP"
        else:
            # Procura se varreu a máxima da janela e fechou caindo
            prior_high = window['high'].max()
            swept = displacement_candle['high'] >= prior_high and displacement_candle['close'] < displacement_candle['open']
            return swept, "BSL_SWEEP" if swept else "NO_SWEEP"


class VisionLiquidityAnalyzer:
    def __init__(self, resolution=(128, 128)):
        self.res = resolution

    def validate_liquidity_path(self, df, direction, entry_price, tp_price):
        if df is None or len(df) < 20:
            return True, "Candles insuficientes para matriz de visão"

        grid = np.zeros(self.res, dtype=np.float32)
        min_p = float(df['low'].min())
        max_p = float(df['high'].max())
        p_range = max_p - min_p if max_p != min_p else 1.0

        n_bars = min(len(df), self.res[0])
        sub_df = df.iloc[-n_bars:]

        for col_idx, (_, row) in enumerate(sub_df.iterrows()):
            y_high = int((1.0 - (row['high'] - min_p) / p_range) * (self.res[1] - 1))
            y_low = int((1.0 - (row['low'] - min_p) / p_range) * (self.res[1] - 1))
            y_open = int((1.0 - (row['open'] - min_p) / p_range) * (self.res[1] - 1))
            y_close = int((1.0 - (row['close'] - min_p) / p_range) * (self.res[1] - 1))

            y_min_w = min(y_high, y_low)
            y_max_w = max(y_high, y_low)
            grid[y_min_w : y_max_w + 1, col_idx] += 0.5

            y_top = min(y_open, y_close)
            y_bot = max(y_open, y_close)
            grid[y_top : y_bot + 1, col_idx] += 1.0

        if HAS_OPENCV:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            grid = cv2.dilate(grid, kernel, iterations=1)

        y_entry = int((1.0 - (entry_price - min_p) / p_range) * (self.res[1] - 1))
        y_tp = int((1.0 - (tp_price - min_p) / p_range) * (self.res[1] - 1))

        y_entry = max(0, min(self.res[1] - 1, y_entry))
        y_tp = max(0, min(self.res[1] - 1, y_tp))

        y_start, y_end = min(y_entry, y_tp), max(y_entry, y_tp)
        path_zone = grid[y_start:y_end, :]

        density = np.sum(path_zone >= 1.0) / (path_zone.size + 1e-5)

        if density > 0.45:
            return False, f"Parede de absorção detectada por visão (Densidade: {density:.1%})"

        return True, "Caminho livre até o alvo"


class MarketStructureDetector:
    @staticmethod
    def get_m15_structure(df):
        if df is None or len(df) < 15:
            return "NEUTRAL", 0.0, 0.0

        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values

        swing_highs = []
        swing_lows = []

        for i in range(2, len(df) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                swing_highs.append(highs[i])
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                swing_lows.append(lows[i])

        last_close = closes[-1]
        last_high = swing_highs[-1] if swing_highs else highs.max()
        last_low = swing_lows[-1] if swing_lows else lows.min()

        if last_close > last_high:
            return "BULLISH_BOS", last_high, last_low
        elif last_close < last_low:
            return "BEARISH_BOS", last_high, last_low
        elif len(swing_highs) >= 2 and swing_highs[-1] > swing_highs[-2] and swing_lows and swing_lows[-1] > swing_lows[-2]:
            return "UPTREND", last_high, last_low
        elif len(swing_highs) >= 2 and swing_highs[-1] < swing_highs[-2] and swing_lows and swing_lows[-1] < swing_lows[-2]:
            return "DOWNTREND", last_high, last_low

        return "NEUTRAL", last_high, last_low


class FVGDetector:
    def __init__(self, min_gap_nasdaq=3.0, min_gap_xau=0.4):
        self.min_gap_nasdaq = min_gap_nasdaq
        self.min_gap_xau = min_gap_xau

    def find_unmitigated_fvgs(self, df, symbol):
        if df is None or len(df) < 5:
            return []

        fvgs = []
        is_nasdaq = "US100" in symbol.upper() or "NAS" in symbol.upper() or "USTEC" in symbol.upper()
        min_gap = self.min_gap_nasdaq if is_nasdaq else self.min_gap_xau

        for i in range(len(df) - 3):
            candle1 = df.iloc[i]
            candle2 = df.iloc[i+1]
            candle3 = df.iloc[i+2]
            
            fvg_type = None
            fvg_top = 0.0
            fvg_bottom = 0.0
            gap_size = 0.0

            if candle3['low'] > candle1['high']:
                gap_size = candle3['low'] - candle1['high']
                if gap_size >= min_gap:
                    fvg_type = 'BULLISH'
                    fvg_top = candle3['low']
                    fvg_bottom = candle1['high']

            elif candle3['high'] < candle1['low']:
                gap_size = candle1['low'] - candle3['high']
                if gap_size >= min_gap:
                    fvg_type = 'BEARISH'
                    fvg_top = candle1['low']
                    fvg_bottom = candle3['high']

            if fvg_type:
                mitigated = False
                subsequent_candles = df.iloc[i+3:]
                
                for _, sub in subsequent_candles.iterrows():
                    if fvg_type == 'BULLISH' and sub['low'] <= fvg_top:
                        mitigated = True
                        break
                    elif fvg_type == 'BEARISH' and sub['high'] >= fvg_bottom:
                        mitigated = True
                        break
                
                if not mitigated:
                    # Consequent Encroachment (ponto central exato de 50%)
                    ce_50 = round(float((fvg_top + fvg_bottom) / 2.0), 2)

                    # Verifica varredura prévia no momento do deslocamento
                    has_sweep, sweep_type = LiquiditySweepDetector.check_sweep(
                        df, fvg_idx=i+1, direction="BUY" if fvg_type == 'BULLISH' else "SELL"
                    )

                    fvgs.append({
                        'type': fvg_type,
                        'top': round(float(fvg_top), 2),
                        'bottom': round(float(fvg_bottom), 2),
                        'ce_50': ce_50,
                        'has_sweep': has_sweep,
                        'sweep_type': sweep_type,
                        'size': round(float(gap_size), 2),
                        'time_formed': candle2['time'].strftime('%H:%M'),
                        'raw_time': candle2['time'],
                        'age_candles': len(df) - (i+2)
                    })

        return fvgs