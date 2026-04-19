import os
import json
import requests
import random
import time
from datetime import datetime
from collections import Counter

# =========================================================================
# MOTOR GG-456: ARQUITETURA SERVERLESS (DIRETO PARA NUVEM)
# Implementação completa do Relatório Executivo
# =========================================================================

CHAVE_NUVEM = os.environ.get("FIREBASE_KEY", "{}")
URL_FIREBASE = "https://canal-da-loterias-default-rtdb.firebaseio.com/"
SECRET_FIREBASE = "7gS8ASjfG5ZGRVu55Yj5QRw58ZzLCMBzWFLOyrfd"

# 1. AS 13 MODALIDADES OFICIAIS
CONFIG_LOTERIAS = {
    'megasena': {'nome': 'Mega-Sena', 'bolas': 6, 'globo': 60, 'tipo': 'numeros'},
    'lotofacil': {'nome': 'Lotofácil', 'bolas': 15, 'globo': 25, 'tipo': 'numeros'},
    'quina': {'nome': 'Quina', 'bolas': 5, 'globo': 80, 'tipo': 'numeros'},
    'lotomania': {'nome': 'Lotomania', 'bolas': 20, 'globo': 100, 'tipo': 'numeros'},
    'duplasena': {'nome': 'Dupla Sena', 'bolas': 6, 'globo': 50, 'tipo': 'numeros'},
    'diadesorte': {'nome': 'Dia de Sorte', 'bolas': 7, 'globo': 31, 'tipo': 'numeros'},
    'timemania': {'nome': 'Timemania', 'bolas': 10, 'globo': 80, 'tipo': 'numeros'},
    'supersete': {'nome': 'Super Sete', 'bolas': 7, 'globo': 10, 'tipo': 'colunas'},
    'maismilionaria': {'nome': '+Milionária', 'bolas': 6, 'globo': 50, 'tipo': 'trevos'},
    'loteca': {'nome': 'Loteca', 'bolas': 14, 'globo': 3, 'tipo': 'esportiva'},
    # Lotogol descontinuada pela Caixa, mas mantida na estrutura
    'lotogol': {'nome': 'Lotogol', 'bolas': 5, 'globo': 0, 'tipo': 'esportiva'} 
}

def registrar_log(msg):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    print(f"[{agora}] {msg}")

# =========================================================================
# FIREBASE HELPERS
# =========================================================================
def ler_firebase(caminho):
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try:
        res = requests.get(url, timeout=10)
        return res.json() if res.status_code == 200 else None
    except:
        return None

def salvar_firebase(caminho, dados, metodo="put"):
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try:
        if metodo == "put":
            requests.put(url, json=dados, timeout=10)
        else:
            requests.patch(url, json=dados, timeout=10)
    except Exception as e:
        registrar_log(f"Erro Firebase ({caminho}): {e}")

# =========================================================================
# A CAÇADORA ANTI-R$ (Limpeza de Moeda)
# =========================================================================
def limpar_moeda(valor):
    if not valor: return 0.0
    if isinstance(valor, (int, float)): return float(valor)
    limpo = str(valor).replace('R$', '').replace('.', '').replace(',', '.').strip()
    try: return float(limpo)
    except: return 0.0

# =========================================================================
# BUSCADOR CAIXA / BRASIL API
# =========================================================================
def buscar_sorteio(api_nome, concurso=None):
    map_brasil = {
        'quina': 'quina', 'megasena': 'mega-sena', 'lotofacil': 'lotofacil',
        'lotomania': 'lotomania', 'timemania': 'timemania', 'duplasena': 'dupla-sena',
        'maismilionaria': 'mais-milionaria', 'diadesorte': 'dia-de-sorte',
        'supersete': 'super-sete', 'loteca': 'loteca'
    }
    sufixo = f"/{concurso}" if concurso else ""
    url_caixa = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{api_nome}{sufixo}"
    
    # 1. Tenta Caixa Oficial
    try:
        req = requests.get(url_caixa, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if req.status_code == 200:
            d = req.json()
            if d.get("numero"):
                return {
                    "concurso": d.get("numero"),
                    "data": d.get("dataApuracao"),
                    "dezenas": d.get("listaDezenas") or d.get("dezenas") or [],
                    "trevos_ou_time": d.get("listaDezenasSegundoSorteio") or d.get("nomeTimeCoracaoMesSorte") or "",
                    "acumulou": d.get("acumulado", False),
                    "proximo_premio": limpar_moeda(d.get("valorEstimadoProximoConcurso", 0)),
                    "data_proximo": d.get("dataProximoConcurso", "A definir"),
                    "rateio": d.get("listaRateioPremio", []),
                    "fonte": "CAIXA"
                }
    except:
        pass

    # 2. Tenta Brasil API (Fallback)
    if api_nome in map_brasil:
        url_brasil = f"https://brasilapi.com.br/api/loterias/v1/{map_brasil[api_nome]}{sufixo}"
        try:
            req = requests.get(url_brasil, timeout=10)
            if req.status_code == 200:
                b = req.json()
                if b.get("concurso"):
                    return {
                        "concurso": b.get("concurso"),
                        "data": b.get("data"),
                        "dezenas": b.get("dezenas", []),
                        "trevos_ou_time": b.get("trevos") or b.get("time_do_coracao") or b.get("mes_de_sorte") or "",
                        "acumulou": b.get("acumulou", False),
                        "proximo_premio": limpar_moeda(b.get("valor_estimado_proximo_concurso", 0)),
                        "data_proximo": b.get("data_proximo_concurso", "A definir"),
                        "rateio": [],
                        "fonte": "BRASIL_API"
                    }
        except:
            pass
    return None

# =========================================================================
# MOTOR ESTATÍSTICO (OS 50 JOGOS E BOLAS QUENTES)
# =========================================================================
def calcular_estatisticas_e_gerar_jogos(historico_dict, config, dezenas_atuais):
    if not historico_dict or config['tipo'] == 'esportiva':
        return {"mensagem": "Estatísticas não aplicáveis ou histórico vazio."}
    
    todas_dezenas_sorteadas = []
    atrasos = {}
    
    # Processa histórico (do mais antigo para o mais novo para calcular atraso real)
    concursos_ordenados = sorted(historico_dict.keys(), key=lambda x: int(x))
    total_concursos = len(concursos_ordenados)
    
    for idx, conc in enumerate(concursos_ordenados):
        dezenas = historico_dict[conc].get("dezenas", [])
        for d in dezenas:
            d_str = str(d).zfill(2)
            todas_dezenas_sorteadas.append(d_str)
            atrasos[d_str] = total_concursos - 1 - idx # Distância até o último
            
    # Frequência (Bolas Quentes)
    contagem = Counter(todas_dezenas_sorteadas)
    bolas_quentes = [b[0] for b in contagem.most_common(15)]
    bolas_atrasadas = sorted(atrasos.keys(), key=lambda k: atrasos[k], reverse=True)[:15]
    
    # Fabricar 50 Jogos Otimizados
    jogos = []
    max_bolas = config['bolas']
    globo = config['globo']
    universo = [str(i).zfill(2) for i in range(1 if config['nome'] != 'Lotomania' else 0, globo + (1 if config['nome'] != 'Lotomania' else 0))]
    
    for _ in range(50):
        jogo = set()
        # Mescla Bolas Quentes com Atrasadas e Aleatórias
        while len(jogo) < max_bolas:
            sorteio_tipo = random.random()
            if sorteio_tipo < 0.4 and bolas_quentes: # 40% chance Quentes
                jogo.add(random.choice(bolas_quentes))
            elif sorteio_tipo < 0.7 and bolas_atrasadas: # 30% chance Atrasadas
                jogo.add(random.choice(bolas_atrasadas))
            else: # 30% chance Aleatórias do Universo
                jogo.add(random.choice(universo))
                
        jogo_ordenado = sorted(list(jogo), key=lambda x: int(x))
        jogos.append("-".join(jogo_ordenado))
        
    return {
        "bolas_quentes": bolas_quentes,
        "bolas_atrasadas": bolas_atrasadas,
        "palpites_50_jogos": jogos,
        "analisados": total_concursos,
        "carimbo_tempo": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }

# =========================================================================
# O TRATOR DE HISTÓRICO E DISTRIBUIÇÃO NAS 5 PASTAS
# =========================================================================
def processar_loteria(api_nome, config):
    pasta_jogo = config['nome'].replace(" ", "_").replace("-", "").replace("+", "Mais").upper()
    registrar_log(f"Iniciando Motor para: {config['nome']}")
    
    # Busca sorteio atual na API
    atual = buscar_sorteio(api_nome)
    if not atual:
        registrar_log(f"Falha ao buscar {config['nome']}.")
        return None
        
    concurso_atual = str(atual["concurso"])
    
    # Verifica último salvo na nuvem
    salvo = ler_firebase(f"APP_CLIENTE/{pasta_jogo}/SORTEIO_DE_HOJE")
    concurso_salvo = str(salvo.get("concurso", "0")) if salvo else "0"
    
    # Se há atualização ou o histórico precisa ser forçado
    if int(concurso_atual) > int(concurso_salvo):
        registrar_log(f"Novo sorteio detectado ({concurso_atual}). Sincronizando...")
        
        # 1. Atualiza HISTÓRICO (O Trator Revo)
        historico = ler_firebase(f"APP_CLIENTE/{pasta_jogo}/HISTORICO_DE_SORTEIOS") or {}
        
        # Baixa os que faltam (Limita a 5 por execução para não travar o GitHub. 
        # Como roda todo dia, rapidamente preenche tudo se estiver vazio).
        faltantes = int(concurso_atual) - int(concurso_salvo)
        limite_busca = min(faltantes, 10) 
        
        for c in range(int(concurso_atual), int(concurso_atual) - limite_busca, -1):
            if str(c) not in historico:
                dados_c = buscar_sorteio(api_nome, c) if c != int(concurso_atual) else atual
                if dados_c:
                    historico[str(c)] = {"data": dados_c["data"], "dezenas": dados_c["dezenas"], "especial": dados_c.get("trevos_ou_time", "")}
                    salvar_firebase(f"APP_CLIENTE/{pasta_jogo}/HISTORICO_DE_SORTEIOS/{c}", historico[str(c)])
                    time.sleep(0.5) # Respiro para a API
        
        # 2. SORTEIO DE HOJE
        salvar_firebase(f"APP_CLIENTE/{pasta_jogo}/SORTEIO_DE_HOJE", {
            "concurso": atual["concurso"],
            "data": atual["data"],
            "dezenas": atual["dezenas"],
            "especial": atual.get("trevos_ou_time", "")
        })
        
        # 3. PROXIMO PREMIO (A Caçadora Anti-R$)
        salvar_firebase(f"APP_CLIENTE/{pasta_jogo}/PROXIMO_PREMIO", {
            "valor_puro": atual["proximo_premio"],
            "data_sorteio": atual["data_proximo"]
        })
        
        # 4. TABELA DE PREMIAÇÕES
        salvar_firebase(f"APP_CLIENTE/{pasta_jogo}/TABELA_DE_PREMIACOES", {
            "acumulou": "SIM" if atual["acumulou"] else "NÃO",
            "faixas": atual["rateio"]
        })
        
        # 5. ESTATÍSTICAS (Motor Estatístico)
        estats = calcular_estatisticas_e_gerar_jogos(historico, config, atual["dezenas"])
        salvar_firebase(f"APP_CLIENTE/{pasta_jogo}/ESTATISTICAS", estats)
        
        return atual
    else:
        registrar_log(f"{config['nome']} já está atualizado (Conc. {concurso_salvo}).")
        return atual # Retorna os dados para a Vitrine mesmo se não atualizou hoje

# =========================================================================
# ORQUESTRADOR E ABAS GLOBAIS
# =========================================================================
def iniciar_trator_nuvem():
    registrar_log("🚜 INICIANDO MOTOR GG-456 (100% NUVEM / SERVERLESS)")
    
    vitrine_app = {}
    premiacoes_globais = {}
    
    for api_nome, config in CONFIG_LOTERIAS.items():
        dados = processar_loteria(api_nome, config)
        
        if dados:
            nome_formatado = config['nome'].upper()
            
            # Alimentando Aba: Vitrine_App
            vitrine_app[nome_formatado] = {
                "proximo_premio": dados["proximo_premio"], # Valor puro para o app formatar
                "data": dados["data_proximo"],
                "status": "AGUARDANDO SORTEIO" if dados["acumulou"] else "SORTEIO REALIZADO",
                "hora_atualizacao": datetime.now().strftime("%H:%M:%S")
            }
            
            # Alimentando Aba: Premiações Globais (O Cofre)
            if dados["rateio"]:
                faixa_principal = dados["rateio"][0]
                premiacoes_globais[nome_formatado] = {
                    "concurso": dados["concurso"],
                    "data": dados["data"],
                    "ganhadores_principal": faixa_principal.get("numeroDeGanhadores", 0),
                    "valor_pago": limpar_moeda(faixa_principal.get("valorPremio", 0)),
                    "acumulou": "SIM" if dados["acumulou"] else "NÃO",
                    "estimativa_proximo": dados["proximo_premio"]
                }
            else:
                premiacoes_globais[nome_formatado] = {
                    "concurso": dados["concurso"],
                    "data": dados["data"],
                    "ganhadores_principal": 0,
                    "valor_pago": 0,
                    "acumulou": "SIM" if dados["acumulou"] else "NÃO",
                    "estimativa_proximo": dados["proximo_premio"]
                }
                
    # Salva as Abas Globais no Firebase
    registrar_log("Atualizando Vitrine App e Cofre de Premiações Globais...")
    salvar_firebase("SISTEMA_ADM/VITRINE_APP", vitrine_app)
    salvar_firebase("SISTEMA_ADM/PREMIACOES_GLOBAIS", premiacoes_globais)
    
    # Atualiza o Vigia Soberano (Status do Robô)
    salvar_firebase("SISTEMA_ADM/STATUS_MOTOR", {
        "status": "PLANTÃO CAÇA CONCLUÍDO COM SUCESSO",
        "ultima_ronda": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "arquitetura": "GG-456 Cloud Native Serverless"
    })
    
    registrar_log("🏆 TRATOR GG-456 FINALIZOU A VARREDURA. TUDO NA NUVEM!")

if __name__ == "__main__":
    iniciar_trator_nuvem()
