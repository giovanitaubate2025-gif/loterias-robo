import os
import json
import requests
from datetime import datetime

# BUSCA AS CHAVES NO GITHUB
chave_drive = os.environ.get("GOOGLE_CREDENTIALS")
chave_nuvem = os.environ.get("FIREBASE_KEY")

URL_PLANILHA = "https://script.google.com/macros/s/AKfycby-taEbqkJHCo7G0gNOXutIhk6IpTJ2TWmCyd8yoAJV0hKtGUV-wGYEuidJJg7OSFNDIA/exec"
URL_FIREBASE = "https://canal-da-loterias-default-rtdb.firebaseio.com/"
SECRET_FIREBASE = "7gS8ASjfG5ZGRVu55Yj5QRw58ZzLCMBzWFLOyrfd"

def motor_principal():
    print("🚜 MOTOR GG-456: OPERAÇÃO INICIADA")
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    try:
        if chave_nuvem:
            info = json.loads(chave_nuvem)
            payload = {"status": "ONLINE", "projeto": info.get('project_id'), "hora": agora}
            url = f"{URL_FIREBASE}STATUS_MOTOR.json?auth={SECRET_FIREBASE}"
            requests.put(url, data=json.dumps(payload))
            print("🚀 Nuvem sincronizada!")

        print("📡 Enviando comando para a Planilha...")
        # 👇 A SENHA EXATA QUE A SUA PLANILHA ESPERA (Projeto 14) 👇
        params = {"acao": "EXECUTAR_TRATOR", "loteria": "TODOS"}
        res = requests.get(URL_PLANILHA, params=params, timeout=300)
        print(f"Resposta da Planilha: {res.text}")

    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    motor_principal()
