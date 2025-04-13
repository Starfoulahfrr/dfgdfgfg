import json
import random
import string
from datetime import datetime, timedelta
import os

class AccessManager:
    def __init__(self):
        self.access_file = "data/access_codes.json"
        self._ensure_file_exists()
        
    def _ensure_file_exists(self):
        """Crée le fichier d'accès s'il n'existe pas"""
        if not os.path.exists("data"):
            os.makedirs("data")
        if not os.path.exists(self.access_file):
            with open(self.access_file, 'w') as f:
                json.dump({
                    "codes": [],
                    "authorized_users": []
                }, f, indent=4)

    def generate_code(self, admin_id: int) -> tuple[str, str]:
        """Génère un nouveau code d'accès"""
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        expiration = (datetime.now() + timedelta(hours=24)).isoformat()
        
        with open(self.access_file, 'r') as f:
            data = json.load(f)
        
        data["codes"].append({
            "code": code,
            "expiration": expiration,
            "created_by": admin_id,
            "used": False
        })
        
        with open(self.access_file, 'w') as f:
            json.dump(data, f, indent=4)
            
        return code, expiration

    def verify_code(self, code: str, user_id: int) -> tuple[bool, str]:
        """Vérifie un code d'accès"""
        with open(self.access_file, 'r') as f:
            data = json.load(f)
        
        if user_id in data["authorized_users"]:
            return True, "already_authorized"

        now = datetime.now()
        
        # Nettoyer les codes expirés
        data["codes"] = [c for c in data["codes"] 
                        if datetime.fromisoformat(c["expiration"]) > now]
        
        for c in data["codes"]:
            if c["code"] == code and not c["used"]:
                if datetime.fromisoformat(c["expiration"]) > now:
                    c["used"] = True
                    data["authorized_users"].append(user_id)
                    with open(self.access_file, 'w') as f:
                        json.dump(data, f, indent=4)
                    return True, "success"
                else:
                    return False, "expired"
        
        return False, "invalid"
    
    def is_authorized(self, user_id: int) -> bool:
        """Vérifie si un utilisateur est autorisé"""
        with open(self.access_file, 'r') as f:
            data = json.load(f)
        return user_id in data["authorized_users"]
    
    def list_active_codes(self) -> list:
        """Liste tous les codes actifs"""
        with open(self.access_file, 'r') as f:
            data = json.load(f)
        
        now = datetime.now()
        return [c for c in data["codes"] 
                if not c["used"] and datetime.fromisoformat(c["expiration"]) > now]