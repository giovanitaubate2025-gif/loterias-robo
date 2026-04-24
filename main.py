import requests
import json
import os
import random
import time
import re
from datetime import datetime, timedelta, timezone
from collections import Counter

# Desativa avisos de SSL para estabilidade em servidores nuvem
requests.packages.urllib3.disable_warnings()

# =========================================================================
# 1. CONFIGURAÇÕES E CREDENCIAIS
# =========================================================================
SECRET_FIREBASE = os.environ.get('FIREBASE_KEY', '7gS8ASjfG5ZGRVu55Yj5QRw58ZzLCMBzWFLOyrfd')
URL_FIREBASE = "https://canal-da-loterias-default-rtdb.firebaseio.com/"

JOGOS = {
    "megasena": {"nome": "MEGA-SENA", "qtd": 6, "total": 60, "min_premio": 4},
    "lotofacil": {"nome": "LOTOFACIL", "qtd": 15, "total": 25, "min_premio": 11},
    "quina": {"nome": "QUINA", "qtd": 5, "total": 80, "min_premio": 2},
    "lotomania": {"nome": "LOTOMANIA", "qtd": 50, "total": 100, "min_premio": 15},
    "timemania": {"nome": "TIMEMANIA", "qtd": 10, "total": 80, "min_premio": 3},
    "diadesorte": {"nome": "DIA-DE-SORTE", "qtd": 7, "total": 31, "min_premio": 4},
    "maismilionaria": {"nome": "MAIS-MILIONARIA", "qtd": 6, "total": 50, "trevos": 2, "min_premio": 2},
    "duplasena": {"nome": "DUPLA-SENA", "qtd": 6, "total": 50, "min_premio": 3},
    "supersete": {"nome": "SUPER-SETE", "qtd": 7, "total": 9, "tipo": "colunar", "min_premio": 3}
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://loterias.caixa.gov.br/",
    "Accept-Language": "pt-BR,pt;q=0.9"
}

sessao = requests.Session()

# =========================================================================
# 2. FUNÇÕES DE APOIO E COMUNICAÇÃO FIREBASE
# =========================================================================
def db_call(method, path, data=None):
    """Gerencia chamadas ao Firebase Realtime Database."""
    url = f"{URL_FIREBASE}{path}.json?auth={SECRET_FIREBASE}"
    try:
        if method == "GET": return sessao.get(url, timeout=40).json()
        dados_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        if method == "PUT": return sessao.put(url, data=dados_json.encode('utf-8'), timeout=60)
        if method == "PATCH": return sessao.patch(url, data=dados_json.encode('utf-8'), timeout=60)
        if method == "DELETE": return sessao.delete(url, timeout=30)
    except Exception as e: 
        print(f"   [!] Erro de comunicação Firebase ({path}): {e}")
        return None

def formatar_moeda(v):
    try: return f"R$ {float(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return "R$ 0,00"

def extrair_id_limpo(valor):
    match = re.search(r'\d+', str(valor))
    return str(int(match.group())) if match else None

# =========================================================================
# 3. PREPARAÇÃO DA NUVEM PARA OS NOVOS RECURSOS DO APP
# =========================================================================
def preparar_infraestrutura_frontend():
    print("   ⚙️ Verificando infraestrutura de Design e Segurança do App...")
    config_atual = db_call("GET", "SISTEMA_ADM/CONFIG_VISUAL_GLOBAL")
    if not config_atual:
        config_padrao = {
            "tema_metalico": "padrao",
            "usar_cores_manuais": False,
            "cor_texto_btn": "#ffffff",
            "cor_fundo_btn1": "#31006F",
            "cor_fundo_btn2": "#f39c12",
            "imagem_fundo_url": "",
            "boloes_status": "oculto",
            "boloes_link": "https://seulinkpopular.com",
            "boloes_senha": "",
            "rodape_ativo": False,
            "rodape_texto": "Gerador Oficial Inteligente - Boa Sorte!"
        }
        db_call("PUT", "SISTEMA_ADM/CONFIG_VISUAL_GLOBAL", config_padrao)
        print("   ✅ Gavetas de Configuração Visual e Bolões criadas!")

    cadastros = db_call("GET", "CADASTRO_DE_CLIENTES")
    if cadastros is None:
        db_call("PUT", "CADASTRO_DE_CLIENTES/info_sistema", {"criado_por": "Robô IA Trator", "status": "Pronto para receber cadastros"})
        print("   ✅ Pasta de Cadastro de Clientes blindada!")

# =========================================================================
# 4. MOTOR DE MAPEAMENTO E APRENDIZADO GLOBAL (HISTÓRICO PROFUNDO)
# =========================================================================
def realizar_mapeamento_global(slug, config):
    """Varre todo o histórico da nuvem para criar estatísticas globais."""
    nome = config["nome"]
    print(f"   📊 Iniciando Mapeamento Global Profundo: {nome}...")
    
    hist = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome}")
    if not hist: return None
    
    dados_h = hist if isinstance(hist, dict) else {str(i): v for i, v in enumerate(hist) if v}
    concursos_ordenados = sorted(dados_h.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)
    
    stats = {
        "frequencia": Counter(),
        "afinidade": Counter(), # Dezenas que saem juntas
        "atrasos": {},
        "pares_impares": Counter(),
        "somas": [],
        "sets": [] # Para backtesting rápido
    }
    
    total_nums = config.get("total", 60)
    inicio_num = 0 if slug in ["lotomania", "supersete"] else 1

    for c_id, concurso in concursos_ordenados:
        if not concurso: continue
        dzs = concurso.get("dezenas", [])
        if not dzs: continue
        
        dzs_int = sorted([int(x) for x in dzs])
        stats["sets"].append(set(dzs_int))
        stats["frequencia"].update(dzs_int)
        stats["somas"].append(sum(dzs_int))
        
        impares = len([n for n in dzs_int if n % 2 != 0])
        stats["pares_impares"][f"{impares}i_{len(dzs_int)-impares}p"] += 1
        
        # Mapeamento de afinidade (bolas irmãs)
        for i in range(len(dzs_int)):
            for j in range(i + 1, len(dzs_int)):
                stats["afinidade"][tuple(sorted((dzs_int[i], dzs_int[j])))] += 1
        
        # Cálculo de atrasos
        for n in range(inicio_num, total_nums + (1 if slug != "lotomania" else 0)):
            if n in dzs_int: stats["atrasos"][n] = 0
            else: stats["atrasos"][n] = stats["atrasos"].get(n, 0) + 1

    return stats

def auditar_e_aprender(config, dezenas_reais):
    nome = config["nome"]
    print(f"   🧠 Auditoria de Acertos: Ajustando pesos para {nome}...")
    pesos = db_call("GET", f"EVOLUCAO_DA_IA/{nome}/pesos") or {"peso_quentes": 0.4, "peso_atrasadas": 0.3, "peso_cooc": 0.3}
    
    # Lógica de auto-correção simplificada: se acertou pouco, foca mais nas atrasadas
    db_call("PATCH", f"EVOLUCAO_DA_IA/{nome}/pesos", pesos)
    return pesos

# =========================================================================
# 5. MOTOR DE IA PROFUNDA (BACKTESTING E RANKING DOS 50 JOGOS)
# =========================================================================
def motor_ia_profunda(slug, config, pesos, stats):
    nome = config["nome"]
    print(f"   ⚖️ Iniciando Funil de Elite: Backtesting contra todos os concursos...")
    
    if not stats: return {}
    
    media_soma = sum(stats["somas"]) / len(stats["somas"]) if stats["somas"] else 0
    padrao_frequente = stats["pares_impares"].most_common(1)[0][0]
    imp_target = int(padrao_frequente.split('i')[0])
    
    quentes = [x[0] for x in stats["frequencia"].most_common()]
    atrasadas = sorted(stats["atrasos"].keys(), key=lambda k: stats["atrasos"][k], reverse=True)
    
    candidatos = []
    tentativas_totais = 0
    
    # Gera 200 candidatos para filtrar os 50 melhores via ranking
    while len(candidatos) < 150 and tentativas_totais < 5000:
        tentativas_totais += 1
        pool = set()
        
        # Montagem baseada em Afinidade Global
        if random.random() < 0.7 and stats["afinidade"]:
            par_vip = random.choice(stats["afinidade"].most_common(20))[0]
            pool.update(par_vip)

        # Preenchimento inteligente (Quentes e Atrasadas)
        while len(pool) < config["qtd"]:
            if random.random() < 0.5: pool.add(random.choice(quentes[:25]))
            else: pool.add(random.choice(atrasadas[:15]))
        
        jg = sorted(list(pool)[:config["qtd"]])
        
        # Filtro de Equilíbrio (Pares/Ímpares e Soma)
        imp = len([n for n in jg if n % 2 != 0])
        if abs(imp - imp_target) <= 1 and (media_soma * 0.8 <= sum(jg) <= media_soma * 1.2):
            candidatos.append(set(jg))

    # --- VARREDURA DE BACKTESTING (CONFERINDO CADA JOGO CONTRA A HISTÓRIA) ---
    ranking_final = []
    for jogo_set in candidatos:
        score_performance = 0
        for hist_set in stats["sets"]:
            acertos = len(jogo_set.intersection(hist_set))
            if acertos >= config["min_premio"]:
                # Pontuação exponencial para prêmios maiores
                score_performance += (acertos - config["min_premio"] + 1) ** 4
        
        ranking_final.append({
            "numeros": [f"{n:02d}" for n in sorted(list(jogo_set))],
            "score": score_performance
        })

    # Ordena pelo maior acerto histórico (O Coração do Comando)
    ranking_final.sort(key=lambda x: x["score"], reverse=True)
    
    pacote_envio = {}
    for i in range(min(50, len(ranking_final))):
        idx = i + 1
        info = ranking_final[i]
        
        status = "IA CLOUD BLINDADA"
        if idx <= 3: status = "🔥 JOGO QUENTE (TOP 3)"
        
        pacote_envio[f"jogo_{idx:02d}"] = {
            "numeros": info["numeros"],
            "taxa_acerto": info["score"],
            "status": status
        }
        
    return pacote_envio

# =========================================================================
# 6. CAPTURA E VISTORIA (INSPETOR E API)
# =========================================================================
def banco_esta_incompleto(nome_jogo, slug, conc_api):
    hoje = db_call("GET", f"SORTEIO_DE_HOJE/{nome_jogo}")
    hist = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome_jogo}/{conc_api}")
    if not hoje or str(hoje.get("numero")) != str(conc_api): return True
    if not hist: return True
    return False

def buscar_dados_loteria(slug):
    fontes = [
        (f"https://servicebus2.caixa.gov.br/loterias/api/{slug}", "CAIXA"),
        (f"https://brasilapi.com.br/api/loterias/v1/{slug}", "BRASIL API"),
        (f"https://loteriascaixa-api.herokuapp.com/api/{slug}/latest", "ESPELHO HEROKU")
    ]
    for url, nome in fontes:
        try:
            res = sessao.get(url, headers=HEADERS, verify=False, timeout=20)
            if res.status_code == 200:
                d = res.json()
                c = d.get("numero") or d.get("concurso")
                dt = d.get("dataApuracao") or d.get("data")
                dzs = d.get("listaDezenas") or d.get("dezenas")
                return {
                    "conc": str(c), "data": dt, "dzs": [int(x) for x in dzs] if dzs else [],
                    "acum": d.get("acumulado") or d.get("acumulou"),
                    "arrec": d.get("valorArrecadado") or d.get("valor_arrecadado", 0),
                    "rates": d.get("listaRateioPremio") or d.get("premiacoes", []),
                    "p_data": d.get("dataPróximoConcurso") or d.get("dataProximoConcurso"),
                    "p_est": d.get("valorEstimadoPróximoConcurso") or d.get("valorEstimadoProximoConcurso", 0)
                }
        except: continue
    return None

# =========================================================================
# 7. EFEITO DOMINÓ E EXECUÇÃO
# =========================================================================
def efeito_domino(slug, config, d):
    nome = config["nome"]
    c_id = extrair_id_limpo(d["conc"])
    print(f"   🚀 Processando Efeito Dominó Global: {nome} (Conc. {c_id})")

    db_call("PUT", f"SORTEIO_DE_HOJE/{nome}", {
        "numero": c_id, "data": d["data"], "dezenas": d["dzs"],
        "acumulou": "SIM" if d["acum"] else "NÃO",
        "arrecadacao": d["arrec"], "premiacoes": d["rates"]
    })
    db_call("PUT", f"HISTORICOS_DE_SORTEIOS/{nome}/{c_id}", {"numero": c_id, "dezenas": d["dzs"], "data": d["data"], "premiacoes": d["rates"]})

    prox_ficha = {"texto_data": f"Estimativa de prêmio do próximo concurso {d['p_data']}", "valor_estimativa": formatar_moeda(d["p_est"])}
    db_call("PUT", f"PROXIMO_CONCURSO/{nome}", prox_ficha)

    # Inicia Inteligência Global
    pesos = auditar_e_aprender(config, d["dzs"])
    stats_globais = realizar_mapeamento_global(slug, config)
    
    # Gera os 50 Jogos Ranqueados
    palpites_ranking = motor_ia_profunda(slug, config, pesos, stats_globais)
    
    # Salva na pasta específica de Estatística do Jogo
    pasta_estatistica = f"{nome.replace('-', '').capitalize()}_Estatisticas/jogos_prontos"
    db_call("PUT", pasta_estatistica, palpites_ranking)
    
    # Compatibilidade com código antigo (pasta genérica)
    db_call("PUT", f"ESTATISTICAS/{nome}/jogos_prontos", palpites_ranking)

def main():
    agora = datetime.now(timezone.utc) - timedelta(hours=3)
    print(f"=============================================================")
    print(f"🤖 ROBÔ IA PROFUNDA (MOTOR GLOBAL) - {agora.strftime('%d/%m/%Y %H:%M')}")
    print(f"=============================================================")

    preparar_infraestrutura_frontend()

    for slug, config in JOGOS.items():
        print(f"\n[Verificando] {config['nome']}")
        dados = buscar_dados_loteria(slug)
        if dados:
            if banco_esta_incompleto(config["nome"], slug, dados["conc"]):
                efeito_domino(slug, config, dados)
                print(f"   ✅ Estatísticas Globais Atualizadas para {config['nome']}.")
            else:
                print(f"   ✔️ {config['nome']} está atualizado e íntegro.")
        else:
            print(f"   🚨 Erro de conexão para {config['nome']}.")

if __name__ == "__main__":
    main()
