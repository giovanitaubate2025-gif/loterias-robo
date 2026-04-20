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
# 1. CONFIGURAÇÕES E CREDENCIAIS (INTEGRAÇÃO GITHUB ACTIONS)
# =========================================================================
# O GitHub Actions injetará a chave via segredo de ambiente
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

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://loterias.caixa.gov.br/",
    "Accept-Language": "pt-BR,pt;q=0.9"
}

# Criamos uma sessão para reaproveitar conexões e ser muito mais rápido
sessao = requests.Session()

# =========================================================================
# 2. FUNÇÕES DE APOIO E LIMPEZA (GAVETAS BLINDADAS)
# =========================================================================
def db_call(method, path, data=None):
    """Gerencia todas as chamadas ao Firebase com suporte a pacotes pesados."""
    url = f"{URL_FIREBASE}{path}.json?auth={SECRET_FIREBASE}"
    try:
        if method == "GET": return sessao.get(url, timeout=40).json()
        
        # Para envios, usamos compressão para evitar erros de pacotes grandes
        dados_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        if method == "PUT": return sessao.put(url, data=dados_json.encode('utf-8'), timeout=None)
        if method == "PATCH": return sessao.patch(url, data=dados_json.encode('utf-8'), timeout=None)
        if method == "DELETE": return sessao.delete(url, timeout=30)
    except Exception as e: 
        print(f"   [!] Erro de comunicação Firebase: {e}")
        return None

def limpar_chave(txt):
    """Firebase proíbe: . $ # [ ] /"""
    t = str(txt).strip()
    for c in ['.', '$', '#', '[', ']', '/']: t = t.replace(c, '')
    return t

def formatar_moeda(v):
    try: return f"R$ {float(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return "R$ 0,00"

def extrair_id_limpo(valor):
    """Extrai apenas números, ignorando traços, espaços ou lixo (Lotomania/Federal)."""
    match = re.search(r'\d+', str(valor))
    return str(int(match.group())) if match else None

# =========================================================================
# 3. O CÉREBRO DA IA (VARREDURA TOTAL E COOCORRÊNCIA)
# =========================================================================
def motor_ia_avancado(slug, config):
    nome = config["nome"]
    print(f"   🧠 IA: Iniciando varredura profunda de {nome}...")
    
    # Busca o histórico completo para análise (Regra da Varredura Total)
    hist = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome}")
    if not hist: return {}

    # Normalização dos dados históricos
    dados_h = hist if isinstance(hist, dict) else {str(i): v for i, v in enumerate(hist) if v}
    
    todas_dz = []
    matriz_afinidade = Counter() # Mapeia bolas que saem juntas
    
    # Processa cada concurso do histórico
    for concurso in dados_h.values():
        dzs = sorted(list(set(concurso.get("dezenas", [])))) # Deduplicação interna
        if not dzs: continue
        
        todas_dz.extend(dzs)
        # Calcula amizades entre bolas (Coocorrência)
        for i in range(len(dzs)):
            for j in range(i + 1, len(dzs)):
                matriz_afinidade[tuple(sorted((dzs[i], dzs[j])))] += 1

    freq = Counter(todas_dz)
    quentes = [x[0] for x in freq.most_common(25)]
    frias = [x[0] for x in freq.most_common()[:-10:-1]]
    
    # Geração dos 50 palpites blindados
    palpites = {}
    inicio = 0 if slug in ["lotomania", "supersete"] else 1
    fim = 99 if slug == "lotomania" else (9 if slug == "supersete" else config.get("total", 60))
    
    for i in range(1, 51):
        qtd = config["qtd"]
        # Mistura equilibrada entre quentes (40%) e tendências
        pool = set(random.sample(quentes, min(len(quentes), int(qtd * 0.4))))
        
        while len(pool) < qtd:
            num = random.randint(inicio, fim)
            pool.add(num)
            
        jg = sorted(list(pool))
        
        # Estruturação final conforme pedido
        if "trevos" in config:
            t = sorted(random.sample(range(1, 7), 2))
            palpites[f"jogo_{i:02d}"] = {"numeros": [f"{x:02d}" for x in jg], "trevos": [f"{x:02d}" for x in t]}
        else:
            palpites[f"jogo_{i:02d}"] = [f"{x:02d}" for x in jg]
            
    return palpites

# =========================================================================
# 4. AUDITORIA DE INTEGRIDADE (O FISCAL DE CAMPOS VAZIOS)
# =========================================================================
def banco_esta_incompleto(nome_jogo, conc_api):
    """
    Fiscaliza se o banco tem buracos (Data vazia ou Rateio ausente).
    Se estiver incompleto, força o robô a baixar tudo de novo.
    """
    hoje = db_call("GET", f"SORTEIO_DE_HOJE/{nome_jogo}")
    if not hoje: return True
    
    if str(hoje.get("numero")) != str(conc_api): return True
    
    # Checagem de integridade (conforme os prints do usuário)
    if not hoje.get("data") or hoje.get("data") == "" or not hoje.get("premiacoes"):
        print(f"   🔍 Auditoria: Detectado dado incompleto em {nome_jogo}. Forçando correção...")
        return True
        
    return False

# =========================================================================
# 5. CAPTURA TRIPLA REDUNDANTE (REDUÇÃO DE FALHAS)
# =========================================================================
def buscar_dados_loteria(slug):
    fontes = [
        (f"https://servicebus2.caixa.gov.br/loterias/api/{slug}", "CAIXA"),
        (f"https://brasilapi.com.br/api/loterias/v1/{slug}", "BRASIL API"),
        (f"https://loteriascaixa-api.herokuapp.com/api/{slug}/latest", "ESPELHO HEROKU")
    ]
    
    for url, nome_fonte in fontes:
        try:
            print(f"   🔎 Tentando {nome_fonte}...")
            res = sessao.get(url, headers=HEADERS, verify=False, timeout=20)
            if res.status_code == 200:
                d = res.json()
                # Normalização inteligente das diferentes APIs
                c = d.get("numero") or d.get("concurso")
                dt = d.get("dataApuracao") or d.get("data")
                dzs = d.get("listaDezenas") or d.get("dezenas")
                
                return {
                    "conc": str(c), "data": dt,
                    "dzs": [int(x) for x in dzs] if dzs else [],
                    "acum": d.get("acumulado") or d.get("acumulou"),
                    "arrec": d.get("valorArrecadado") or d.get("valor_arrecadado", 0),
                    "rates": d.get("listaRateioPremio") or d.get("premiacoes", []),
                    "p_data": d.get("dataPróximoConcurso") or d.get("data_proximo_concurso"),
                    "p_est": d.get("valorEstimadoPróximoConcurso") or d.get("valor_estimado_proximo_concurso", 0),
                    "extra": d.get("nomeTimeCoracaoMessorte") or d.get("time_do_coracao")
                }
        except: continue
    return None

# =========================================================================
# 6. ATUALIZAÇÃO SINCRONIZADA (O EFEITO DOMINÓ)
# =========================================================================
def efeito_domino(slug, config, d):
    nome = config["nome"]
    c_id = extrair_id_limpo(d["conc"])
    print(f"   🚀 Sincronizando: {nome} (Conc. {c_id})")

    # [GAVETA 1] SORTEIO_DE_HOJE: Sempre completo
    ficha_base = {
        "numero": c_id, "data": d["data"], "dezenas": d["dzs"],
        "acumulou": "SIM" if d["acum"] else "NÃO",
        "arrecadacao": d["arrec"], "premiacoes": d["rates"]
    }
    db_call("PUT", f"SORTEIO_DE_HOJE/{nome}", ficha_base)

    # [GAVETA 2] HISTORICOS_DE_SORTEIOS: Raiz > Nome > Numero
    db_call("PATCH", f"HISTORICOS_DE_SORTEIOS/{nome}", {c_id: ficha_base})

    # [GAVETA 3] PROXIMO_CONCURSO: Minimalista conforme pedido
    ficha_prox = {
        "Data do Próximo Sorteio": d["p_data"] or "A definir",
        "Estimativa de Prêmio": formatar_moeda(d["p_est"])
    }
    db_call("PUT", f"PROXIMO_CONCURSO/{nome}", ficha_prox)

    # [GAVETA 4] ESTATISTICAS: Faxina e Recálculo
    db_call("DELETE", f"ESTATISTICAS/{nome}")
    time.sleep(2) # Pausa para o banco respirar
    palpites_novos = motor_ia_avancado(slug, config)
    db_call("PUT", f"ESTATISTICAS/{nome}/jogos_prontos", palpites_novos)
    
    # [GAVETA 5] EVOLUCAO_DA_IA: Log de desempenho
    log = {"evento": f"Atualização Conc {c_id}", "timestamp": str(datetime.now())}
    db_call("PATCH", f"EVOLUCAO_DA_IA/{nome}", {c_id: log})

# =========================================================================
# 7. MOTOR DE EXECUÇÃO PRINCIPAL (CRONOGRAMA E PARADA SEGURA)
# =========================================================================
def main():
    # Ajuste para Horário de Brasília
    agora_br = datetime.now(timezone.utc) - timedelta(hours=3)
    hora = agora_br.hour
    print(f"=============================================================")
    print(f"🤖 ROBÔ LOTERIAS MASTER - {agora_br.strftime('%d/%m/%Y %H:%M')}")
    print(f"=============================================================")

    # Regra de Ouro: Parada Segura às 09:00
    if hora == 9:
        print("🌅 Repescagem das 09h. Se a Caixa não liberar, jogaremos a toalha.")

    # Processa cada jogo do dicionário
    for slug, config in JOGOS.items():
        print(f"\n[Fase de Busca] {config['nome']}")
        dados = buscar_dados_loteria(slug)
        
        if dados:
            # Auditoria de Integridade: Confere se o banco está vazio ou incompleto
            if banco_esta_incompleto(config["nome"], dados["conc"]):
                efeito_domino(slug, config, dados)
                print(f"   ✅ {config['nome']} Atualizado e Auditado!")
            else:
                print(f"   ✔️ {config['nome']} já está íntegro na nuvem.")
        else:
            print(f"   🚨 Erro Crítico: Falha nas 3 fontes para {config['nome']}.")

    print(f"\n🏁 CICLO DE PROCESSAMENTO FINALIZADO.")

if __name__ == "__main__":
    main()
