# ai_groq.py — Agente de Inteligência de Regime Macro (Assíncrono e Desacoplado da Execução)
import os
import json
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class LumiGroqAgent:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        self.enabled = bool(api_key)
        self.client = Groq(api_key=api_key) if self.enabled else None
        self.model = "llama-3.3-70b-versatile"
        
        # Cache de Viés Macro (Atualizado em background a cada 15 min para NÃO travar scalping)
        self.macro_cache = {
            "NASDAQ": {"bias": "NEUTRAL", "allowed_profiles": ["tatico", "guardiao"], "updated_at": 0},
            "GOLD": {"bias": "NEUTRAL", "allowed_profiles": ["tatico", "guardiao"], "updated_at": 0}
        }

    def update_macro_regime_async(self, symbol_key, m15_structure, atr, spreads):
        """
        Atualiza o viés macroeconômico em segundo plano.
        Essa chamada NÃO bloqueia o envio de ordens.
        """
        if not self.enabled:
            return

        now = time.time()
        if now - self.macro_cache.get(symbol_key, {}).get("updated_at", 0) < 900: # 15 minutos de cache
            return

        prompt = f"""
        Você é o Chief Risk Officer de uma mesa proprietária institucional.
        Analise o regime para o ativo {symbol_key}:
        - Estrutura M15: {m15_structure}
        - ATR Atual: {atr}
        - Spread Atual: {spreads}

        Responda APENAS em JSON no formato:
        {{
            "bias": "BULLISH" ou "BEARISH" ou "NEUTRAL",
            "allowed_profiles": ["sniper", "tatico"] ou ["guardiao"],
            "justificativa": "resumo de 1 frase"
        }}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Responda estritamente em JSON puro sem markdown."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            data = json.loads(response.choices[0].message.content)
            self.macro_cache[symbol_key] = {
                "bias": data.get("bias", "NEUTRAL"),
                "allowed_profiles": data.get("allowed_profiles", ["tatico"]),
                "updated_at": now
            }
            print(f"🧠 [IA GROQ MACRO] {symbol_key} atualizado: Viés {data.get('bias')} | Perfis: {data.get('allowed_profiles')}")
        except Exception as e:
            print(f"⚠️ [IA GROQ] Falha na atualização macro ({e}). Mantendo heurística local.")

    def quick_validate_trade(self, symbol_key, direction, current_profile):
        """
        Validação instantânea em memória (< 1 milissegundo).
        Verifica o viés macro em cache sem fazer requisição de rede.
        """
        cached = self.macro_cache.get(symbol_key)
        if not cached or cached["bias"] == "NEUTRAL":
            return True, "Neutro / Liberado por Heurística Local"

        # Se a IA identificou regime estritamente baixista, não permite compras no topo
        if cached["bias"] == "BEARISH" and direction == "BUY":
            return False, f"IA Macro definiu viés BEARISH para {symbol_key}"

        if cached["bias"] == "BULLISH" and direction == "SELL":
            return False, f"IA Macro definiu viés BULLISH para {symbol_key}"

        return True, "Alinhado com Viés Institucional da IA"