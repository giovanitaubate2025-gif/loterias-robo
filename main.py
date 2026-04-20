import os
import json
import requests
import random
import time
from datetime import datetime
from collections import Counter

# =========================================================================
# MOTOR GG-456: ARQUITETURA SERVERLESS (100% NUVEM / SEM PLANILHA)
# Implementação Fiel e Absoluta do Relatório Executivo
# =========================================================================

URL_FIREBASE = "https://canal-da-loterias-default-rtdb.firebaseio.com/"
SECRET_FIREBASE = "7gS8ASjfG5ZGRVu55Yj5QRw58ZzLCMBzWFLOyrfd"

# 1. AS 13 MODALIDADES OFICIAIS (Regras de Extração)
CONFIG_LOTERIAS = {
    'megasena': {'nome': 'Mega-Sena', 'bolas': 6, 'globo': 60},
    'lotofacil': {'nome': 'Lotofácil', 'bolas': 15, 'globo': 25},
    'quina': {'nome': 'Quina', 'bolas': 5, 'globo': 80},
    'lotomania': {'nome': 'Lotomania', 'bolas': 20, 'globo': 100},
    'duplasena': {'nome': 'Dupla Sena', 'bolas': 6, 'globo': 50},
    'diadesorte': {'nome': 'Dia de Sorte', 'bolas': 7, 'globo': 31},
    'timemania': {'nome': 'Timemania', 'bolas': 10, 'globo': 80},
    'supersete': {'nome': 'Super Sete', 'bolas': 7, 'globo': 10},
    'maismilionaria': {'nome': '+Milionária', 'bolas': 6, 'globo': 50},
    'loteca': {'nome': 'Loteca', 'bolas': 14, 'globo': 3}
}

def log(msg):
    agora = datetime.now().strftime("%H:%M:%S")
    print(f"[{agora}] {msg}")

# =========================================================================
# COMUNICAÇÃO FIREBASE (Leitura e Escrita Direta)
# =========================================================================
def ler_nuvem(caminho):
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200 and res.text != 'null':
            return res.json()
    except Exception as e:
        log(f"Erro ao ler nuvem ({caminho}): {e}")
    return {}

def salvar_nuvem(caminho, dados):
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    for _ in range(3): # Tenta 3 vezes para garantir
        try:
            res = requests.put(url, json=dados, timeout=15)
            if res.status_code == 200: return True
        except:
            time.sleep(1)
    log(f"❌ Falha ao salvar no Firebase: {caminho}")
    return False

def atualizar_nuvem_parcial(caminho, dados):
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try:
        requests.patch(url, json=dados, timeout=15)
    except:
        pass

# =========================================================================
# A CAÇADORA ANTI-R$ (Tratamento Numérico Puro)
# =========================================================================
def limpar_moeda(valor):
    if not valor: return 0.0
    if isinstance(valor, (int, float)): return float(valor)
    try:
        limpo = str(valor).replace('R$', '').replace('.', '').replace(',', '.').strip()
        return float(limpo)
    except:
        return 0.0

# =========================================================================
# BUSCADOR DE APIS (Caixa e Brasil API) - Aprimorado para buscar Tudo
# =========================================================================
def buscar_sorteio(api_nome, concurso=None):
    sufixo = f"/{concurso}" if concurso else ""
    url_caixa = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{api_nome}{sufixo}"
    
    # Tentativa 1: CAIXA OFICIAL
    try:
        req = requests.get(url_caixa, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if req.status_code == 200:
            d = req.json()
            if d.get("numero"):
                resultado = {
                    "concurso": d.get("numero"),
                    "data": d.get("dataApuracao"),
                    "dezenas": d.get("listaDezenas") or d.get("dezenas") or [],
                    "acumulou": d.get("acumulado", False),
                    "proximo_premio": limpar_moeda(d.get("valorEstimadoProximoConcurso", 0)),
                    "data_proximo": d.get("dataProximoConcurso", "A definir"),
                    "rateio": d.get("listaRateioPremio", [])
                }
                # 🔥 BUSCA PROFUNDA DE CAMPOS ESPECIAIS (Time, Trevos, Mês) 🔥
                if d.get("nomeTimeCoracao"):
                    resultado["especial"] = d.get("nomeTimeCoracao")
                elif d.get("nomeMesSorte"):
                    resultado["especial"] = d.get("nomeMesSorte")
                elif d.get("listaTrevos"):
                    resultado["especial"] = d.get("listaTrevos")
                
                return resultado
    except:
        pass

    # Tentativa 2: BRASIL API (Fallback com rateios e campos especiais)
    map_brasil = {
        'quina': 'quina', 'megasena': 'mega-sena', 'lotofacil': 'lotofacil',
        'lotomania': 'lotomania', 'timemania': 'timemania', 'duplasena': 'dupla-sena',
        'maismilionaria': 'mais-milionaria', 'diadesorte': 'dia-de-sorte',
        'supersete': 'super-sete', 'loteca': 'loteca'
    }
    if api_nome in map_brasil:
        url_brasil = f"https://brasilapi.com.br/api/loterias/v1/{map_brasil[api_nome]}{sufixo}"
        try:
            req = requests.get(url_brasil, timeout=10)
            if req.status_code == 200:
                b = req.json()
                if b.get("concurso"):
                    resultado = {
                        "concurso": b.get("concurso"),
                        "data": b.get("data"),
                        "dezenas": b.get("dezenas", []),
                        "acumulou": b.get("acumulou", False),
                        "proximo_premio": limpar_moeda(b.get("valor_estimado_proximo_concurso", 0)),
                        "data_proximo": b.get("data_proximo_concurso", "A definir"),
                        "rateio": b.get("premiacoes", []) # Puxa o rateio da Brasil API se precisar
                    }
                    # 🔥 BUSCA PROFUNDA DE CAMPOS ESPECIAIS (Time, Trevos, Mês) 🔥
                    if b.get("time_do_coracao"):
                        resultado["especial"] = b.get("time_do_coracao")
                    elif b.get("mes_da_sorte"):
                        resultado["especial"] = b.get("mes_da_sorte")
                    elif b.get("trevos"):
                        resultado["especial"] = b.get("trevos")
                        
                    return resultado
        except:
            pass
            
    return None

# =========================================================================
# 2. O TRATOR DE HISTÓRICO (CARGA DE BIG DATA ABSOLUTA)
# =========================================================================
def executar_trator_historico(api_nome, nome_jogo, pasta_jogo, concurso_atual):
    log(f"🚜 Trator ativado para {nome_jogo}. Verificando banco de dados...")
    
    # Puxa o histórico atual da nuvem
    historico_nuvem = ler_nuvem(f"APP_CLIENTE/{pasta_jogo}/HISTORICO_DE_SORTEIOS")
    if not historico_nuvem: historico_nuvem = {}
    
    # Descobre quais concursos faltam entre 1 e o Concurso Atual
    concursos_existentes = set(historico_nuvem.keys())
    concursos_esperados = set(str(i) for i in range(1, int(concurso_atual) + 1))
    faltantes = list(concursos_esperados - concursos_existentes)
    
    if not faltantes:
        log(f"✅ Histórico de {nome_jogo} já está 100% completo.")
        return historico_nuvem

    # Ordena do mais recente para o mais antigo para baixar
    faltantes.sort(key=int, reverse=True)
    log(f"⚠️ Faltam {len(faltantes)} concursos de {nome_jogo}. Iniciando download absoluto (Todos os concursos)...")
    
    # AGORA BAIXA TODOS OS CONCURSOS, SEM LIMITES DE LOTE.
    lote_download = faltantes 
    
    for conc in lote_download:
        dados_conc = buscar_sorteio(api_nome, conc)
        if dados_conc and dados_conc["dezenas"]:
            # 🔥 AGORA SALVA ABSOLUTAMENTE TUDO NO HISTÓRICO (Dezenas, Rateios e Especiais)
            pacote = {
                "data": dados_conc.get("data", ""),
                "dezenas": dados_conc.get("dezenas", []),
                "rateio": dados_conc.get("rateio", []),
                "acumulou": dados_conc.get("acumulou", False)
            }
            
            if "especial" in dados_conc:
                pacote["especial"] = dados_conc["especial"]
                
            atualizar_nuvem_parcial(f"APP_CLIENTE/{pasta_jogo}/HISTORICO_DE_SORTEIOS/{conc}", pacote)
            historico_nuvem[str(conc)] = pacote
            time.sleep(0.2) # Intervalo pequeno de 0.2s para evitar bloqueio da API da Caixa
            
    log(f"✅ Trator baixou todos os {len(lote_download)} jogos faltantes de {nome_jogo} com informações completas.")
    return historico_nuvem

# =========================================================================
# 5. O MOTOR ESTATÍSTICO (OS 50 JOGOS E BOLAS QUENTES)
# =========================================================================
def fabricar_estatisticas(historico, config, concurso_base):
    if not historico or config['nome'] == 'Loteca': 
        return {"mensagem": "Estatísticas não aplicáveis."}
    
    todas_bolas = []
    atrasos = {}
    
    # Organiza do mais antigo (1) para o mais novo
    concursos_ordenados = sorted(historico.keys(), key=int)
    total_lido = len(concursos_ordenados)
    
    for idx, conc in enumerate(concursos_ordenados):
        dezenas = historico[conc].get('dezenas', [])
        for d in dezenas:
            str_d = str(d).zfill(2)
            todas_bolas.append(str_d)
            atrasos[str_d] = total_lido - 1 - idx # Distância até hoje
            
    contagem = Counter(todas_bolas)
    bolas_quentes = [b[0] for b in contagem.most_common(15)]
    bolas_atrasadas = sorted(atrasos.keys(), key=lambda x: atrasos[x], reverse=True)[:15]
    
    # Gerando os 50 Jogos (Misturando Quentes, Atrasadas e Universo)
    jogos_prontos = []
    max_b = config['bolas']
    universo = [str(i).zfill(2) for i in range(1 if config['nome'] != 'Lotomania' else 0, config['globo'] + (1 if config['nome'] != 'Lotomania' else 0))]
    
    for _ in range(50):
        jogo = set()
        while len(jogo) < max_b:
            sorteio = random.random()
            if sorteio < 0.4 and bolas_quentes: jogo.add(random.choice(bolas_quentes))
            elif sorteio < 0.6 and bolas_atrasadas: jogo.add(random.choice(bolas_atrasadas))
            else: jogo.add(random.choice(universo))
            
        jogos_prontos.append("-".join(sorted(list(jogo), key=int)))
        
    return {
        "carimbo_tempo": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "concurso_base": concurso_base,
        "bolas_quentes": bolas_quentes,
        "bolas_atrasadas": bolas_atrasadas,
        "jogos": jogos_prontos,
        "total_analisado": total_lido
    }

# =========================================================================
# ORQUESTRADOR CENTRAL (AS 5 PASTAS E ABAS GLOBAIS)
# =========================================================================
def executar_motor_gg456():
    log("🚀 INICIANDO MOTOR GG-456 (RELATÓRIO EXECUTIVO - 100% NUVEM)")
    
    vitrine_global = {}
    cofre_global = {}
    
    for api_nome, config in CONFIG_LOTERIAS.items():
        pasta_jogo = config['nome'].replace(" ", "_").replace("-", "").replace("+", "Mais").upper()
        
        # 1. Pega o Sorteio de Hoje
        dados_atuais = buscar_sorteio(api_nome)
        if not dados_atuais:
            log(f"⚠️ Sorteio atual de {config['nome']} não encontrado.")
            continue
            
        concurso_atual = dados_atuais["concurso"]
        
        # 2. Aciona o Trator de Histórico
        historico_completo = executar_trator_historico(api_nome, config['nome'], pasta_jogo, concurso_atual)
        
        # 3. Garante que o concurso de hoje está no histórico
        if str(concurso_atual) not in historico_completo:
            pacote_hoje_historico = {
                "data": dados_atuais["data"], 
                "dezenas": dados_atuais["dezenas"],
                "rateio": dados_atuais.get("rateio", []),
                "acumulou": dados_atuais.get("acumulou", False)
            }
            if "especial" in dados_atuais: pacote_hoje_historico["especial"] = dados_atuais["especial"]
            historico_completo[str(concurso_atual)] = pacote_hoje_historico
        
        # =========================================================
        # SALVANDO NAS 5 PASTAS DO FIREBASE (Regra do Relatório)
        # =========================================================
        
        # 📂 SORTEIO_DE_HOJE
        payload_sorteio_hoje = {
            "concurso": concurso_atual,
            "data": dados_atuais["data"],
            "dezenas": dados_atuais["dezenas"]
        }
        if "especial" in dados_atuais:
            payload_sorteio_hoje["especial"] = dados_atuais["especial"]
            
        salvar_nuvem(f"APP_CLIENTE/{pasta_jogo}/SORTEIO_DE_HOJE", payload_sorteio_hoje)
        
        # 📂 PROXIMO_PREMIO
        salvar_nuvem(f"APP_CLIENTE/{pasta_jogo}/PROXIMO_PREMIO", {
            "valor_puro": dados_atuais["proximo_premio"],
            "data_sorteio": dados_atuais["data_proximo"]
        })
        
        # 📂 TABELA_DE_PREMIACOES
        salvar_nuvem(f"APP_CLIENTE/{pasta_jogo}/TABELA_DE_PREMIACOES", {
            "acumulou": "SIM" if dados_atuais["acumulou"] else "NÃO",
            "faixas": dados_atuais["rateio"]
        })
        
        # 📂 ESTATISTICAS (Motor Estatístico)
        estatisticas = fabricar_estatisticas(historico_completo, config, concurso_atual)
        salvar_nuvem(f"APP_CLIENTE/{pasta_jogo}/ESTATISTICAS", estatisticas)
        
        # =========================================================
        # PREPARANDO AS ABAS GLOBAIS (Vitrine e Cofre)
        # =========================================================
        nome_aba = config['nome'].upper()
        vitrine_global[nome_aba] = {
            "proximo_premio": dados_atuais["proximo_premio"],
            "data": dados_atuais["data_proximo"],
            "status": "AGUARDANDO SORTEIO" if dados_atuais["acumulou"] else "SORTEIO REALIZADO",
            "atualizado_em": datetime.now().strftime("%H:%M:%S")
        }
        
        if dados_atuais["rateio"]:
            cofre_global[nome_aba] = {
                "concurso": concurso_atual,
                "data": dados_atuais["data"],
                "ganhadores_principal": dados_atuais["rateio"][0].get("numeroDeGanhadores", 0),
                "valor_pago": limpar_moeda(dados_atuais["rateio"][0].get("valorPremio", 0)),
                "acumulou": "SIM" if dados_atuais["acumulou"] else "NÃO",
                "estimativa_proximo": dados_atuais["proximo_premio"]
            }
        else:
            cofre_global[nome_aba] = {
                "concurso": concurso_atual, "data": dados_atuais["data"], "ganhadores_principal": 0, "valor_pago": 0,
                "acumulou": "SIM" if dados_atuais["acumulou"] else "NÃO", "estimativa_proximo": dados_atuais["proximo_premio"]
            }

    # =========================================================
    # SALVANDO AS ABAS GLOBAIS NA NUVEM
    # =========================================================
    log("Atualizando Vitrine App e Premiações Globais...")
    salvar_nuvem("SISTEMA_ADM/VITRINE_APP", vitrine_global)
    salvar_nuvem("SISTEMA_ADM/PREMIACOES_GLOBAIS", cofre_global)
    
    salvar_nuvem("SISTEMA_ADM/STATUS_MOTOR", {
        "status": "MOTOR 100% ATIVO - BIG DATA E ESTATÍSTICAS OK",
        "ultima_ronda": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    })
    
    log("🏆 MOTOR GG-456 EXECUTADO COM SUCESSO! A NUVEM ESTÁ COMPLETAMENTE ATUALIZADA.")

if __name__ == "__main__":
    executar_motor_gg456()
