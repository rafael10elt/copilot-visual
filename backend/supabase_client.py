import os
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

        if self.enabled:
            try:
                self.client = create_client(url, key)
                print("☁️ [SUPABASE] Conectado à nuvem com sucesso!")
            except Exception as e:
                print(f"⚠️ [SUPABASE] Erro ao conectar: {e}")
                self.enabled = False

    def send_heartbeat(self, profile, pnl=0.0, login="--", balance=0.0, equity=0.0, server="--", today_stats=None):
        if not self.enabled: return
        try:
            payload = {
                "is_online": True,
                "current_profile": profile,
                "pnl_today": round(pnl, 2),
                "account_login": str(login),
                "account_balance": round(balance, 2),
                "account_equity": round(equity, 2),
                "broker": str(server),
                "last_seen": datetime.now(timezone.utc).isoformat()
            }
            if today_stats:
                payload["today_stats"] = today_stats

            self.client.table("copilot_status").update(payload).eq("id", 1).execute()
        except Exception as e:
            print(f"Erro heartbeat: {e}")
                  
    def add_log(self, symbol, message, level="INFO"):
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
        if not self.enabled: return None
        try:
            res = self.client.table("copilot_settings").select("*").eq("id", 1).single().execute()
            return res.data
        except Exception:
            return None