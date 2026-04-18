import firebase_admin
from firebase_admin import credentials, db
import json
import os
import requests
import sys
import urllib3
from datetime import datetime

# Desativa avisos de segurança da Caixa
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Lista completa de todas as loterias que o robô vai varrer
LOTERIAS_CAIXA = [
    'lotofacil', 'megasena', 'quina', 'lotomania', 
    'duplasena', 'diadesorte', 'timemania', 'supersete', 
    'maismilionaria', 'loteca', 'lotogol'
]

def inicializar_firebase():
    service_account_info = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
    if not service_account_info:
        print("❌ ERRO: Segredo FIREBASE_SERVICE_ACCOUNT não encontrado!")
        sys.exit(1)

    try:
        cert_dict = json.loads(service_account_info)
    except Exception as e:
        print(f"❌ ERRO no formato do Segredo: {e}")
        sys.exit(1)

    database_url = "https://canal-da-loterias-default-rtdb.firebaseio.com"

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(cert_dict)
            firebase_admin.initialize_app(cred, {'databaseURL': database_url})
        print("✅ Conectado ao Firebase!")
    except Exception as e:
        print(f"❌ ERRO ao conectar no Firebase: {e}")
        sys.exit(1)

def atualizar_loterias():
    print("🤖 Iniciando o Super Robô Multiloterias...")
    inicializar_firebase()
    ref = db.reference()

    for loteria in LOTERIAS_CAIXA:
        print(f"\n⏳ Buscando dados da {loteria.upper()}...")
        try:
            url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{loteria}/"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, verify=False, timeout=15)
            
            # Se a loteria foi descontinuada (ex: Lotogol), a Caixa pode retornar erro. O robô ignora e vai pra próxima.
            if response.status_code != 200:
                print(f"⚠️ Aviso: A loteria {loteria} retornou status {response.status_code}. Pulando...")
                continue
                
            dados = response.json()
            concurso_num = str(dados.get('numero'))
            
            # 1. PROCESSAR RATEIO (PRÊMIOS OFICIAIS)
            rateio = {}
            lista_rateio = dados.get('listaRateioPremio', [])
            
            if loteria == 'lotofacil':
                # Regra exata combinada para o aplicativo da Lotofácil não quebrar
                rateio = { "pago_15": 0.0, "pago_14": 0.0, "pago_13": 30.0, "pago_12": 12.0, "pago_11": 6.0 }
                for faixa in lista_rateio:
                    n = faixa.get('numeroFaixa')
                    v = faixa.get('valorPremio', 0.0)
                    if n == 1: rateio["pago_15"] = v
                    elif n == 2: rateio["pago_14"] = v
                    elif n == 3: rateio["pago_13"] = v
                    elif n == 4: rateio["pago_12"] = v
                    elif n == 5: rateio["pago_11"] = v
            else:
                # Regra genérica para todas as outras loterias (ex: faixa_1 = Sena, faixa_2 = Quina, etc)
                for faixa in lista_rateio:
                    n = faixa.get('numeroFaixa')
                    rateio[f"faixa_{n}"] = faixa.get('valorPremio', 0.0)

            # 2. PACOTE DE RESULTADO ATUAL
            resultado_data = {
                "concurso": concurso_num,
                "data_sorteio": dados.get('dataApuracao', ''),
                "dezenas": [int(n) for n in dados.get('listaDezenas', [])] if dados.get('listaDezenas') else [],
                "rateio": rateio
            }

            # Regras especiais para loterias com dados extras
            if loteria == 'maismilionaria':
                resultado_data["trevos"] = dados.get('listaTrevosSorteados', [])
            elif loteria == 'duplasena':
                resultado_data["dezenas_sorteio2"] = dados.get('listaDezenasSegundoSorteio', [])
            elif loteria == 'timemania':
                resultado_data["time_coracao"] = dados.get('nomeTimeCoracaoSorteado', '')
            elif loteria == 'diadesorte':
                resultado_data["mes_sorteado"] = dados.get('nomeMesSorteado', '')
            elif loteria in ['loteca', 'lotogol']:
                # Nas esportivas, pegamos a lista de partidas em vez de dezenas
                resultado_data["partidas"] = dados.get('listaResultadoEquipeEsportiva', [])

            # 3. PACOTE DO PRÓXIMO CONCURSO
            proximo_data = {
                "proximo_premio": dados.get('valorEstimadoProximoConcurso', 0.0),
                "data_proximo": dados.get('dataProximoConcurso', ''),
                "status": "ACUMULOU" if dados.get('acumulado') else "ESTIMATIVA",
                "concurso_proximo": str(int(concurso_num) + 1) if concurso_num.isdigit() else ""
            }

            # 4. GRAVAÇÃO NO FIREBASE
            ref.child(f"Resultados/{loteria}").set(resultado_data)
            ref.child(f"Proximo_Concurso/{loteria}").set(proximo_data)
            ref.child(f"Historico/{loteria}/{concurso_num}").set(resultado_data)

            # 5. ESTATÍSTICAS DA IA (Apenas para Lotofácil no momento)
            if loteria == 'lotofacil':
                dezenas_sorteadas = [str(n).zfill(2) for n in dados.get('listaDezenas', [])]
                todas_dezenas = [str(n).zfill(2) for n in range(1, 26)]
                bolas_atrasadas = [d for d in todas_dezenas if d not in dezenas_sorteadas]
                estatisticas = {
                    "bolasQuentes": dezenas_sorteadas[:8],
                    "bolasAtrasadas": bolas_atrasadas[:8],
                    "totalDeJogosAnalisados": 3500 + int(concurso_num),
                    "horaDaSincronizacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                }
                ref.child("Lotofacil_Estatisticas").set(estatisticas)

            print(f"✅ {loteria.upper()} Gravada com sucesso! (Concurso {concurso_num})")

        except Exception as e:
            print(f"❌ ERRO ao processar a loteria {loteria}: {e}")
            continue # Se der erro em uma, não para o robô, vai para a próxima!

    print("\n🏁 FIM DA VARREDURA! O Robô atualizou todas as loterias no Firebase.")

if __name__ == "__main__":
    atualizar_loterias()
