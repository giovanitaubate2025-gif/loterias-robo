import firebase_admin
from firebase_admin import credentials, db
import json
import os
import requests
from datetime import datetime
import urllib3

# Desativa avisos de segurança
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LOTERIAS_CONFIG = {
    'lotofacil': {'especial': None, 'trevos': False, 'sorteio2': False},
    'megasena': {'especial': None, 'trevos': False, 'sorteio2': False},
    'quina': {'especial': None, 'trevos': False, 'sorteio2': False},
    'lotomania': {'especial': None, 'trevos': False, 'sorteio2': False},
    'timemania': {'especial': 'time_coracao', 'trevos': False, 'sorteio2': False},
    'duplasena': {'especial': None, 'trevos': False, 'sorteio2': True},
    'diadesorte': {'especial': 'mes_sorteado', 'trevos': False, 'sorteio2': False},
    'supersete': {'especial': None, 'trevos': False, 'sorteio2': False},
    'maismilionaria': {'especial': None, 'trevos': True, 'sorteio2': False},
    'loteca': {'is_esportiva': True},
    'lotogol': {'is_esportiva': True}
}

def extrair_rateio(dados, loteria):
    rateio = {}
    lista = dados.get('listaRateioPremio', []) or []
    if loteria == 'lotofacil':
        rateio = { "pago_15": 0.0, "pago_14": 0.0, "pago_13": 30.0, "pago_12": 12.0, "pago_11": 6.0 }
        for f in lista:
            n, v = f.get('faixa') or f.get('numeroFaixa'), f.get('valorPremio', 0.0)
            if n == 1: rateio["pago_15"] = v
            elif n == 2: rateio["pago_14"] = v
    elif loteria == 'maismilionaria':
        mapa = {1:'6_2', 2:'6_1', 3:'5_2', 4:'5_1', 5:'4_2', 6:'4_1', 7:'3_2', 8:'3_1', 9:'2_2', 10:'2_1'}
        for f in lista:
            n, v = f.get('faixa') or f.get('numeroFaixa'), f.get('valorPremio', 0.0)
            if n in mapa: rateio[f"pago_{mapa[n]}"] = v
    else:
        for f in lista:
            n, v = f.get('faixa') or f.get('numeroFaixa'), f.get('valorPremio', 0.0)
            rateio[f"faixa_{n}"] = v
            acertos = f.get('numeroDeAcertos')
            if acertos is not None: rateio[f"pago_{acertos}"] = v
    return rateio

def executar():
    service_account = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
    if not service_account: return
    
    if not firebase_admin._apps:
        cred = credentials.Certificate(json.loads(service_account))
        firebase_admin.initialize_app(cred, {'databaseURL': "https://canal-da-loterias-default-rtdb.firebaseio.com"})
    
    ref = db.reference()
    headers = {'User-Agent': 'Mozilla/5.0'}

    for loteria, cfg in LOTERIAS_CONFIG.items():
        try:
            res = requests.get(f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{loteria}", headers=headers, verify=False, timeout=10)
            if res.status_code != 200: continue
            dados = res.json()
            num = str(dados['numero'])
            
            pacote = {
                "concurso": num,
                "data_sorteio": dados.get('dataApuracao', ''),
                "rateio": extrair_rateio(dados, loteria),
                "dezenas": [str(n).zfill(2) for n in dados.get('listaDezenas', [])] if not cfg.get('is_esportiva') else None,
                "partidas": dados.get('listaResultadoEquipeEsportiva', []) if cfg.get('is_esportiva') else None
            }
            
            if cfg.get('trevos'): pacote["trevos"] = [str(n).zfill(2) for n in (dados.get('listaTrevosSorteados') or [])]
            if cfg.get('sorteio2'): pacote["dezenas_sorteio2"] = [str(n).zfill(2) for n in (dados.get('listaDezenasSegundoSorteio') or [])]
            if cfg.get('especial'): pacote[cfg['especial']] = dados.get('nomeTimeCoracaoMesSorte') or dados.get('nomeMesSorteado') or ""

            ref.child(f"Resultados/{loteria}").set(pacote)
            ref.child(f"Historico/{loteria}/{num}").set(pacote)
            ref.child(f"Proximo_Concurso/{loteria}").set({
                "proximo_premio": dados.get('valorEstimadoProximoConcurso', 0.0),
                "data_proximo": dados.get('dataProximoConcurso', ''),
                "concurso_proximo": str(int(num) + 1)
            })
        except: continue

if __name__ == "__main__":
    executar()
    print("✅ Sincronização concluída.")
