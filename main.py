import os
import json
import requests
from datetime import datetime

# BUSCA AS CHAVES NO COFRE DO GITHUB
e_drive = os.environ.get("GOOGLE_CREDENTIALS")
e_nuvem = os.environ.get("FIREBASE_KEY")

# CONFIGURAÇÕES DE DESTINO
URL_PLANILHA = "https://script.google.com/macros/s/AKfycby-taEbqkJHCo7G0gNOXutIhk6IpTJ2TWmCyd8yoAJV0hKtGUV-wGYEuidJJg7OSFNDIA/exec"
URL_FIREBASE = "https://canal-da-loterias-default-rtdb.firebaseio.com/"
SECRET_FIREBASE = "7gS8ASjfG5ZGRVu55Yj5QRw58ZzLCMBzWFLOyrfd"

def motor_principal():
    print("🚜 MOTOR GG-456: OPERAÇÃO INICIADA")
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    try:
        # A. SINCRONIZAÇÃO COM A NUVEM
        if e_nuvem:
            info_fb = json.loads(e_nuvem)
            status_payload = {
                "status": "CONECTADO",
                "projeto": info_fb.get('project_id'),
                "horario": agora
            }
            url_fb = f"{URL_FIREBASE}STATUS_SISTEMA.json?auth={SECRET_FIREBASE}"
            requests.put(url_fb, data=json.dumps(status_payload))
            print("🚀 Nuvem sincronizada!")

        # B. DISPARO DA PLANILHA
        print("📡 Enviando sinal para a Planilha...")
        params = {"acao": "EXECUTAR_TRATOR", "loteria": "TODOS"}
        res = requests.get(URL_PLANILHA, params=params, timeout=300)
        print(f"📥 RESPOSTA: {res.text}")

    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    motor_principal()
