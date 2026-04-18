import firebase_admin
from firebase_admin import credentials, db
import json
import os
import requests
import sys
import urllib3
from datetime import datetime

# Desativa avisos de segurança chatos do site da Caixa
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def atualizar_loterias():
    print("🤖 Iniciando o Robô...")
    
    # 1. Autenticação Firebase
    service_account_info = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
    if not service_account_info:
        print("❌ ERRO FATAL: Segredo FIREBASE_SERVICE_ACCOUNT não encontrado no GitHub!")
        sys.exit(1) # Faz a bolinha ficar VERMELHA no GitHub

    try:
        cert_dict = json.loads(service_account_info)
    except Exception as e:
        print(f"❌ ERRO FATAL: O Segredo copiado não é válido. {e}")
        sys.exit(1)

    database_url = "https://canal-da-loterias-default-rtdb.firebaseio.com"

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(cert_dict)
            firebase_admin.initialize_app(cred, {'databaseURL': database_url})
        print("✅ Conectado ao Firebase com sucesso!")
    except Exception as e:
        print(f"❌ ERRO ao conectar no Firebase: {e}")
        sys.exit(1)

    # 2. Busca de Dados na Fonte OFICIAL da Caixa Econômica
    print("⏳ Buscando resultados direto do servidor da Caixa...")
    try:
        url = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        response.raise_for_status()
        dados = response.json()
        print(f"✅ Dados fresquinhos recebidos! Concurso: {dados.get('numero')}")
        
    except Exception as e:
        print(f"❌ ERRO ao buscar dados da Caixa: {e}")
        sys.exit(1)

    # 3. Organiza os dados para o seu Aplicativo
    try:
        resultado_data = {
            "concurso": str(dados['numero']),
            "data_sorteio": dados['dataApuracao'],
            "dezenas": [int(n) for n in dados['listaDezenas']]
        }

        proximo_data = {
            "proximo_premio": dados['valorEstimadoProximoConcurso'],
            "data_proximo": dados['dataProximoConcurso'],
            "status": "ACUMULOU" if dados['acumulado'] else "ESTIMATIVA",
            "concurso_proximo": str(int(dados['numero']) + 1)
        }

        dezenas_sorteadas = [str(n).zfill(2) for n in dados['listaDezenas']]
        todas_dezenas = [str(n).zfill(2) for n in range(1, 26)]
        bolas_atrasadas = [d for d in todas_dezenas if d not in dezenas_sorteadas]
        
        estatisticas = {
            "bolasQuentes": dezenas_sorteadas[:8],
            "bolasAtrasadas": bolas_atrasadas[:8],
            "totalDeJogosAnalisados": 3500 + int(dados['numero']),
            "horaDaSincronizacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }

        # 4. Escreve nas Pastas do Firebase
        print("⏳ Salvando as pastas no seu banco de dados...")
        ref = db.reference()
        ref.child("Resultados/lotofacil").set(resultado_data)
        ref.child("Proximo_Concurso/lotofacil").set(proximo_data)
        ref.child("Lotofacil_Estatisticas").set(estatisticas)

        print(f"🚀 SUCESSO ABSOLUTO! O Robô gravou as pastas na nuvem!")

    except Exception as e:
        print(f"❌ ERRO ao escrever no Firebase: {e}")
        sys.exit(1)

if __name__ == "__main__":
    atualizar_loterias()
