import os
import threading
from datetime import datetime, timezone
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

class SupabaseSync:
    def __init__(self, on_settings_update_callback=None):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        self.enabled = bool(url and key)
        self.client = None
        self.on_settings_update = on_settings_update_callback

        if self.enabled:
            try:
                self.client = create_client(url, key)
                print("☁️ [SUPABASE] Conectado à nuvem com sucesso!")
                self._carregar_configuracoes_iniciais()
            except Exception as e:
                print(f"⚠️ [SUPABASE] Erro ao conectar: {e}")
                self.enabled = False
        else:
            print("ℹ️ [SUPABASE] Chaves não configuradas no .env. Rodando em modo offline.")

    def _carregar_configuracoes_iniciais(self):
        """Busca o perfil atual configurado no banco."""
        try:
            res = self.client.table("copilot_settings").select("*").eq("id", 1).single().execute()
            if res.data and self.on_settings_update:
                self.on_settings_update(res.data)
        except Exception:
            pass

    def send_heartbeat(self, profile, pnl=0.0):
        """Atualiza no banco que o robô do notebook está vivo."""
        if not self.enabled: return
        try:
            self.client.table("copilot_status").update({
                "is_online": True,
                "current_profile": profile,
                "pnl_today": pnl,
                "last_seen": datetime.now(timezone.utc).isoformat()
            }).eq("id", 1).execute()
        except Exception:
            pass

    def add_log(self, symbol, message, level="INFO"):
        """Envia um log que vai pipocar instantaneamente no feed do seu celular."""
        print(f"[{level}] {symbol or 'SISTEMA'}: {message}")
        if not self.enabled: return
        try:
            self.client.table("copilot_logs").insert({
                "symbol": symbol,
                "message": message,
                "level": level
            }).execute()
        except Exception:
            pass

    def check_remote_settings(self):
        """Checa se você mudou algum toggle no celular."""
        if not self.enabled: return None
        try:
            res = self.client.table("copilot_settings").select("*").eq("id", 1).single().execute()
            return res.data
        except Exception:
            return None