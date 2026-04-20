import requests
import json
import os
import random
import time
from datetime import datetime, timedelta, timezone
from collections import Counter

# Desativa avisos de SSL para garantir que o robô não pare em redes móveis
requests.packages.urllib3.disable_warnings()

# =========================================================================
# 1. CONFIGURAÇÕES E CREDENCIAIS
# =========================================================================
SECRET_FIREBASE = os.environ.get('FIREBASE_KEY', '7gS8ASjfG5ZGRVu55Yj5QRw58ZzLCMBzWFLOyrfd')
URL_FIREBASE = "https://canal-da-loterias-default-rtdb.firebaseio.com/"

JOGOS = {
    "megasena": {"nome": "MEGA-SENA", "qtd": 6, "total": 60},
    "lotofacil": {"nome": "LOTOFACIL", "qtd": 15, "total": 25},
    "quina": {"nome": "QUINA", "qtd": 5, "total": 80},
    "lotomania": {"nome": "LOTOMANIA", "qtd": 50, "total": 100},
    "timemania": {"nome": "TIMEMANIA", "qtd": 10, "total": 80},
    "diadesorte": {"nome": "DIA-DE-SORTE", "qtd": 7, "total": 31},
    "maismilionaria": {"nome": "MAIS-MILIONARIA", "qtd": 6, "total": 50, "trevos": 2},
    "duplasena": {"nome": "DUPLA-SENA", "qtd": 6, "total": 50},
    "supersete": {"nome": "SUPER-SETE", "qtd": 7, "total": 9, "tipo": "colunar"}
}

# Cabeçalhos para simular um navegador real e evitar bloqueios
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://loterias.caixa.gov.br/",
    "Accept-Language": "pt-BR,pt;q=0.9"
}

# =========================================================================
# 2. FUNÇÕES FIREBASE (AS GAVETAS BLINDADAS)
# =========================================================================
def db_call(method, path, data=None):
    url = f"{URL_FIREBASE}{path}.json?auth={SECRET_FIREBASE}"
    try:
        if method == "GET": return requests.get(url, timeout=20).json()
        if method == "PUT": return requests.put(url, json=data, timeout=20)
        if method == "PATCH": return requests.patch(url, json=data, timeout=20)
        if method == "DELETE": return requests.delete(url, timeout=20)
    except: return None

def formatar_moeda(v):
    try: return f"R$ {float(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return "R$ 0,00"

# =========================================================================
# 3. O CÉREBRO MATEMÁTICO (GERADOR DE 50 PALPITES)
# =========================================================================
def gerar_50_estatisticas(slug, config):
    nome = config["nome"]
    hist = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome}")
    
    # Tratamento de erro de estrutura do Firebase
    data_h = {}
    if isinstance(hist, list):
        data_h = {str(i): v for i, v in enumerate(hist) if v}
    elif isinstance(hist, dict):
        data_h = hist

    todas_dz = []
    for c in data_h.values():
        todas_dz.extend(c.get("dezenas", []))
    
    freq = Counter(todas_dz)
    quentes = [x[0] for x in freq.most_common(25)]
    
    inicio = 0 if slug in ["lotomania", "supersete"] else 1
    fim = 99 if slug == "lotomania" else (9 if slug == "supersete" else config.get("total", 60))
    
    resultado = {}
    for i in range(1, 51):
        qtd = config.get("qtd", 6)
        if config.get("tipo", "") == "colunar":
            jg = [random.randint(0, 9) for _ in range(7)]
        else:
            # Lógica: Mistura entre quentes (40%) e aleatórias
            pool = set(random.sample(quentes, min(len(quentes), int(qtd * 0.4))) if quentes else [])
            while len(pool) < qtd: pool.add(random.randint(inicio, fim))
            jg = sorted(list(pool))
        
        if "trevos" in config:
            t = sorted(random.sample(range(1, 7), 2))
            resultado[f"jogo_{i:02d}"] = {"numeros": [f"{x:02d}" for x in jg], "trevos": [f"{x:02d}" for x in t]}
        else:
            resultado[f"jogo_{i:02d}"] = [f"{x:02d}" for x in jg]
            
    return resultado

# =========================================================================
# 4. CAPTURA TRIPLA (CAIXA -> BRASIL API -> ESPELHO INDEPENDENTE)
# =========================================================================
def buscar_dados_loteria(slug):
    # Fonte 1: API Oficial da Caixa (ServiceBus)
    print(f"   🔎 Tentando Caixa Oficial...")
    try:
        url = f"https://servicebus2.caixa.gov.br/loterias/api/{slug}"
        res = requests.get(url, headers=HEADERS, verify=False, timeout=15)
        if res.status_code == 200:
            d = res.json()
            return {
                "conc": str(d.get("numero")), "data": d.get("dataApuracao"),
                "dzs": [int(x) for x in d.get("listaDezenas", [])],
                "acum": d.get("acumulado"), "arrec": d.get("valorArrecadado", 0),
                "rates": d.get("listaRateioPremio", []),
                "p_conc": str(d.get("numeroFinalConcursoPróximo")),
                "p_data": d.get("dataPróximoConcurso"),
                "p_est": d.get("valorEstimadoPróximoConcurso", 0),
                "t": d.get("dezenasSorteioOrdemCrescente", [])[6:] if slug == "maismilionaria" else None,
                "extra": d.get("nomeTimeCoracaoMessorte")
            }
    except: pass

    # Fonte 2: Brasil API (Fallback)
    print(f"   🔎 Tentando Brasil API...")
    try:
        url = f"https://brasilapi.com.br/api/loterias/v1/{slug}"
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            d = res.json()
            return {
                "conc": str(d.get("concurso")), "data": d.get("data"),
                "dzs": [int(x) for x in d.get("dezenas", [])],
                "acum": d.get("acumulou"), "arrec": d.get("valor_arrecadado", 0),
                "rates": d.get("premiacoes", []),
                "p_conc": str(int(d.get("concurso")) + 1),
                "p_data": d.get("data_proximo_concurso"),
                "p_est": d.get("valor_estimado_proximo_concurso", 0),
                "t": d.get("trevos") if slug == "maismilionaria" else None,
                "extra": d.get("time_do_coracao") or d.get("mes_da_sorte")
            }
    except: pass

    # Fonte 3: API de Espelho (Independente) - NOVO!
    print(f"   🔎 Tentando API de Espelho (Mirror)...")
    try:
        url = f"https://loteriascaixa-api.herokuapp.com/api/{slug}/latest"
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            d = res.json()
            return {
                "conc": str(d.get("concurso")), "data": d.get("data"),
                "dzs": [int(x) for x in d.get("dezenas", [])],
                "acum": d.get("acumulou"), "arrec": d.get("valor_arrecadado", 0),
                "rates": d.get("premiacoes", []),
                "p_conc": str(int(d.get("concurso")) + 1),
                "p_data": d.get("data_proximo_concurso"),
                "p_est": d.get("valor_estimado_proximo_concurso", 0),
                "t": d.get("trevos") if slug == "maismilionaria" else None,
                "extra": d.get("time_do_coracao") or d.get("mes_da_sorte")
            }
    except: pass
    
    return None

# =========================================================================
# 5. O EFEITO DOMINÓ (DISTRIBUIÇÃO EM 4 FRENTES)
# =========================================================================
def processar_vitoria(slug, config, d):
    nome = config["nome"]
    c = d["conc"]
    print(f"   🚀 ATUALIZANDO: {nome} (Conc. {c})")

    # [GAVETA 1] HOJE
    ficha_hoje = {
        "numero": c, "data": d["data"], "dezenas": d["dzs"],
        "acumulou": "SIM" if d["acum"] else "NÃO",
        "arrecadacao": d["arrec"], "premiacoes": d["rates"]
    }
    db_call("PUT", f"SORTEIO_DE_HOJE/{nome}", ficha_hoje)

    # [GAVETA 2] HISTÓRICO
    ficha_hist = ficha_hoje.copy()
    if d["t"]: ficha_hist["trevos"] = d["t"]
    if d["extra"]: ficha_hist["informacao_extra"] = d["extra"]
    db_call("PATCH", f"HISTORICOS_DE_SORTEIOS/{nome}", {c: ficha_hist})

    # [GAVETA 3] PRÓXIMO
    ficha_prox = {
        "numero_concurso": d["p_conc"], "data_proximo_sorteio": d["p_data"] or "A definir",
        "estimativa_premio": formatar_moeda(d["p_est"])
    }
    db_call("PUT", f"PROXIMO_CONCURSO/{nome}", ficha_prox)

    # [GAVETA 4] ESTATÍSTICAS (Faxina Completa)
    db_call("DELETE", f"ESTATÍSTICAS/{nome}")
    time.sleep(1)
    p = gerar_50_estatisticas(slug, config)
    db_call("PUT", f"ESTATÍSTICAS/{nome}/jogos_prontos", p)
    print(f"   ✅ Blindagem completa.")

# =========================================================================
# 6. EXECUÇÃO
# =========================================================================
def main():
    agora = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%d/%m/%Y %H:%M")
    print(f"=============================================================")
    print(f"🤖 ROBÔ NUVEM BLINDADA (TRIPLA FONTE) - {agora}")
    print(f"=============================================================")

    for slug, config in JOGOS.items():
        print(f"🔎 Verificando {config['nome']}...")
        dados = buscar_dados_loteria(slug)
        
        if dados:
            hoje_db = db_call("GET", f"SORTEIO_DE_HOJE/{config['nome']}")
            conc_banco = str(hoje_db.get("numero", "")) if hoje_db else ""
            
            if dados["conc"] != conc_banco:
                processar_vitoria(slug, config, dados)
            else:
                print(f"   ✔️ Sincronizado (Conc. {dados['conc']}).")
        else:
            print(f"   🚨 FALHA TOTAL em todas as fontes para {config['nome']}.")

    print(f"\n🏁 CICLO FINALIZADO.")

if __name__ == "__main__":
    main()
