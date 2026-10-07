import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import time

class MT5Engine:
    def __init__(self):
        self.connected = False

    def start(self):
        """Inicializa a conexão com o terminal MetaTrader 5 aberto no background."""
        print("[MT5] Iniciando conexão com MetaTrader 5...")
        if not mt5.initialize():
            print(f"[ERRO] Falha ao inicializar MT5. Erro: {mt5.last_error()}")
            return False
        
        self.connected = True
        print(f"[MT5] Conectado com sucesso! Terminal versão: {mt5.version()}")
        return True

    def stop(self):
        """Encerra a conexão."""
        if self.connected:
            mt5.shutdown()
            print("[MT5] Conexão encerrada.")

    def get_candles(self, symbol, timeframe, num_candles):
        """
        Puxa os dados OHLCV instantaneamente.
        timeframe: mt5.TIMEFRAME_M1, mt5.TIMEFRAME_M5, mt5.TIMEFRAME_M15
        """
        if not self.connected:
            return None

        # Garante que o ativo está visível no Market Watch
        mt5.symbol_select(symbol, True)
        
        # Puxa as velas (a última vela índice 0 é a mais recente/atual)
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
        
        if rates is None or len(rates) == 0:
            print(f"[ERRO] Não foi possível obter dados para {symbol}")
            return None

        # Converte para um DataFrame Pandas para facilitar a matemática
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # MT5 traz do mais antigo para o mais novo. 
        # O último elemento (df.iloc[-1]) é a vela que está se movendo AGORA.
        return df


class FVGDetector:
    def __init__(self, min_gap_nasdaq=3.0, min_gap_xau=0.5):
        # Tamanho mínimo do gap para não operar ruído.
        self.min_gap_nasdaq = min_gap_nasdaq # Ex: 3 pontos de gap na NASDAQ
        self.min_gap_xau = min_gap_xau       # Ex: 0.5 (50 pips/pontos) no XAUUSD

    def find_unmitigated_fvgs(self, df, symbol):
        """
        Analisa o DataFrame procurando FVGs que AINDA NÃO foram mitigados.
        """
        fvgs = []
        
        # Define o tamanho mínimo baseado no ativo
        min_gap = self.min_gap_nasdaq if "US100" in symbol or "NAS" in symbol else self.min_gap_xau

        # Percorremos do candle mais antigo até os 3 últimos.
        # Precisamos de um padrão de 3 velas (i, i+1, i+2).
        for i in range(len(df) - 3):
            candle1 = df.iloc[i]
            candle2 = df.iloc[i+1] # O candle de expansão (onde o gap fica)
            candle3 = df.iloc[i+2]
            
            fvg_type = None
            fvg_top = 0
            fvg_bottom = 0

            # Lógica FVG Bullish (Alta)
            # A mínima do candle 3 não consegue alcançar a máxima do candle 1
            if candle3['low'] > candle1['high']:
                gap_size = candle3['low'] - candle1['high']
                if gap_size >= min_gap:
                    fvg_type = 'BULLISH'
                    fvg_top = candle3['low']
                    fvg_bottom = candle1['high']

            # Lógica FVG Bearish (Baixa)
            # A máxima do candle 3 não consegue alcançar a mínima do candle 1
            elif candle3['high'] < candle1['low']:
                gap_size = candle1['low'] - candle3['high']
                if gap_size >= min_gap:
                    fvg_type = 'BEARISH'
                    fvg_top = candle1['low']
                    fvg_bottom = candle3['high']

            # Se encontrou um FVG, verifica se algum candle DEPOIS do candle3 já o mitigou
            if fvg_type:
                mitigated = False
                # Pega todos os candles depois da formação do FVG até o momento atual
                subsequent_candles = df.iloc[i+3:]
                
                for _, sub_candle in subsequent_candles.iterrows():
                    if fvg_type == 'BULLISH' and sub_candle['low'] <= fvg_top:
                        mitigated = True
                        break
                    elif fvg_type == 'BEARISH' and sub_candle['high'] >= fvg_bottom:
                        mitigated = True
                        break
                
                if not mitigated:
                    fvgs.append({
                        'type': fvg_type,
                        'top': round(fvg_top, 2),
                        'bottom': round(fvg_bottom, 2),
                        'size': round(gap_size, 2),
                        'time_formed': candle2['time'].strftime('%H:%M'),
                        'age_candles': len(df) - (i+2) # Quão velho é esse FVG
                    })

        return fvgs

# =====================================================================
# TESTE RÁPIDO DO MÓDULO (Pode rodar este arquivo direto para testar)
# =====================================================================
if __name__ == "__main__":
    mt5_engine = MT5Engine()
    if mt5_engine.start():
        detector = FVGDetector(min_gap_nasdaq=4.0)
        
        # Substitua pelo ticker exato da sua corretora (ex: US100.cash, NAS100, XAUUSD)
        ativo = "US100" # Ajuste para o nome que aparece no seu MT5
        
        print(f"\n[SCAN] Analisando últimos 60 candles do {ativo} (Timeframe M5)...")
        # Puxa 60 candles do M5 (equivale a 5 horas de pregão)
        df_m5 = mt5_engine.get_candles(ativo, mt5.TIMEFRAME_M5, 60)
        
        if df_m5 is not None:
            fvgs_abertos = detector.find_unmitigated_fvgs(df_m5, ativo)
            
            if fvgs_abertos:
                print(f"✅ Encontrados {len(fvgs_abertos)} FVG(s) Abertos no M5:")
                for f in fvgs_abertos:
                    print(f"  -> {f['type']} | Zona: {f['top']} - {f['bottom']} | Idade: {f['age_candles']} velas")
            else:
                print("⏳ Nenhum FVG virgem encontrado no momento.")
                
        mt5_engine.stop()