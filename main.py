import requests
import json
import os
import random
from datetime import datetime, timedelta
from collections import Counter

# =========================================================================
# 1. CONFIGURAÇÕES E CREDENCIAIS
# =========================================================================
# O segredo vem do GitHub Actions ou da variável de ambiente
SECRET_FIREBASE = os.environ.get('FIREBASE_KEY', '7gS8ASjfG5ZGRVu55Yj5QRw58ZzLCMBzWFLOyrfd')
URL_FIREBASE = "https://canal-da-loterias-default-rtdb.firebaseio.com/"

# Configuração detalhada conforme pedido
JOGOS = {
    "megasena": {"nome": "MEGA-SENA", "total_bolas": 60, "sorteio_api": 6, "gerar_qtd": 6},
    "lotofacil": {"nome": "LOTOFACIL", "total_bolas": 25, "sorteio_api": 15, "gerar_qtd": 15},
    "quina": {"nome": "QUINA", "total_bolas": 80, "sorteio_api": 5, "gerar_qtd": 5},
    "lotomania": {"nome": "LOTOMANIA", "total_bolas": 100, "sorteio_api": 20, "gerar_qtd": 50},
    "timemania": {"nome": "TIMEMANIA", "total_bolas": 80, "sorteio_api": 7, "gerar_qtd": 10},
    "diadesorte": {"nome": "DIA-DE-SORTE", "total_bolas": 31, "sorteio_api": 7, "gerar_qtd": 7},
    "maismilionaria": {"nome": "MAIS-MILIONARIA", "total_bolas": 50, "sorteio_api": 6, "gerar_qtd": 6, "trevos": 2},
    "duplasena": {"nome": "DUPLA-SENA", "total_bolas": 50, "sorteio_api": 6, "gerar_qtd": 6},
    "supersete": {"nome": "SUPER-SETE", "total_bolas": 9, "sorteio_api": 7, "gerar_qtd": 7, "tipo": "colunar"},
    "loteca": {"nome": "LOTECA", "tipo": "esportiva", "jogos": 14},
    "lotogol": {"nome": "LOTOGOL", "tipo": "esportiva", "jogos": 5}
}

# =========================================================================
# 2. UTILITÁRIOS E CONEXÃO FIREBASE
# =========================================================================
def db_get(caminho):
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try:
        res = requests.get(url, timeout=20)
        return res.json() if res.status_code == 200 else None
    except: return None

def db_put(caminho, dados):
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try: requests.put(url, json=dados, timeout=20)
    except: pass

def db_patch(caminho, dados):
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try: requests.patch(url, json=dados, timeout=20)
    except: pass

def db_delete(caminho):
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try: requests.delete(url, timeout=20)
    except: pass

def formatar_moeda(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return "R$ 0,00"

def obter_data_brt():
    return (datetime.utcnow() - timedelta(hours=3)).strftime("%d/%m/%Y")

# =========================================================================
# 3. CÉREBRO DE ESTATÍSTICAS (GERADOR DE PALPITES)
# =========================================================================
def gerar_50_jogos(api_nome, config):
    nome_jogo = config["nome"]
    historico = db_get(f"HISTORICOS_DE_SORTEIOS/{nome_jogo}")
    
    # Se for esportiva ou sem histórico, gera aleatório inteligente
    if config.get("tipo") == "esportiva":
        palpites = {}
        opcoes = ["1", "X", "2"] if api_nome == "loteca" else ["0x0", "1x0", "2x1", "1x1", "2x2"]
        for i in range(1, 51):
            palpites[f"jogo_{i:02d}"] = [random.choice(opcoes) for _ in range(config["jogos"])]
        return palpites

    if not historico: return None

    # Lógica de Quentes e Atrasadas
    todas_dezenas = []
    inicio = 0 if api_nome in ["lotomania", "supersete"] else 1
    fim = 99 if api_nome == "lotomania" else (9 if api_nome == "supersete" else config["total_bolas"])
    
    concursos = sorted(historico.keys(), key=int)
    atrasos = {i: 0 for i in range(inicio, fim + 1)}

    for c in concursos:
        dzs = historico[c].get("dezenas", [])
        todas_dezenas.extend(dzs)
        for b in range(inicio, fim + 1):
            atrasos[b] = 0 if b in dzs else atrasos[b] + 1

    freq = Counter(todas_dezenas)
    quentes = [b[0] for b in freq.most_common(int(config["total_bolas"]*0.4))]
    atrasadas = sorted(atrasos, key=atrasos.get, reverse=True)[:int(config["total_bolas"]*0.3)]
    
    lista_final = {}
    for i in range(1, 51):
        if config.get("tipo") == "colunar": # Super Sete
            jogo = [random.randint(0, 9) for _ in range(7)]
        else:
            qtd = config["gerar_qtd"]
            # Mescla Quentes (40%), Atrasadas (30%) e Aleatórias (30%)
            comb = set(random.sample(quentes, min(len(quentes), int(qtd*0.4))))
            restante = [x for x in atrasadas if x not in comb]
            comb.update(random.sample(restante, min(len(restante), int(qtd*0.3))))
            
            todos_disp = [x for x in range(inicio, fim + 1) if x not in comb]
            comb.update(random.sample(todos_disp, qtd - len(comb)))
            jogo = sorted(list(comb))
        
        # Formatação de +Milionária com trevos
        if "trevos" in config:
            trevos = sorted(random.sample(range(1, 7), 2))
            lista_final[f"jogo_{i:02d}"] = {"numeros": [f"{x:02d}" for x in jogo], "trevos": [f"{x:02d}" for x in trevos]}
        else:
            lista_final[f"jogo_{i:02d}"] = [f"{x:02d}" for x in jogo]

    return lista_final

# =========================================================================
# 4. MOTOR DE ATUALIZAÇÃO (EFEITO DOMINÓ)
# =========================================================================
def efeito_domino(api_nome, config, dados_api):
    nome_jogo = config["nome"]
    num_conc = str(dados_api.get('concurso'))
    print(f"🚀 ATUALIZANDO: {nome_jogo} | Concurso: {num_conc}")

    # --- GAVETA 1: SORTEIO_DE_HOJE (Substituição) ---
    ficha = {
        "numero": num_conc,
        "data": str(dados_api.get('data'))[:10],
        "dezenas": dados_api.get('dezenas', []),
        "acumulou": "SIM" if dados_api.get('acumulou') else "NÃO",
        "premiacoes": dados_api.get('premiacoes', []),
        "arrecadacao": dados_api.get('valorArrecadado', 0)
    }
    # Campos Especiais
    if "trevos" in config: ficha["trevos"] = dados_api.get("trevos")
    if api_nome == "timemania": ficha["time_coracao"] = dados_api.get("time_do_coracao")
    if api_nome == "diadesorte": ficha["mes_sorte"] = dados_api.get("mes_da_sorte")

    db_put(f"SORTEIO_DE_HOJE/{nome_jogo}", ficha)

    # --- GAVETA 2: HISTORICOS_DE_SORTEIOS (Acumulativo) ---
    db_patch(f"HISTORICOS_DE_SORTEIOS/{nome_jogo}", {num_conc: ficha})

    # --- GAVETA 3: PROXIMO_CONCURSO (Limpeza e Troca) ---
    proximo = {
        "numero_concurso": str(int(num_conc) + 1),
        "data_proximo_sorteio": dados_api.get('data_proximo_concurso', 'A definir'),
        "estimativa_premio": formatar_moeda(dados_api.get('valor_estimado_proximo_concurso', 0))
    }
    db_put(f"PROXIMO_CONCURSO/{nome_jogo}", proximo)

    # --- GAVETA 4: ESTATÍSTICAS (Faxina e Recálculo) ---
    db_delete(f"ESTATISTICAS/{nome_jogo}") # Limpeza total antes
    novos_palpites = gerar_50_jogos(api_nome, config)
    if novos_palpites:
        db_put(f"ESTATISTICAS/{nome_jogo}/jogos_prontos", novos_palpites)
        print(f"📊 Estatísticas Recalculadas para {nome_jogo}")

# =========================================================================
# 5. EXECUÇÃO PRINCIPAL
# =========================================================================
def iniciar_robo():
    print(f"🕒 Início da Rodada: {obter_data_brt()}")
    
    for api_nome, config in JOGOS.items():
        if config.get("tipo") == "esportiva": continue # BrasilAPI foca em loterias numéricas

        try:
            res = requests.get(f"https://brasilapi.com.br/api/loterias/v1/{api_nome}", timeout=20)
            if res.status_code == 200:
                dados = res.json()
                conc_atual = str(dados.get('concurso'))
                
                # Verifica se já temos esse concurso no Hoje
                hoje = db_get(f"SORTEIO_DE_HOJE/{config['nome']}")
                if not hoje or str(hoje.get("numero")) != conc_atual:
                    efeito_domino(api_nome, config, dados)
                else:
                    print(f"✔️ {config['nome']} já está atualizado.")
        except Exception as e:
            print(f"⚠️ Erro ao processar {api_nome}: {e}")

    # Garante que ESTATISTICAS iniciais existam
    for api_nome, config in JOGOS.items():
        if not db_get(f"ESTATISTICAS/{config['nome']}/jogos_prontos"):
            print(f"🛠️ Criando Estatísticas Iniciais para {config['nome']}")
            p = gerar_50_jogos(api_nome, config)
            if p: db_put(f"ESTATISTICAS/{config['nome']}/jogos_prontos", p)

if __name__ == "__main__":
    iniciar_robo()
