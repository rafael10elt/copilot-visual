# mt5_core.py — Conexão, Killzones Alinhadas a UTC, Filtro de Spread e Visão Computacional
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False


class MT5Engine:
    def __init__(self):
        self.connected = False
        self.symbol_cache = {}
        self.broker_utc_offset_hours = 2  # Padrão EET (GMT+2 / GMT+3)

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
        
        self._calibrate_broker_utc_offset()
        return True

    def stop(self):
        if self.connected:
            mt5.shutdown()
            self.connected = False
            print("[MT5] Conexão encerrada.")

    def _calibrate_broker_utc_offset(self):
        """Calcula a diferença entre o relógio da corretora e o UTC real."""
        tick = mt5.symbol_info_tick("EURUSD") or mt5.symbol_info_tick("XAUUSD")
        if tick and tick.time > 0:
            now_utc = datetime.now(timezone.utc).timestamp()
            diff_hours = round((tick.time - now_utc) / 3600.0)
            self.broker_utc_offset_hours = diff_hours
            print(f"🌐 [TIME SYNC] Offset do servidor da corretora detectado: UTC{'+' if diff_hours >= 0 else ''}{diff_hours}")
        else:
            print(f"⚠️ [TIME SYNC] Usando offset padrão da corretora: UTC+{self.broker_utc_offset_hours}")

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

    def get_broker_current_time(self, symbol="XAUUSD"):
        tick = mt5.symbol_info_tick(symbol)
        if tick and tick.time > 0:
            return datetime.fromtimestamp(tick.time)
        # Fallback usando o offset calibrado
        return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=self.broker_utc_offset_hours)

    def is_spread_acceptable(self, symbol):
        """Evita entradas quando o spread dilata por baixa liquidez ou notícias."""
        info = mt5.symbol_info(symbol)
        if not info:
            return False, "Símbolo inacessível"

        point = info.point
        spread_pts = info.spread * point
        is_nasdaq = any(x in symbol.upper() for x in ["US100", "NAS", "USTEC", "NQ"])

        # Teto tolerado de spread (pontos de cotação)
        max_allowed = 3.5 if is_nasdaq else 0.45
        if spread_pts > max_allowed:
            return False, f"Spread excessivo ({spread_pts:.2f} pts > teto de {max_allowed} pts)"

        return True, "Spread OK"


class InstitutionalSessionFilter:
    @staticmethod
    def is_session_active(symbol, broker_candle_time, broker_utc_offset=2):
        """
        Converte o horário do candle do servidor para UTC real e valida
        as Killzones oficiais de Londres e Nova York.
        """
        # Converter server time para UTC real
        candle_utc = broker_candle_time - timedelta(hours=broker_utc_offset)
        utc_hour = candle_utc.hour
        utc_minute = candle_utc.minute

        # Bloqueio estrito da virada/rollover (spreads extremos entre 21h e 23h UTC)
        if utc_hour >= 21 or utc_hour < 2:
            return False

        is_nasdaq = any(x in symbol.upper() for x in ["US100", "NAS", "USTEC", "NQ"])

        if is_nasdaq:
            # NY Cash Open: 13:30 às 17:00 UTC (maior respeito aos FVGs do índice)
            if (utc_hour == 13 and utc_minute >= 30) or (14 <= utc_hour < 17):
                return True
            return False
        else:
            # XAUUSD: Londres (07:00 às 10:30 UTC) e Nova York (12:30 às 16:30 UTC)
            london = (7 <= utc_hour < 10) or (utc_hour == 10 and utc_minute <= 30)
            ny = (12 <= utc_hour < 16) or (utc_hour == 16 and utc_minute <= 30)
            return london or ny


class LiquiditySweepDetector:
    @staticmethod
    def check_sweep(df, fvg_idx, direction, lookback=8):
        if df is None or fvg_idx < lookback:
            return False, "Histórico insuficiente"

        window = df.iloc[max(0, fvg_idx - lookback) : fvg_idx]
        displacement_candle = df.iloc[fvg_idx]

        if direction == "BUY":
            prior_low = window['low'].min()
            swept = displacement_candle['low'] <= prior_low
            return swept, "SSL_SWEEP" if swept else "NO_SWEEP"
        else:
            prior_high = window['high'].max()
            swept = displacement_candle['high'] >= prior_high
            return swept, "BSL_SWEEP" if swept else "NO_SWEEP"


class VisionLiquidityAnalyzer:
    def __init__(self, resolution=(128, 128)):
        self.res = resolution

    def validate_liquidity_path(self, df, direction, entry_price, tp_price):
        """
        Analisa a rota do preço até o Take Profit.
        Se a região entre a entrada e o TP já foi amplamente congestionada,
        a ordem é rejeitada para evitar reversões em falso breakout.
        """
        if df is None or len(df) < 20:
            return True, "Candles insuficientes"

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

        y_entry = max(0, min(self.res[1] - 1, int((1.0 - (entry_price - min_p) / p_range) * (self.res[1] - 1))))
        y_tp = max(0, min(self.res[1] - 1, int((1.0 - (tp_price - min_p) / p_range) * (self.res[1] - 1))))

        y_start, y_end = min(y_entry, y_tp), max(y_entry, y_tp)
        path_zone = grid[y_start:y_end, :]
        density = np.sum(path_zone >= 1.0) / (path_zone.size + 1e-5)

        if density > 0.55:
            return False, f"Absorção densa ({density:.1%})"

        return True, "Livre"


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
    def __init__(self, min_gap_nasdaq=2.5, min_gap_xau=0.30):
        self.min_gap_nasdaq = min_gap_nasdaq
        self.min_gap_xau = min_gap_xau

    def find_all_historical_fvgs(self, df, symbol):
        if df is None or len(df) < 5:
            return []

        fvgs = []
        is_nasdaq = any(x in symbol.upper() for x in ["US100", "NAS", "USTEC", "NQ"])
        min_gap = self.min_gap_nasdaq if is_nasdaq else self.min_gap_xau

        for i in range(len(df) - 3):
            c1 = df.iloc[i]
            c2 = df.iloc[i+1]
            c3 = df.iloc[i+2]

            fvg_type = None
            fvg_top = 0.0
            fvg_bottom = 0.0
            gap_size = 0.0

            if c3['low'] > c1['high']:
                gap_size = c3['low'] - c1['high']
                if gap_size >= min_gap:
                    fvg_type = 'BULLISH'
                    fvg_top = c3['low']
                    fvg_bottom = c1['high']

            elif c3['high'] < c1['low']:
                gap_size = c1['low'] - c3['high']
                if gap_size >= min_gap:
                    fvg_type = 'BEARISH'
                    fvg_top = c1['low']
                    fvg_bottom = c3['high']

            if fvg_type:
                ce_50 = round(float((fvg_top + fvg_bottom) / 2.0), 2)
                has_sweep, sweep_type = LiquiditySweepDetector.check_sweep(
                    df, fvg_idx=i+1, direction="BUY" if fvg_type == 'BULLISH' else "SELL"
                )

                fvgs.append({
                    'index': i + 2,
                    'type': fvg_type,
                    'top': round(float(fvg_top), 2),
                    'bottom': round(float(fvg_bottom), 2),
                    'ce_50': ce_50,
                    'has_sweep': has_sweep,
                    'sweep_type': sweep_type,
                    'size': round(float(gap_size), 2),
                    'time_formed': c3['time'].strftime('%H:%M'),
                    'raw_time': c3['time']
                })

        return fvgs

    def find_unmitigated_fvgs(self, df, symbol):
        all_fvgs = self.find_all_historical_fvgs(df, symbol)
        unmitigated = []

        for f in all_fvgs:
            idx = f['index']
            subsequent = df.iloc[idx+1:]
            mitigated = False

            for _, sub in subsequent.iterrows():
                if f['type'] == 'BULLISH' and sub['low'] <= f['top']:
                    mitigated = True
                    break
                elif f['type'] == 'BEARISH' and sub['high'] >= f['bottom']:
                    mitigated = True
                    break

            if not mitigated:
                f['age_candles'] = len(df) - idx
                unmitigated.append(f)

        return unmitigated