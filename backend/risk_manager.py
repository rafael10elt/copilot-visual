# risk_manager.py — Gestão de Risco Especializada para Mesa Proprietária (Prop Firm Shield)
import MetaTrader5 as mt5
import pandas as pd
import math

class RiskManager:
    def __init__(self, risk_per_trade_usd=100.0, max_daily_loss_usd=400.0):
        self.risk_per_trade_usd = risk_per_trade_usd
        self.max_daily_loss_usd = max_daily_loss_usd
        
        # Monitoramento Institucional de Drawdown Diário (High-Water Mark)
        self.start_day_balance = None
        self.peak_day_equity = None
        self.daily_lock_active = False

    def update_account_state(self, current_balance, current_equity):
        """Atualiza os picos do dia para proteger trailing drawdown de mesa proprietária."""
        if self.start_day_balance is None or self.start_day_balance == 0:
            self.start_day_balance = current_balance
            self.peak_day_equity = current_equity

        if current_equity > (self.peak_day_equity or 0.0):
            self.peak_day_equity = current_equity

        # Drawdown em relação ao início do dia
        drawdown_from_start = self.start_day_balance - current_equity
        if drawdown_from_start >= self.max_daily_loss_usd:
            self.daily_lock_active = True
            return True, f"DRAWDOWN_LIMIT_REACHED: Perdendo ${drawdown_from_start:.2f} (Limite: ${self.max_daily_loss_usd:.2f})"
        
        return False, "OK"

    def calculate_atr(self, df, period=14):
        """Calcula a volatilidade ATR com segurança."""
        if df is None or len(df) < period + 1:
            return 1.0
        
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(window=period).mean().iloc[-1]
        
        return round(float(atr), 2)

    def get_trade_parameters(self, profile, fvg, atr, symbol, direction):
        """
        Calcula os parâmetros de entrada com teto dinâmico de risco e limites de corretora.
        """
        is_nasdaq = "US100" in symbol.upper() or "NAS" in symbol.upper() or "USTEC" in symbol.upper()
        buffer = 1.0 if is_nasdaq else 0.30
        max_allowed_risk = 25.0 if is_nasdaq else 3.50

        fvg_top = float(fvg['top'])
        fvg_bottom = float(fvg['bottom'])

        raw_risk = abs(fvg_top - fvg_bottom) + buffer
        capped_risk = min(raw_risk, max_allowed_risk)

        if direction == 'BUY':
            entry_price = fvg_top
            if profile == 'sniper':
                risk = capped_risk
                tp_price = entry_price + (risk * 4.0)
            elif profile == 'tatico':
                risk = min(capped_risk + (atr * 0.4), max_allowed_risk)
                tp_price = entry_price + (risk * 2.5)
            else: # guardiao
                risk = min(capped_risk + (atr * 0.8), max_allowed_risk)
                tp_price = entry_price + (risk * 1.5)
            sl_price = entry_price - risk

        else: # SELL
            entry_price = fvg_bottom
            if profile == 'sniper':
                risk = capped_risk
                tp_price = entry_price - (risk * 4.0)
            elif profile == 'tatico':
                risk = min(capped_risk + (atr * 0.4), max_allowed_risk)
                tp_price = entry_price - (risk * 2.5)
            else: # guardiao
                risk = min(capped_risk + (atr * 0.8), max_allowed_risk)
                tp_price = entry_price - (risk * 1.5)
            sl_price = entry_price + risk

        # Arredondamento conforme o ativo
        decimals = 2 if is_nasdaq else 2
        return {
            "entry": round(entry_price, decimals),
            "sl": round(sl_price, decimals),
            "tp": round(tp_price, decimals),
            "risk_points": round(risk, decimals)
        }

    def calculate_lot_size(self, symbol, risk_points):
        """
        Calcula o volume exato respeitando o Tick Value, Tick Size e Steps da Corretora.
        """
        info = mt5.symbol_info(symbol)
        if not info:
            return 0.01

        tick_size = info.trade_tick_size or 0.01
        tick_value = info.trade_tick_value or 1.0

        if risk_points <= 0 or tick_size <= 0 or tick_value <= 0:
            return info.volume_min

        # Valor financeiro do risco de 1 lote inteiro
        ticks_at_risk = risk_points / tick_size
        risk_per_full_lot = ticks_at_risk * tick_value

        if risk_per_full_lot <= 0:
            return info.volume_min

        raw_lot = self.risk_per_trade_usd / risk_per_full_lot

        # Ajuste ao passo da corretora (step)
        step = info.volume_step or 0.01
        lot_size = math.floor(raw_lot / step) * step

        # Garantir limites da conta
        lot_size = max(lot_size, info.volume_min)
        lot_size = min(lot_size, info.volume_max)

        return round(lot_size, 2)

    def calculate_safe_breakeven_sl(self, symbol, position_type, open_price, current_price):
        """
        Calcula o Stop Loss do Break-even respeitando rigorosamente o StopsLevel e Spread da corretora.
        Previne o erro 10016 (TRADE_RETCODE_INVALID_STOPS).
        """
        info = mt5.symbol_info(symbol)
        if not info:
            return None

        point = info.point
        stops_level = info.trade_stops_level * point
        spread = info.spread * point

        # Distância mínima necessária de segurança
        min_offset = max(stops_level, spread, 2 * point)

        if position_type == mt5.POSITION_TYPE_BUY:
            # Só move se o preço atual já estiver seguro acima do ponto de entrada
            if (current_price - open_price) <= (min_offset + spread):
                return None
            proposed_sl = open_price + min_offset
            # Não pode ficar acima do bid atual
            if proposed_sl >= info.bid - stops_level:
                return None
            return round(proposed_sl, info.digits)

        elif position_type == mt5.POSITION_TYPE_SELL:
            # Só move se o preço atual já estiver seguro abaixo do ponto de entrada
            if (open_price - current_price) <= (min_offset + spread):
                return None
            proposed_sl = open_price - min_offset
            # Não pode ficar abaixo do ask atual
            if proposed_sl <= info.ask + stops_level:
                return None
            return round(proposed_sl, info.digits)

        return None