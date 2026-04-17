import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# 1. Configuração da Chave do Firebase
service_account_info = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
DATABASE_URL = "https://canal-da-loterias-default-rtdb.firebaseio.com"

if not service_account_info:
    print("❌ Erro: Chave FIREBASE_SERVICE_ACCOUNT não configurada.")
    exit(1)

cred = credentials.Certificate(json.loads(service_account_info))
firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})

# 2. Lista de todas as loterias que vamos buscar
loterias = [
    {'id': 'lotofacil', 'nome': 'LOTOFÁCIL'},
    {'id': 'quina', 'nome': 'QUINA'},
    {'id': 'megasena', 'nome': 'MEGA-SENA'},
    {'id': 'lotomania', 'nome': 'LOTOMANIA'},
    {'id': 'timemania', 'nome': 'TIMEMANIA'},
    {'id': 'duplasena', 'nome': 'DUPLA SENA'},
    {'id': 'diadesorte', 'nome': 'DIA DE SORTE'},
    {'id': 'supersete', 'nome': 'SUPER SETE'},
    {'id': 'maismilionaria', 'nome': '+MILIONÁRIA'}
]

def capturar():
    # Configurando o robô para rodar invisível no servidor
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0")
    
    driver = webdriver.Chrome(options=options)
    
    # 3. Criando as DUAS pastas no Firebase, como combinamos!
    ref_proximo = db.reference('Proximo_Concurso')
    ref_resultados = db.reference('Resultados')

    for jogo in loterias:
        try:
            # Acessa o site da Caixa
            driver.get(f"https://servicebus2.caixa.gov.br/portalloterias/api/{jogo['id']}")
            time.sleep(3) # Pausa rápida para a Caixa não bloquear
            
            # Pega o texto puro que a Caixa devolve
            dados = json.loads(driver.find_element("tag name", "body").text)
            
            agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            # =========================================================
            # PASTA 1: SALVA OS DADOS DO PRÓXIMO CONCURSO
            # =========================================================
            info_proximo = {
                "nome": jogo['nome'],
                "proximo_premio": dados.get('valorEstimadoProximoConcurso', 0),
                "data_proximo": dados.get('dataProximoConcurso', '-'),
                "status": "ACUMULOU" if dados.get('acumulado') else "SAIU",
                "atualizado_em": agora
            }
            ref_proximo.child(jogo['id']).set(info_proximo)
            
            # =========================================================
            # PASTA 2: SALVA OS DADOS DO ÚLTIMO SORTEIO REALIZADO
            # =========================================================
            info_resultado = {
                "nome": jogo['nome'],
                "concurso": dados.get('numero', 0),
                "data_sorteio": dados.get('dataApuracao', '-'),
                "dezenas": dados.get('listaDezenas', []),
                "acumulou": dados.get('acumulado', False),
                "atualizado_em": agora
            }
            ref_resultados.child(jogo['id']).set(info_resultado)

            print(f"✅ {jogo['nome']}: Salvo nas pastas Resultados e Proximo_Concurso!")
            
        except Exception as e:
            print(f"❌ Erro ao buscar {jogo['nome']}: {e}")
            
    # Desliga o robô
    driver.quit()

if __name__ == "__main__":
    capturar()
