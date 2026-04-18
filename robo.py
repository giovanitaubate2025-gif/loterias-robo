import firebase_admin
from firebase_admin import credentials, db
import json
import os
import requests
import time
from datetime import datetime
import urllib3

# Desativa avisos de segurança ao acessar a API da Caixa
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================================================================
# 1. MAPA DE CONFIGURAÇÕES (Simplificado sem estatísticas)
# ==============================================================================
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

# ==============================================================================
# 2. CONEXÃO COM O FIREBASE
# ==============================================================================
def inicializar_firebase():
    service_account_info = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
    if not service_account_info:
        print("❌ ERRO: Segredo FIREBASE_SERVICE_ACCOUNT não encontrado!")
        return False
    try:
        if not firebase_admin._apps:
            cred_dict = json.loads(service_account_info)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred, {'databaseURL': "https://canal-da-loterias-default-rtdb.firebaseio.com"})
        return True
    except Exception as e:
        print(f"❌ ERRO ao conectar no Firebase: {e}")
        return False

# ==============================================================================
# 3. EXTRAÇÃO DE RATEIO (Prêmios)
# ==============================================================================
def extrair_rateio(dados, loteria):
    rateio = {}
    lista = dados.get('listaRateioPremio', []) or []
    
    if loteria == 'lotofacil':
        # Valores fixos que a Caixa às vezes omite no JSON
        rateio = { "pago_15": 0.0, "pago_14": 0.0, "pago_13": 30.0, "pago_12": 12.0, "pago_11": 6.0 }
        for faixa in lista:
            n = faixa.get('faixa') or faixa.get('numeroFaixa') 
            v = faixa.get('valorPremio', 0.0)
            if n == 1: rateio["pago_15"] = v
            elif n == 2: rateio["pago_14"] = v
            
    elif loteria == 'maismilionaria':
        mapa = {1:'6_2', 2:'6_1', 3:'5_2', 4:'5_1', 5:'4_2', 6:'4_1', 7:'3_2', 8:'3_1', 9:'2_2', 10:'2_1'}
        for faixa in lista:
            n = faixa.get('faixa') or faixa.get('numeroFaixa')
            v = faixa.get('valorPremio', 0.0)
            if n in mapa: rateio[f"pago_{mapa[n]}"] = v
    else:
        for faixa in lista:
            n = faixa.get('faixa') or faixa.get('numeroFaixa')
            v = faixa.get('valorPremio', 0.0)
            rateio[f"faixa_{n}"] = v
            acertos = faixa.get('numeroDeAcertos')
            if acertos is not None:
                rateio[f"pago_{acertos}"] = v
    return rateio

# ==============================================================================
# 4. BUSCA DE DADOS NA CAIXA
# ==============================================================================
def buscar_dados_caixa(loteria):
    url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{loteria}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=15)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"⚠️ Falha ao buscar {loteria}: {e}")
    return None

# ==============================================================================
# 5. EXECUÇÃO PRINCIPAL
# ==============================================================================
def executar_robo():
    if not inicializar_firebase(): return
    ref = db.reference()

    print(f"🚀 Iniciando Sincronização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    for loteria, cfg in LOTERIAS_CONFIG.items():
        dados = buscar_dados_caixa(loteria)
        if not dados or 'numero' not in dados:
            continue

        concurso_num = str(dados['numero'])
        print(f"📦 Processando {loteria.upper()} - Concurso {concurso_num}")

        # 1. Preparar pacote de dados
        pacote = {
            "concurso": concurso_num,
            "data_sorteio": dados.get('dataApuracao', ''),
            "rateio": extrair_rateio(dados, loteria)
        }

        # Trata dados de dezenas ou partidas (esportivas)
        if cfg.get('is_esportiva'):
            pacote["partidas"] = dados.get('listaResultadoEquipeEsportiva', [])
        else:
            pacote["dezenas"] = [str(n).zfill(2) for n in dados.get('listaDezenas', [])]

        # Campos extras (Trevos, Sorteio 2, Meses/Times)
        if cfg.get('trevos'):
            t = dados.get('listaTrevosSorteados') or dados.get('listaDezenasSegundoSorteio') or []
            pacote["trevos"] = [str(n).zfill(2) for n in t]
        
        if cfg.get('sorteio2'):
            pacote["dezenas_sorteio2"] = [str(n).zfill(2) for n in dados.get('listaDezenasSegundoSorteio', [])]
            
        if cfg.get('especial'):
            campo = cfg['especial']
            pacote[campo] = dados.get('nomeTimeCoracaoMesSorte') or dados.get('nomeMesSorteado') or ""

        # 2. Salvar em RESULTADOS (Último sorteio)
        ref.child(f"Resultados/{loteria}").set(pacote)

        # 3. Salvar em HISTÓRICO (Apenas o concurso atual)
        ref.child(f"Historico/{loteria}/{concurso_num}").set(pacote)

        # 4. Salvar PRÓXIMO CONCURSO
        proximo = {
            "proximo_premio": dados.get('valorEstimadoProximoConcurso', 0.0),
            "data_proximo": dados.get('dataProximoConcurso', ''),
            "concurso_proximo": str(int(concurso_num) + 1),
            "status": "ACUMULOU" if dados.get('acumulado') else "ESTIMATIVA"
        }
        ref.child(f"Proximo_Concurso/{loteria}").set(proximo)

    print("✅ Sincronização concluída com sucesso!")

if __name__ == "__main__":
    executar_robo()
