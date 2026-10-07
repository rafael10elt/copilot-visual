# risk_manager.py — Trailing Stop, Break-even, ATR, limites diários e Shadow Trading/backtest
import pandas as pd
import MetaTrader5 as mt5
import math

class RiskManager:
    def __init__(self, risk_per_trade_usd=100.0, max_daily_loss_usd=400.0):
        # Configurações globais da Mesa Proprietária
        self.risk_per_trade_usd = risk_per_trade_usd
        self.max_daily_loss_usd = max_daily_loss_usd
        
        # Estado do dia
        self.daily_lock_active = False

    def calculate_atr(self, df, period=14):
        """Calcula o Average True Range (Volatilidade) dos últimos N candles."""
        if len(df) < period + 1:
            return 1.0 # Retorna valor padrão se não houver velas suficientes
        
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift(1)).abs()
        low_close = (df['low'] - df['close'].shift(1)).abs()
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(window=period).mean().iloc[-1]
        
        return round(atr, 2)

    def check_daily_limit(self, current_equity, starting_balance):
        """Verifica se a conta atingiu a Perda Máxima Diária."""
        drawdown = starting_balance - current_equity
        if drawdown >= self.max_daily_loss_usd:
            self.daily_lock_active = True
            print(f"⛔ [HARD LOCK ATIVADO] Drawdown de ${drawdown:.2f} atingiu o limite de ${self.max_daily_loss_usd:.2f}!")
            return True
        return False

    def get_trade_parameters(self, profile, fvg, atr, symbol, direction):
        """
        Gera os preços exatos de SL e TP baseados no Perfil e na Volatilidade (ATR).
        """
        # Distância padrão do Spread/Ruído baseada no ativo
        buffer = 1.0 if "US100" in symbol or "NAS" in symbol else 0.3
        
        fvg_top = fvg['top']
        fvg_bottom = fvg['bottom']
        fvg_size = fvg['size']
        
        sl_price = 0.0
        tp_price = 0.0

        if direction == 'BUY':
            entry_price = fvg_top # Limit order na borda superior do FVG
            
            if profile == 'sniper':
                # SL colado na borda inferior do FVG + pequeno buffer. Alvo longo (1:4)
                sl_price = fvg_bottom - buffer
                risk = entry_price - sl_price
                tp_price = entry_price + (risk * 4.0)
                
            elif profile == 'tatico':
                # SL com respiro médio (FVG + Metade do ATR). Alvo médio (1:2.5)
                sl_price = fvg_bottom - (atr * 0.5)
                risk = entry_price - sl_price
                tp_price = entry_price + (risk * 2.5)
                
            elif profile == 'guardiao':
                # SL protegido pela volatilidade total (FVG + 1 ATR inteiro). Alvo curto (1:1.5)
                sl_price = fvg_bottom - atr
                risk = entry_price - sl_price
                tp_price = entry_price + (risk * 1.5)

        elif direction == 'SELL':
            entry_price = fvg_bottom # Limit order na borda inferior do FVG
            
            if profile == 'sniper':
                sl_price = fvg_top + buffer
                risk = sl_price - entry_price
                tp_price = entry_price - (risk * 4.0)
                
            elif profile == 'tatico':
                sl_price = fvg_top + (atr * 0.5)
                risk = sl_price - entry_price
                tp_price = entry_price - (risk * 2.5)
                
            elif profile == 'guardiao':
                sl_price = fvg_top + atr
                risk = sl_price - entry_price
                tp_price = entry_price - (risk * 1.5)

        return {
            "entry": round(entry_price, 2),
            "sl": round(sl_price, 2),
            "tp": round(tp_price, 2),
            "risk_points": round(risk, 2)
        }

    def calculate_lot_size(self, symbol, risk_points):
        """
        Calcula o lote ideal no MT5 para arriscar exatamente X dólares.
        Usa informações internas do ativo na corretora (Tick Value).
        """
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return 0.01 # Lote mínimo de segurança se falhar
            
        tick_size = symbol_info.trade_tick_size
        tick_value = symbol_info.trade_tick_value # Quanto vale 1 tick na moeda da conta
        
        if tick_size == 0 or tick_value == 0:
            return 0.01
            
        # Dinheiro arriscado = (Distância em Pontos / Tick Size) * Tick Value * Lotes
        # Isolando os Lotes: Lotes = Risco_USD / ((Risco_Pontos / Tick_Size) * Tick_Value)
        
        ticks_at_risk = risk_points / tick_size
        value_at_risk_per_lot = ticks_at_risk * tick_value
        
        lot_size = self.risk_per_trade_usd / value_at_risk_per_lot
        
        # Arredondar para o step da corretora (geralmente 0.01 ou 0.1)
        step = symbol_info.volume_step
        lot_size = math.floor(lot_size / step) * step
        
        # Garantir limites da corretora
        lot_size = max(lot_size, symbol_info.volume_min)
        lot_size = min(lot_size, symbol_info.volume_max)
        
        return round(lot_size, 2)


# =====================================================================
# TESTE RÁPIDO DO MÓDULO DE RISCO
# =====================================================================
if __name__ == "__main__":
    rm = RiskManager(risk_per_trade_usd=100.0) # Arriscando $100 por operação
    
    # Simulação de um FVG Bullish encontrado pelo mt5_core.py
    fake_fvg = {'type': 'BULLISH', 'top': 20110.0, 'bottom': 20100.0, 'size': 10.0}
    fake_atr = 15.0 # Volatilidade do momento
    ativo = "US100"
    
    print("\n[MESA PROPRIETÁRIA] Cálculo de Risco para Arriscar exatos $100.00")
    print(f"Cenário: Compra Limit em {fake_fvg['top']}, FVG Base em {fake_fvg['bottom']}, ATR: {fake_atr}")
    print("-" * 50)
    
    for perfil in ['sniper', 'tatico', 'guardiao']:
        params = rm.get_trade_parameters(perfil, fake_fvg, fake_atr, ativo, 'BUY')
        print(f"🤖 Perfil: {perfil.upper()}")
        print(f"  Entrada: {params['entry']}")
        print(f"  Stop Loss: {params['sl']} (Risco: {params['risk_points']} pts)")
        print(f"  Take Profit: {params['tp']}")
        # Aqui simulamos o cálculo de lote (como o MT5 não tá conectado no teste isolado, mostramos a fórmula)
        print("-" * 50)