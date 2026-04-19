import os
import json
import requests
from datetime import datetime

# 1. PEGA AS CHAVES DO COFRE
chave_drive = os.environ.get("GOOGLE_CREDENTIALS")
chave_nuvem = os.environ.get("FIREBASE_KEY")

# 2. CONFIGURAÇÕES FIXAS
URL_PLANILHA = "https://script.google.com/macros/s/AKfycby-taEbqkJHCo7G0gNOXutIhk6IpTJ2TWmCyd8yoAJV0hKtGUV-wGYEuidJJg7OSFNDIA/exec"
URL_FIREBASE = "https://canal-da-loterias-default-rtdb.firebaseio.com/"
SECRET_FIREBASE = "7gS8ASjfG5ZGRVu55Yj5QRw58ZzLCMBzWFLOyrfd"

def motor_principal():
    print("🚜 MOTOR GG-456: OPERAÇÃO INICIADA")
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    try:
        # FASE A: NUVEM
        if chave_nuvem:
            info = json.loads(chave_nuvem)
            status = {"status": "ONLINE", "projeto": info.get('project_id'), "horario": agora}
            url = f"{URL_FIREBASE}STATUS_MOTOR.json?auth={SECRET_FIREBASE}"
            requests.put(url, data=json.dumps(status))
            print("🚀 Nuvem sincronizada!")

        # FASE B: PLANILHA
        print("📡 Enviando sinal para a Planilha...")
        params = {"acao": "EXECUTAR_TRATOR_GLOBAL", "loteria": "TODAS"}
        res = requests.get(URL_PLANILHA, params=params, timeout=300)
        print(f"📥 RESPOSTA: {res.text}")

    except Exception as e:
        print(f"❌ Erro crítico: {e}")

if __name__ == "__main__":
    motor_principal()
