import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class LumiGroqAgent:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("⚠️ GROQ_API_KEY não encontrada no arquivo .env!")
        
        self.client = Groq(api_key=api_key)
        self.model = self.discover_best_model()

    def discover_best_model(self):
        """Descobre dinamicamente os modelos ativos na sua conta do Groq."""
        # Lista dos melhores modelos em ordem de prioridade
        preferidos = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama-3.1-70b-versatile",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
            "openai/gpt-oss-20b"
        ]

        try:
            # Pede para a API do Groq a lista real do que está liberado para você
            lista = self.client.models.list()
            ativos = [m.id for m in lista.data]
            print(f"[IA] Modelos encontrados na sua conta: {ativos[:4]}...")

            for cand in preferidos:
                if cand in ativos:
                    print(f"✅ [IA] Modelo autoselecionado com sucesso: {cand}")
                    return cand

            # Se nenhum dos preferidos estiver, pega o primeiro modelo de chat ativo
            escolhido = ativos[0]
            print(f"ℹ️ [IA] Usando modelo padrão ativo da conta: {escolhido}")
            return escolhido

        except Exception as e:
            print(f"⚠️ [IA] Erro ao listar modelos ({e}). Usando fallback padrão.")
            return "llama-3.3-70b-versatile"

    def validate_fvg_trade(self, symbol, fvg_type, fvg_price, m15_trend, atr, current_profile):
        """Envia o contexto matemático para validação."""
        prompt = f"""
        Você é um algoritmo institucional de trading. Responda APENAS em JSON no seguinte formato:
        {{"autorizado": true, "motivo": "resumo curto", "acao": "BUY_LIMIT"}} ou {{"autorizado": false, "motivo": "motivo", "acao": "NONE"}}

        CENÁRIO:
        - Ativo: {symbol}
        - Tendência M15: {m15_trend}
        - FVG M5: {fvg_type} em {fvg_price}
        - Volatilidade ATR M1: {atr}
        - Perfil: {current_profile}

        REGRA:
        1. BULLISH FVG só é autorizado se M15 for de Alta (UPTREND). Ação: BUY_LIMIT.
        2. BEARISH FVG só é autorizado se M15 for de Baixa (DOWNTREND). Ação: SELL_LIMIT.
        3. Caso contrário, autorizado: false e acao: NONE.
        """

        # Tenta com o modelo principal, se falhar tenta alternativas
        modelos_tentativa = [self.model, "llama-3.3-70b-versatile", "gemma2-9b-it"]

        for mod in modelos_tentativa:
            try:
                response = self.client.chat.completions.create(
                    model=mod,
                    messages=[
                        {"role": "system", "content": "Você é uma IA de trading que só responde em JSON estrito."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                resposta_texto = response.choices[0].message.content
                decisao = json.loads(resposta_texto)
                return decisao

            except Exception as e:
                print(f"⚠️ Tentativa com {mod} falhou: {e}. Tentando alternativa...")
                continue

        # Fallback Heurístico Institucional (Garante que você não perde o trade se a API oscilar)
        print("⚡ [IA FALLBACK] Validando matematicamente pelo algoritmo interno...")
        if fvg_type == "BULLISH" and "UPTREND" in m15_trend:
            return {"autorizado": True, "motivo": "Heurística: Alinhamento M15 Alta com FVG Compra", "acao": "BUY_LIMIT"}
        elif fvg_type == "BEARISH" and "DOWNTREND" in m15_trend:
            return {"autorizado": True, "motivo": "Heurística: Alinhamento M15 Baixa com FVG Venda", "acao": "SELL_LIMIT"}
        
        return {"autorizado": False, "motivo": "FVG contra a tendência maior do M15", "acao": "NONE"}

    def analyze_daily_regime(self, market_summary_json):
        return {"perfil_recomendado": "tatico", "justificativa": "Modo automático calibrado."}