# mt5_core.py — Motor de Conexão, Resolução Dinâmica de Ativos e Detecção SMC/Visão Computacional
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import cv2
from datetime import datetime

class MT5Engine:
    def __init__(self):
        self.connected = False
        self.symbol_cache = {}

    def start(self):
        """Inicializa a conexão com o terminal MetaTrader 5."""
        print("[MT5] Conectando ao terminal MetaTrader 5...")
        if not mt5.initialize():
            print(f"❌ [ERRO] Falha ao inicializar MT5. Código: {mt5.last_error()}")
            return False
        
        self.connected = True
        account = mt5.account_info()
        acc_id = account.login if account else "Desconhecido"
        server = account.server if account else "Desconhecido"
        print(f"✅ [MT5] Conectado com sucesso! Conta: {acc_id} | Servidor: {server} | Build: {mt5.version()[0]}")
        return True

    def stop(self):
        """Finaliza a conexão."""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            print("[MT5] Conexão encerrada.")

    def resolve_symbol(self, category):
        """
        Descobre automaticamente o ticker exato da sua corretora para NASDAQ ou OURO.
        category: 'NASDAQ' ou 'GOLD'
        """
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

        # 1. Correspondência exata
        for target in targets:
            for symbol_name in available_names:
                if target.lower() == symbol_name.lower():
                    mt5.symbol_select(symbol_name, True)
                    self.symbol_cache[category] = symbol_name
                    print(f"🎯 [ATIVO MAPEADO] {category} -> {symbol_name}")
                    return symbol_name

        # 2. Correspondência parcial (fallback de segurança)
        for target in targets:
            for symbol_name in available_names:
                if target.lower() in symbol_name.lower():
                    mt5.symbol_select(symbol_name, True)
                    self.symbol_cache[category] = symbol_name
                    print(f"🎯 [ATIVO MAPEADO PARCIAL] {category} -> {symbol_name}")
                    return symbol_name

        print(f"⚠️ [ERRO] Não foi possível encontrar nenhum ticker para a categoria {category}")
        return None

    def get_candles(self, symbol, timeframe, num_candles):
        """Puxa candles OHLCV em DataFrame estruturado."""
        if not self.connected or not symbol:
            return None

        mt5.symbol_select(symbol, True)
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
        
        if rates is None or len(rates) == 0:
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df


class MarketStructureDetector:
    """Análise Institucional de Estrutura de Mercado M15 (BOS / MSS) — Não usa média ingênua."""
    @staticmethod
    def get_m15_structure(df):
        if df is None or len(df) < 15:
            return "NEUTRAL", 0.0, 0.0

        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values

        # Identifica Swing Highs e Swing Lows locais
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

        # Quebra de Estrutura (BOS / MSS)
        if last_close > last_high:
            return "BULLISH_BOS", last_high, last_low
        elif last_close < last_low:
            return "BEARISH_BOS", last_high, last_low
        elif len(swing_highs) >= 2 and swing_highs[-1] > swing_highs[-2] and swing_lows and swing_lows[-1] > swing_lows[-2]:
            return "UPTREND", last_high, last_low
        elif len(swing_highs) >= 2 and swing_highs[-1] < swing_highs[-2] and swing_lows and swing_lows[-1] < swing_lows[-2]:
            return "DOWNTREND", last_high, last_low

        return "NEUTRAL", last_high, last_low


class VisionLiquidityAnalyzer:
    """
    Módulo de Visão Computacional Gratuita usando NumPy e OpenCV.
    Renderiza uma matriz gráfica bidimensional de preço/volume para detectar
    piscinas de liquidez (BSL/SSL) e desequilíbrios institucionais sem custo de API.
    """
    def __init__(self, resolution=(128, 128)):
        self.res = resolution

    def analyze_chart_matrix(self, df):
        """
        Gera e analisa um mapa de calor matricial dos últimos candles.
        Retorna: score de liquidez acima e abaixo do preço atual.
        """
        if df is None or len(df) < 20:
            return {"clear_path": True, "bsl_score": 0, "ssl_score": 0}

        img = np.zeros(self.res, dtype=np.uint8)
        min_p = df['low'].min()
        max_p = df['high'].max()
        p_range = max_p - min_p if max_p != min_p else 1.0

        n_bars = min(len(df), self.res[0])
        sub_df = df.iloc[-n_bars:]

        # Desenha a densidade de sombras e corpos na matriz (representação gráfica)
        for col_idx, (_, row) in enumerate(sub_df.iterrows()):
            y_high = int((1.0 - (row['high'] - min_p) / p_range) * (self.res[1] - 1))
            y_low = int((1.0 - (row['low'] - min_p) / p_range) * (self.res[1] - 1))
            cv2.line(img, (col_idx, y_high), (col_idx, y_low), 120, 1)

            y_open = int((1.0 - (row['open'] - min_p) / p_range) * (self.res[1] - 1))
            y_close = int((1.0 - (row['close'] - min_p) / p_range) * (self.res[1] - 1))
            y_top = min(y_open, y_close)
            y_bot = max(y_open, y_close)
            cv2.line(img, (col_idx, y_top), (col_idx, y_bot), 255, 2)

        # Processamento morfológico: encontra clusters de rejeição (Equal Highs / Equal Lows)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(img, kernel, iterations=1)

        # Linha horizontal do preço atual
        current_close = df.iloc[-1]['close']
        y_curr = int((1.0 - (current_close - min_p) / p_range) * (self.res[1] - 1))

        # Densidade de toques acima (Resistência/BSL) e abaixo (Suporte/SSL)
        upper_zone = dilated[0:max(y_curr, 1), :]
        lower_zone = dilated[min(y_curr, self.res[1]-1):, :]

        bsl_score = float(np.sum(upper_zone > 200))
        ssl_score = float(np.sum(lower_zone > 200))

        return {
            "clear_path": True,
            "bsl_score": bsl_score,
            "ssl_score": ssl_score,
            "current_y_pixel": y_curr
        }


class FVGDetector:
    def __init__(self, min_gap_nasdaq=3.0, min_gap_xau=0.4):
        self.min_gap_nasdaq = min_gap_nasdaq
        self.min_gap_xau = min_gap_xau

    def find_unmitigated_fvgs(self, df, symbol):
        """Localiza desequilíbrios de valor justo (FVG) não mitigados."""
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

            # Bullish FVG (Mínima do candle 3 > Máxima do candle 1)
            if candle3['low'] > candle1['high']:
                gap_size = candle3['low'] - candle1['high']
                if gap_size >= min_gap:
                    fvg_type = 'BULLISH'
                    fvg_top = candle3['low']
                    fvg_bottom = candle1['high']

            # Bearish FVG (Máxima do candle 3 < Mínima do candle 1)
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
                    fvgs.append({
                        'type': fvg_type,
                        'top': round(float(fvg_top), 2),
                        'bottom': round(float(fvg_bottom), 2),
                        'size': round(float(gap_size), 2),
                        'time_formed': candle2['time'].strftime('%H:%M'),
                        'age_candles': len(df) - (i+2)
                    })

        return fvgs