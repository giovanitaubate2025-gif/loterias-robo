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
# 1. MAPA DE TODAS AS 11 LOTERIAS (Nomes oficiais e regras)
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

# ==============================================================================
# 2. CONEXÃO COM A NUVEM
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
# 3. EXTRAÇÃO DE PRÊMIOS (Rateio Completo)
# ==============================================================================
def extrair_rateio_completo(dados, loteria):
    rateio = {}
    lista = dados.get('listaRateioPremio', [])
    
    if loteria == 'lotofacil':
        rateio = { "pago_15": 0.0, "pago_14": 0.0, "pago_13": 30.0, "pago_12": 12.0, "pago_11": 6.0 }
        for faixa in lista:
            n = faixa.get('faixa') or faixa.get('numeroFaixa') 
            v = faixa.get('valorPremio', 0.0)
            if n == 1: rateio["pago_15"] = v
            elif n == 2: rateio["pago_14"] = v
            elif n == 3: rateio["pago_13"] = v
            elif n == 4: rateio["pago_12"] = v
            elif n == 5: rateio["pago_11"] = v
            
    elif loteria == 'maismilionaria':
        mapa_milionaria = {1: '6_2', 2: '6_1', 3: '5_2', 4: '5_1', 5: '4_2', 6: '4_1', 7: '3_2', 8: '3_1', 9: '2_2', 10: '2_1'}
        for faixa in lista:
            n = faixa.get('faixa') or faixa.get('numeroFaixa')
            v = faixa.get('valorPremio', 0.0)
            if n in mapa_milionaria: rateio[f"pago_{mapa_milionaria[n]}"] = v
            
    else:
        for faixa in lista:
            n = faixa.get('faixa') or faixa.get('numeroFaixa')
            v = faixa.get('valorPremio', 0.0)
            rateio[f"faixa_{n}"] = v
            acertos = faixa.get('numeroDeAcertos')
            if acertos is not None:
                rateio[f"pago_{acertos}"] = v
            else:
                desc = faixa.get('descricaoFaixa', '').lower()
                if 'acerto' in desc:
                    num = ''.join(filter(str.isdigit, desc))
                    if num: rateio[f"pago_{num}"] = v
    return rateio

# ==============================================================================
# 4. MOTOR MATEMÁTICO GG-456
# ==============================================================================
def gerar_estatisticas_gg456(historico_completo, config):
    if config.get('is_esportiva'):
        return [], [], [], []

    frequencia = {}
    for sorteio in historico_completo:
        if isinstance(sorteio, list):
            for dezena in sorteio:
                frequencia[dezena] = frequencia.get(dezena, 0) + 1
            
    # CORREÇÃO: .items() com M
    bolas_ordenadas = sorted(frequencia.items(), key=lambda x: x[1], reverse=True)
    bolas_quentes = [b[0] for b in bolas_ordenadas[:15]] if bolas_ordenadas else []
    bolas_atrasadas = [b[0] for b in bolas_ordenadas[-15:]] if bolas_ordenadas else []
    
    palpites = []
    palpites_trevos = []
    
    if config.get('is_supersete'):
        for _ in range(50):
            jogo = [str(random.randint(0,9)) for _ in range(7)]
            palpites.append(jogo)
        return palpites, [], bolas_quentes[:10], bolas_atrasadas[:10]

    total_globos = config['total_globos']
    bolas_por_jogo = config['bolas_jogo']
    
    todas_bolas = [str(i).zfill(2) for i in range(1, total_globos + 1)]
    quentes_pares = [n for n in bolas_quentes if int(n) % 2 == 0]
    quentes_impares = [n for n in bolas_quentes if int(n) % 2 != 0]

    for _ in range(50):
        jogo = set()
        meta_par = bolas_por_jogo // 2
        if bolas_por_jogo % 2 != 0: meta_par += random.choice([0, 1])
        
        while len([x for x in jogo if int(x) % 2 == 0]) < meta_par:
            opcoes = quentes_pares if random.random() < 0.6 and quentes_pares else [n for n in todas_bolas if int(n) % 2 == 0]
            jogo.add(random.choice(opcoes))
            
        while len(jogo) < bolas_por_jogo:
            opcoes = quentes_impares if random.random() < 0.6 and quentes_impares else [n for n in todas_bolas if int(n) % 2 != 0]
            jogo.add(random.choice(opcoes))
            
        palpites.append(sorted(list(jogo)))

    if config.get('tem_trevos'):
        for _ in range(50):
            t = random.sample(range(1, 7), 2)
            palpites_trevos.append([str(x).zfill(2) for x in sorted(t)])
            
    return palpites, palpites_trevos, bolas_quentes[:10], bolas_atrasadas[:10]

# ==============================================================================
# 5. O TRATOR DE DADOS E SINCRONIZADOR GLOBAL
# ==============================================================================
def buscar_dados_concurso(loteria, concurso_num=""):
    url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{loteria}/{concurso_num}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return None

def executar_robo():
    if not inicializar_firebase(): return
    ref = db.reference()

    print("🚜 INICIANDO O TRATOR DE LOTERIAS (VERSÃO CORRIGIDA 10.21)...")

    for loteria, cfg in LOTERIAS_CONFIG.items():
        print(f"\n========================================")
        print(f"📊 PROCESSANDO LOTERIA: {loteria.upper()}")
        
        dados_atuais = buscar_dados_concurso(loteria)
        if not dados_atuais or 'numero' not in dados_atuais:
            print(f"⚠️ API falhou para {loteria}. Pulando...")
            continue
            
        concurso_atual_caixa = int(dados_atuais['numero'])
        historico_ref = ref.child(f"Historico/{loteria}")
        ultimo_salvo_db = historico_ref.order_by_key().limit_to_last(1).get()
        
        ultimo_concurso_salvo = 0
        if ultimo_salvo_db:
            try: ultimo_concurso_salvo = int(list(ultimo_salvo_db.keys())[0])
            except: pass

        print(f"📍 Caixa: {concurso_atual_caixa} | 💾 Nuvem: {ultimo_concurso_salvo}")

        ultimo_pacote = dados_atuais

        if ultimo_concurso_salvo < concurso_atual_caixa:
            print(f"⬇️ Faltam {concurso_atual_caixa - ultimo_concurso_salvo} concursos. Iniciando Trator...")
            for num_concurso in range(ultimo_concurso_salvo + 1, concurso_atual_caixa + 1):
                dados = buscar_dados_concurso(loteria, num_concurso) if num_concurso != concurso_atual_caixa else dados_atuais
                if dados and 'numero' in dados:
                    concurso_str = str(dados['numero'])
                    pacote_hist = {
                        "concurso": concurso_str,
                        "data_sorteio": dados.get('dataApuracao', ''),
                        "rateio": extrair_rateio_completo(dados, loteria)
                    }
                    if cfg.get('is_esportiva'):
                        pacote_hist["partidas"] = dados.get('listaResultadoEquipeEsportiva', [])
                    else:
                        pacote_hist["dezenas"] = [str(n).zfill(2) for n in dados.get('listaDezenas', [])]
                    
                    historico_ref.child(concurso_str).set(pacote_hist)
                    ultimo_pacote = dados
                time.sleep(0.1) 
        else:
            print("✅ Histórico já está 100% atualizado!")

        try:
            concurso_txt = str(ultimo_pacote.get('numero'))
            res_atual = {
                "concurso": concurso_txt, 
                "data_sorteio": ultimo_pacote.get('dataApuracao', ''),
                "rateio": extrair_rateio_completo(ultimo_pacote, loteria)
            }
            if cfg.get('is_esportiva'):
                res_atual["partidas"] = ultimo_pacote.get('listaResultadoEquipeEsportiva', [])
            else:
                res_atual["dezenas"] = [str(n).zfill(2) for n in ultimo_pacote.get('listaDezenas', [])]

            ref.child(f"Resultados/{loteria}").set(res_atual)

            if not cfg.get('is_esportiva'):
                print(f"🧠 Calculando Estatísticas para {loteria}...")
                hist_db = historico_ref.get()
                matriz = []
                
                # TRAVA DEFINITIVA: Trata se veio como Lista ou Dicionário
                if isinstance(hist_db, dict):
                    for k, v in hist_db.items():
                        if isinstance(v, dict) and 'dezenas' in v: matriz.append(v['dezenas'])
                elif isinstance(hist_db, list):
                    for v in hist_db:
                        if isinstance(v, dict) and 'dezenas' in v: matriz.append(v['dezenas'])
                
                if not matriz: matriz = [res_atual.get("dezenas", [])]

                palpites, palpites_trevos, quentes, atrasadas = gerar_estatisticas_gg456(matriz, cfg)

                estatisticas = {
                    "ultimoSorteio": res_atual.get("dezenas", []),
                    "bolasQuentes": quentes,
                    "bolasAtrasadas": atrasadas,
                    "palpitesProntos": palpites,
                    "totalDeJogosAnalisados": len(matriz),
                    "horaSinc": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                }
                ref.child(cfg['stat_path']).set(estatisticas)
            print(f"✅ Feito! {loteria.upper()} online.")
        except Exception as e:
            print(f"❌ Erro ao finalizar {loteria}: {e}")

    print("\n🏁 TRABALHO CONCLUÍDO!")

if __name__ == "__main__":
    executar_robo()
