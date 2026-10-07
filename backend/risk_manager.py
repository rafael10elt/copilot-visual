# risk_manager.py — Gestão de Risco com Reset no Servidor, Trailing Stop M1 e Escudo FTMO
import MetaTrader5 as mt5
import pandas as pd
import math
from datetime import datetime

class RiskManager:
    def __init__(self, risk_per_trade_usd=100.0, max_daily_loss_usd=400.0):
        self.risk_per_trade_usd = risk_per_trade_usd
        self.max_daily_loss_usd = max_daily_loss_usd
        
        self.start_day_balance = None
        self.peak_day_equity = None
        self.daily_lock_active = False
        self.current_broker_day_str = None

    def update_account_state(self, current_balance, current_equity, broker_server_time=None):
        now = broker_server_time or datetime.now()
        today_str = now.strftime('%Y-%m-%d')

        if self.current_broker_day_str != today_str:
            self.current_broker_day_str = today_str
            self.start_day_balance = max(current_balance, current_equity)
            self.peak_day_equity = current_equity
            self.daily_lock_active = False
            print(f"🔄 [PROP FIRM SHIELD] Novo dia no servidor ({today_str}). Benchmark inicial: ${self.start_day_balance:.2f}")

        if current_equity > (self.peak_day_equity or 0.0):
            self.peak_day_equity = current_equity

        drawdown_from_start = self.start_day_balance - current_equity
        soft_stop_limit = self.max_daily_loss_usd * 0.85

        if drawdown_from_start >= soft_stop_limit:
            self.daily_lock_active = True
            return True, f"DRAWDOWN_LIMIT_GUARD: Perdendo ${drawdown_from_start:.2f} (Margem de segurança atingida: ${soft_stop_limit:.2f} de ${self.max_daily_loss_usd:.2f})"
        
        return False, "OK"

    def calculate_atr(self, df, period=14):
        if df is None or len(df) < period + 1:
            return 1.0
        
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(window=period).mean().iloc[-1]
        
        return round(float(atr), 2)

    def get_trade_parameters(self, profile, fvg, atr, symbol, direction, use_ce_50=True):
        is_nasdaq = any(x in symbol.upper() for x in ["US100", "NAS", "USTEC", "NQ"])
        buffer = 1.0 if is_nasdaq else 0.30
        max_allowed_risk = 25.0 if is_nasdaq else 3.50

        fvg_top = float(fvg['top'])
        fvg_bottom = float(fvg['bottom'])
        ce_price = float(fvg.get('ce_50', (fvg_top + fvg_bottom) / 2.0))

        if direction == 'BUY':
            entry_price = ce_price if use_ce_50 else fvg_top
            raw_risk = (entry_price - fvg_bottom) + buffer
            risk = min(max(raw_risk, 1.5 if is_nasdaq else 0.4), max_allowed_risk)

            if profile == 'sniper': tp_price = entry_price + (risk * 4.0)
            elif profile == 'tatico': tp_price = entry_price + (risk * 2.5)
            else: tp_price = entry_price + (risk * 1.5)
            sl_price = entry_price - risk

        else: # SELL
            entry_price = ce_price if use_ce_50 else fvg_bottom
            raw_risk = (fvg_top - entry_price) + buffer
            risk = min(max(raw_risk, 1.5 if is_nasdaq else 0.4), max_allowed_risk)

            if profile == 'sniper': tp_price = entry_price - (risk * 4.0)
            elif profile == 'tatico': tp_price = entry_price - (risk * 2.5)
            else: tp_price = entry_price - (risk * 1.5)
            sl_price = entry_price + risk

        return {
            "entry": round(entry_price, 2),
            "sl": round(sl_price, 2),
            "tp": round(tp_price, 2),
            "risk_points": round(risk, 2)
        }

    def calculate_lot_size(self, symbol, risk_points):
        info = mt5.symbol_info(symbol)
        if not info: return 0.01

        tick_size = info.trade_tick_size or 0.01
        tick_value = info.trade_tick_value or 1.0

        if risk_points <= 0 or tick_size <= 0 or tick_value <= 0:
            return info.volume_min

        ticks_at_risk = risk_points / tick_size
        risk_per_full_lot = ticks_at_risk * tick_value

        if risk_per_full_lot <= 0:
            return info.volume_min

        raw_lot = self.risk_per_trade_usd / risk_per_full_lot
        step = info.volume_step or 0.01
        lot_size = math.floor(raw_lot / step) * step

        lot_size = max(lot_size, info.volume_min)
        lot_size = min(lot_size, info.volume_max)

        return round(lot_size, 2)

    def calculate_safe_breakeven_sl(self, symbol, position_type, open_price, current_price):
        info = mt5.symbol_info(symbol)
        if not info: return None

        point = info.point
        stops_level = info.trade_stops_level * point
        spread = info.spread * point
        min_offset = max(stops_level, spread, 2 * point)

        if position_type == mt5.POSITION_TYPE_BUY:
            if (current_price - open_price) <= (min_offset + spread):
                return None
            proposed_sl = open_price + min_offset
            if proposed_sl >= info.bid - stops_level:
                return None
            return round(proposed_sl, info.digits)

        elif position_type == mt5.POSITION_TYPE_SELL:
            if (open_price - current_price) <= (min_offset + spread):
                return None
            proposed_sl = open_price - min_offset
            if proposed_sl <= info.ask + stops_level:
                return None
            return round(proposed_sl, info.digits)

        return None

    def calculate_safe_trailing_sl(self, symbol, position_type, open_price, current_price, current_sl, last_m1_low, last_m1_high):
        """
        Rastreia vela a vela após o trade avançar no lucro, garantindo proteção sem violar stops_level.
        """
        info = mt5.symbol_info(symbol)
        if not info: return None

        point = info.point
        stops_level = info.trade_stops_level * point
        spread = info.spread * point
        buffer = 3 * point

        if position_type == mt5.POSITION_TYPE_BUY:
            proposed_sl = last_m1_low - buffer
            # Só move para cima e se já estiver acima do breakeven
            if proposed_sl <= current_sl or proposed_sl <= open_price:
                return None
            if proposed_sl >= (info.bid - stops_level):
                return None
            return round(proposed_sl, info.digits)

        elif position_type == mt5.POSITION_TYPE_SELL:
            proposed_sl = last_m1_high + buffer
            # Só move para baixo e se já estiver abaixo do breakeven
            if current_sl > 0 and proposed_sl >= current_sl:
                return None
            if proposed_sl >= open_price:
                return None
            if proposed_sl <= (info.ask + stops_level):
                return None
            return round(proposed_sl, info.digits)

        return None