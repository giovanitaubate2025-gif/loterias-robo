import firebase_admin
from firebase_admin import credentials, db
import json
import os
import requests
import random
import time
from datetime import datetime
import urllib3

# Desativa avisos de segurança ao acessar a API da Caixa
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================================================================
# 1. MAPA DE TODAS AS 11 LOTERIAS
# ==============================================================================
LOTERIAS_CONFIG = {
    'lotofacil': {'bolas_jogo': 15, 'total_globos': 25, 'stat_path': 'Lotofacil_Estatisticas'},
    'megasena': {'bolas_jogo': 6, 'total_globos': 60, 'stat_path': 'Megasena_Estatisticas'},
    'quina': {'bolas_jogo': 5, 'total_globos': 80, 'stat_path': 'Quina_Estatisticas'},
    'lotomania': {'bolas_jogo': 50, 'total_globos': 100, 'stat_path': 'Lotomania_Estatisticas'},
    'timemania': {'bolas_jogo': 10, 'total_globos': 80, 'stat_path': 'Timemania_Estatisticas', 'especial': 'time_coracao'},
    'duplasena': {'bolas_jogo': 6, 'total_globos': 50, 'stat_path': 'DuplaSena_Estatisticas', 'sorteio2': True},
    'diadesorte': {'bolas_jogo': 7, 'total_globos': 31, 'stat_path': 'DiaDeSorte_Estatisticas', 'especial': 'mes_sorteado'},
    'supersete': {'bolas_jogo': 7, 'total_globos': 9, 'stat_path': 'SuperSete_Estatisticas', 'is_supersete': True},
    'maismilionaria': {'bolas_jogo': 6, 'total_globos': 50, 'stat_path': 'MaisMilionaria_Estatisticas', 'tem_trevos': True},
    'loteca': {'is_esportiva': True},
    'lotogol': {'is_esportiva': True}
}

def inicializar_firebase():
    service_account_info = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
    if not service_account_info:
        print("❌ ERRO: FIREBASE_SERVICE_ACCOUNT não encontrado!")
        return False
    try:
        if not firebase_admin._apps:
            cred_dict = json.loads(service_account_info)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {'databaseURL': "https://canal-da-loterias-default-rtdb.firebaseio.com"})
        return True
    except Exception as e:
        print(f"❌ ERRO Firebase: {e}")
        return False

def extrair_rateio_completo(dados, loteria):
    rateio = {}
    lista = dados.get('listaRateioPremio') or []
    if loteria == 'lotofacil':
        rateio = { "pago_15": 0.0, "pago_14": 0.0, "pago_13": 30.0, "pago_12": 12.0, "pago_11": 6.0 }
        for faixa in lista:
            n = faixa.get('faixa') or faixa.get('numeroFaixa') 
            v = faixa.get('valorPremio', 0.0)
            if n == 1: rateio["pago_15"] = v
            elif n == 2: rateio["pago_14"] = v
    else:
        for faixa in lista:
            n = faixa.get('faixa') or faixa.get('numeroFaixa')
            v = faixa.get('valorPremio', 0.0)
            rateio[f"faixa_{n}"] = v
    return rateio

def gerar_estatisticas_gg456(historico_completo, config):
    if config.get('is_esportiva'): return [], [], [], []
    frequencia = {}
    for sorteio in historico_completo:
        if isinstance(sorteio, list):
            for dezena in sorteio:
                frequencia[dezena] = frequencia.get(dezena, 0) + 1
    
    bolas_ordenadas = sorted(frequencia.items(), key=lambda x: x[1], reverse=True)
    quentes = [b[0] for b in bolas_ordenadas[:15]] if bolas_ordenadas else []
    atrasadas = [b[0] for b in bolas_ordenadas[-15:]] if bolas_ordenadas else []
    
    todas = [str(i).zfill(2) for i in range(1, config.get('total_globos', 25) + 1)]
    palpites = []
    for _ in range(50):
        p = random.sample(todas, config.get('bolas_jogo', 15))
        palpites.append(sorted(p))
    return palpites, [], quentes[:10], atrasadas[:10]

def buscar_dados_concurso(loteria, concurso_num=""):
    url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{loteria}/{concurso_num}"
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, verify=False, timeout=15)
        if res.status_code == 200: return res.json()
    except: pass
    return None

def executar_robo():
    if not inicializar_firebase(): return
    ref = db.reference()
    print("🚜 TRATOR INICIADO...")

    for loteria, cfg in LOTERIAS_CONFIG.items():
        try:
            print(f"📊 {loteria.upper()}")
            dados = buscar_dados_concurso(loteria)
            if not dados or 'numero' not in dados: continue
            
            # Sincroniza Histórico Faltante
            hist_ref = ref.child(f"Historico/{loteria}")
            ultimo_db = hist_ref.order_by_key().limit_to_last(1).get()
            u_concurso = int(list(ultimo_db.keys())[0]) if ultimo_db else 0
            
            if u_concurso < int(dados['numero']):
                for n in range(u_concurso + 1, int(dados['numero']) + 1):
                    d = buscar_dados_concurso(loteria, n) if n != int(dados['numero']) else dados
                    if d:
                        hist_ref.child(str(d['numero'])).set({
                            "concurso": str(d['numero']),
                            "data_sorteio": d.get('dataApuracao', ''),
                            "dezenas": [str(x).zfill(2) for x in d.get('listaDezenas', [])],
                            "rateio": extrair_rateio_completo(d, loteria)
                        })

            # Salva Resultado Atual
            ref.child(f"Resultados/{loteria}").set({
                "concurso": str(dados['numero']),
                "data_sorteio": dados.get('dataApuracao', ''),
                "dezenas": [str(x).zfill(2) for x in dados.get('listaDezenas', [])],
                "rateio": extrair_rateio_completo(dados, loteria)
            })

            # CORREÇÃO DEFINITIVA DO ERRO DO PRINT:
            if not cfg.get('is_esportiva'):
                raw = hist_ref.get()
                matriz = []
                # Se for lista, filtra nulos. Se for dicionário, pega os valores.
                if isinstance(raw, list):
                    matriz = [v['dezenas'] for v in raw if v and 'dezenas' in v]
                elif isinstance(raw, dict):
                    matriz = [v['dezenas'] for v in raw.values() if v and 'dezenas' in v]

                if matriz:
                    palpites, _, q, a = gerar_estatisticas_gg456(matriz, cfg)
                    ref.child(cfg['stat_path']).set({
                        "ultimoSorteio": matriz[-1],
                        "bolasQuentes": q, "bolasAtrasadas": a,
                        "palpitesProntos": palpites,
                        "horaSinc": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    })
            print(f"✅ {loteria.upper()} OK")
        except Exception as e:
            print(f"❌ Erro em {loteria}: {e}")

if __name__ == "__main__":
    executar_robo()
