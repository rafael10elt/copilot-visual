# ai_groq.py — Agente de Regime Macro Institucional (Filtro Estrito de Modelos de Chat)
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
        
        self.macro_cache = {
            "NASDAQ": {"bias": "NEUTRAL", "allowed_profiles": ["tatico", "guardiao"], "updated_at": 0},
            "GOLD": {"bias": "NEUTRAL", "allowed_profiles": ["tatico", "guardiao"], "updated_at": 0}
        }

    def detect_best_active_model(self):
        """Descobre modelos de chat reais, ignorando modelos de classificação/guarda."""
        candidatos_preferidos = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "llama3-70b-8192",
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]

        termos_bloqueados = ["guard", "whisper", "orpheus", "embedding", "audio", "classification"]

        try:
            lista = self.client.models.list()
            # Filtra apenas modelos que são de texto/chat real
            ativos = [
                m.id for m in lista.data 
                if not any(b in m.id.lower() for b in termos_bloqueados)
            ]
            
            # 1. Tenta correspondência com a lista de preferidos
            for cand in candidatos_preferidos:
                if cand in ativos:
                    print(f"✅ [IA GROQ] Modelo de chat ativo selecionado: {cand}")
                    return cand

            # 2. Se não estiver nos preferidos, pega o primeiro modelo de chat válido
            if len(ativos) > 0:
                print(f"ℹ️ [IA GROQ] Usando modelo de chat disponível: {ativos[0]}")
                return ativos[0]

        except Exception as e:
            print(f"⚠️ [IA GROQ] Erro ao listar modelos ({e}). Usando fallback padrão.")

        return "llama-3.1-8b-instant"

    def update_macro_regime_async(self, symbol_key, m15_structure, atr, spreads):
        if not self.enabled or not self.client or not self.model:
            return

        now = time.time()
        if now - self.macro_cache.get(symbol_key, {}).get("updated_at", 0) < 600:
            return

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
            print(f"🧠 [IA GROQ MACRO] {symbol_key} calibrado via {self.model}: Viés {data.get('bias')} | Perfis: {data.get('allowed_profiles')}")

        except Exception as e:
            print(f"⚠️ [IA GROQ] Falha na consulta ({e}). Heurística SMC local mantida no ativo {symbol_key}.")

    def quick_validate_trade(self, symbol_key, direction, current_profile):
        cached = self.macro_cache.get(symbol_key)
        if not cached or cached["bias"] == "NEUTRAL":
            return True, "Liberado por SMC / Heurística Local"

        if cached["bias"] == "BEARISH" and direction == "BUY":
            return False, f"Viés Macro da IA é BEARISH para {symbol_key}"

        if cached["bias"] == "BULLISH" and direction == "SELL":
            return False, f"Viés Macro da IA é BULLISH para {symbol_key}"

        return True, "Alinhado com o Viés Macro da IA"