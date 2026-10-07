# ai_groq.py — Agente de Regime Macro Institucional com Autodescoberta de Modelos Ativos
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
        self.model = self.detect_best_active_model() if self.enabled else None
        
        # Cache de Viés Macro (Atualizado em background sem travar scalping)
        self.macro_cache = {
            "NASDAQ": {"bias": "NEUTRAL", "allowed_profiles": ["tatico", "guardiao"], "updated_at": 0},
            "GOLD": {"bias": "NEUTRAL", "allowed_profiles": ["tatico", "guardiao"], "updated_at": 0}
        }

    def detect_best_active_model(self):
        """Descobre dinamicamente na API da Groq quais modelos estão liberados na sua conta."""
        candidatos_preferidos = [
            "llama-3.1-8b-instant",
            "llama3-70b-8192",
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]

        try:
            lista = self.client.models.list()
            ativos = [m.id for m in lista.data]
            
            for cand in candidatos_preferidos:
                if cand in ativos:
                    print(f"✅ [IA GROQ] Modelo autoselecionado com sucesso: {cand}")
                    return cand

            # Se nenhum dos preferidos estiver, seleciona o primeiro disponível
            if len(ativos) > 0:
                print(f"ℹ️ [IA GROQ] Usando modelo ativo disponível: {ativos[0]}")
                return ativos[0]

        except Exception as e:
            print(f"⚠️ [IA GROQ] Erro ao listar modelos ({e}). Usando fallback padrão.")

        return "llama-3.1-8b-instant"

    def update_macro_regime_async(self, symbol_key, m15_structure, atr, spreads):
        """
        Atualiza o viés macroeconômico em segundo plano.
        Travado a cada 10 minutos (mesmo se der erro, NÃO entra em loop).
        """
        if not self.enabled or not self.client or not self.model:
            return

        now = time.time()
        # Trava rigorosa: se já tentou nos últimos 600 segundos (10 min), aguarda
        if now - self.macro_cache.get(symbol_key, {}).get("updated_at", 0) < 600:
            return

        # IMPORTANTE: Atualiza o timestamp IMEDIATAMENTE para matar o loop se der erro
        self.macro_cache[symbol_key]["updated_at"] = now

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
            self.macro_cache[symbol_key]["bias"] = data.get("bias", "NEUTRAL")
            self.macro_cache[symbol_key]["allowed_profiles"] = data.get("allowed_profiles", ["tatico"])
            print(f"🧠 [IA GROQ MACRO] {symbol_key} calibrado: Viés {data.get('bias')} | Perfis: {data.get('allowed_profiles')}")

        except Exception as e:
            # Em caso de falha de cota ou rede, mantém a heurística local sem flood no terminal
            print(f"⚠️ [IA GROQ] Erro na consulta ({e}). Heurística SMC local assumiu o ativo {symbol_key}.")

    def quick_validate_trade(self, symbol_key, direction, current_profile):
        """
        Validação instantânea em memória (< 1 ms).
        Zero latência no momento de enviar a ordem.
        """
        cached = self.macro_cache.get(symbol_key)
        if not cached or cached["bias"] == "NEUTRAL":
            return True, "Liberado por SMC / Heurística Local"

        if cached["bias"] == "BEARISH" and direction == "BUY":
            return False, f"Viés Macro da IA é BEARISH para {symbol_key}"

        if cached["bias"] == "BULLISH" and direction == "SELL":
            return False, f"Viés Macro da IA é BULLISH para {symbol_key}"

        return True, "Alinhado com o Viés Macro da IA"