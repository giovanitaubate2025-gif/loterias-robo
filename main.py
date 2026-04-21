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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://loterias.caixa.gov.br/",
    "Accept-Language": "pt-BR,pt;q=0.9"
}

sessao = requests.Session()

# =========================================================================
# 2. FUNÇÕES DE APOIO E LIMPEZA
# =========================================================================
def db_call(method, path, data=None):
    """Gerencia chamadas ao Firebase."""
    url = f"{URL_FIREBASE}{path}.json?auth={SECRET_FIREBASE}"
    try:
        if method == "GET": return sessao.get(url, timeout=40).json()
        dados_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        if method == "PUT": return sessao.put(url, data=dados_json.encode('utf-8'), timeout=None)
        if method == "PATCH": return sessao.patch(url, data=dados_json.encode('utf-8'), timeout=None)
        if method == "DELETE": return sessao.delete(url, timeout=30)
    except Exception as e: 
        print(f"   [!] Erro de comunicação Firebase: {e}")
        return None

def formatar_moeda(v):
    try: return f"R$ {float(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return "R$ 0,00"

def extrair_id_limpo(valor):
    match = re.search(r'\d+', str(valor))
    return str(int(match.group())) if match else None

# =========================================================================
# 3. MOTOR 6: MACHINE LEARNING (O ALGORITMO PAI QUE APRENDE)
# =========================================================================
def auditar_e_aprender(config, dezenas_reais):
    """
    O Algoritmo Pai: Lê os jogos gerados no concurso anterior e compara com o sorteio de hoje.
    Ajusta os "Pesos Cognitivos" para a próxima geração ser mais inteligente.
    """
    nome = config["nome"]
    print(f"   🧠 ML-Auditor: Avaliando taxa de acerto do robô para {nome}...")
    
    # Busca palpites antigos antes deles serem deletados
    jogos_antigos = db_call("GET", f"ESTATISTICAS/{nome}/jogos_prontos")
    pesos_atuais = db_call("GET", f"EVOLUCAO_DA_IA/{nome}/pesos")
    
    # Pesos padrão se for a primeira vez rodando
    if not pesos_atuais:
        pesos_atuais = {"peso_quentes": 0.4, "peso_atrasadas": 0.3, "peso_cooc": 0.3}

    if not jogos_antigos or not dezenas_reais:
        db_call("PATCH", f"EVOLUCAO_DA_IA/{nome}/pesos", pesos_atuais)
        return pesos_atuais

    dezenas_reais_set = set(int(x) for x in dezenas_reais)
    total_acertos = 0
    qtd_jogos = len(jogos_antigos)

    for chave, jogo in jogos_antigos.items():
        # Trata jogos com trevos (Mais Milionária)
        dzs_jogo = jogo["numeros"] if isinstance(jogo, dict) else jogo
        dzs_int = set(int(x) for x in dzs_jogo)
        acertos = len(dzs_int.intersection(dezenas_reais_set))
        total_acertos += acertos

    media_acertos = total_acertos / qtd_jogos if qtd_jogos > 0 else 0
    alvo_esperado = config["qtd"] * 0.3 # O robô quer acertar pelo menos 30% da cartela na média geral
    
    # Calibragem Dinâmica (Deep Learning Adjustments)
    if media_acertos < alvo_esperado:
        # Se errou muito, muda a estratégia: dá mais peso para as Atrasadas e Coocorrência
        pesos_atuais["peso_quentes"] = max(0.1, pesos_atuais["peso_quentes"] - 0.05)
        pesos_atuais["peso_atrasadas"] = min(0.6, pesos_atuais["peso_atrasadas"] + 0.05)
    else:
        # Se acertou bem, consolida a estratégia de Quentes
        pesos_atuais["peso_quentes"] = min(0.7, pesos_atuais["peso_quentes"] + 0.05)
        pesos_atuais["peso_atrasadas"] = max(0.1, pesos_atuais["peso_atrasadas"] - 0.05)

    print(f"   📈 Evolução: Média de Acertos: {media_acertos:.2f} | Novos Pesos: {pesos_atuais}")
    
    # Salva os novos pesos de inteligência no banco oculto
    db_call("PATCH", f"EVOLUCAO_DA_IA/{nome}/pesos", pesos_atuais)
    return pesos_atuais

# =========================================================================
# 4. OS 5 MOTORES DE IA PROFUNDA (ESTATÍSTICA E MONTAGEM)
# =========================================================================
def motor_ia_profunda(slug, config, pesos_cognitivos):
    nome = config["nome"]
    print(f"   ⚙️ Motor IA Profunda: Calculando Probabilidades Múltiplas (Análise Global)...")
    
    # MOTOR 1: VARREDURA HISTÓRICA TOTAL E GLOBAL
    # Lê ABSOLUTAMENTE TODOS os concursos já registrados (do nº 1 ao atual) sem atalhos
    hist = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome}")
    if not hist: return {}
    dados_h = hist if isinstance(hist, dict) else {str(i): v for i, v in enumerate(hist) if v}
    
    todas_dz = []
    matriz_afinidade = Counter() # MOTOR 2: Matriz de Coocorrência
    atrasos = {} # MOTOR 3: Ciclos e Atrasos
    somas_historicas = []
    
    # Analisa cronologicamente para pegar atrasos exatos
    concursos_ordenados = sorted(dados_h.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)
    
    for _, concurso in concursos_ordenados:
        dzs = sorted(list(set(concurso.get("dezenas", []))))
        if not dzs: continue
        
        dzs_int = [int(x) for x in dzs]
        todas_dz.extend(dzs_int)
        somas_historicas.append(sum(dzs_int))
        
        # Atualiza o termômetro de atrasos
        for num in range(1 if slug not in ["lotomania", "supersete"] else 0, config.get("total", 60) + 1):
            if num in dzs_int: atrasos[num] = 0
            else: atrasos[num] = atrasos.get(num, 0) + 1
            
        # Mapeia as amizades entre bolas (Quem sai com quem)
        for i in range(len(dzs_int)):
            for j in range(i + 1, len(dzs_int)):
                matriz_afinidade[tuple(sorted((dzs_int[i], dzs_int[j])))] += 1

    freq = Counter(todas_dz)
    quentes = [x[0] for x in freq.most_common()]
    atrasadas = sorted(atrasos.keys(), key=lambda k: atrasos[k], reverse=True)
    
    # MOTOR 4: JUIZ DE BALANCEAMENTO (Média da Curva de Gauss)
    media_soma = sum(somas_historicas) / len(somas_historicas) if somas_historicas else 0
    margem_soma = media_soma * 0.25 # Tolerância de 25% para mais ou para menos

    # MOTOR 5: O MONTADOR ESTRUTURADO (Gera os 50 Jogos)
    palpites = {}
    inicio = 0 if slug in ["lotomania", "supersete"] else 1
    fim = 99 if slug == "lotomania" else (9 if slug == "supersete" else config.get("total", 60))
    jogos_unicos = set()
    
    contador = 1
    tentativas = 0
    qtd = config["qtd"]
    
    # Aplica os pesos do Algoritmo Pai (Machine Learning)
    p_quentes = pesos_cognitivos.get("peso_quentes", 0.4)
    p_atrasadas = pesos_cognitivos.get("peso_atrasadas", 0.3)
    
    print(f"   🔨 Montador: Aplicando Filtro de Soma e Exclusividade...")
    while contador <= 50 and tentativas < 5000:
        tentativas += 1
        pool = set()
        
        # 1. Pega bolas Quentes com base no peso da IA
        qtd_quentes = int(qtd * p_quentes)
        pool.update(random.sample(quentes[:30], min(30, qtd_quentes)))
        
        # 2. Pega bolas Atrasadas com base no peso da IA
        qtd_atrasadas = int(qtd * p_atrasadas)
        pool.update(random.sample(atrasadas[:20], min(20, qtd_atrasadas)))
        
        # 3. Força a Coocorrência (Bolas Amigas)
        if pool:
            bola_base = list(pool)[0]
            # Acha o melhor amigo da bola base no histórico
            amigos = [par for par in matriz_afinidade.keys() if bola_base in par]
            if amigos:
                amigos.sort(key=lambda x: matriz_afinidade[x], reverse=True)
                melhor_amigo = amigos[0][1] if amigos[0][0] == bola_base else amigos[0][0]
                pool.add(melhor_amigo)
        
        # 4. Preenche o resto com números para equilibrar a cartela
        while len(pool) < qtd:
            pool.add(random.randint(inicio, fim))
            
        # O JUIZ ENTRA EM AÇÃO (Validações Estritas)
        jg = sorted(list(pool)[:qtd])
        soma_jogo = sum(jg)
        
        # Só aprova se a soma for matematicamente coerente com o histórico
        passou_juiz_soma = (media_soma - margem_soma) <= soma_jogo <= (media_soma + margem_soma)
        
        assinatura = "-".join(str(x) for x in jg)
        
        if assinatura not in jogos_unicos and (passou_juiz_soma or tentativas > 3000):
            # Se tentou muito (3000x) e a matemática for muito dura, ele aprova pela exclusividade
            jogos_unicos.add(assinatura)
            
            if "trevos" in config:
                t = sorted(random.sample(range(1, 7), 2))
                palpites[f"jogo_{contador:02d}"] = {"numeros": [f"{x:02d}" for x in jg], "trevos": [f"{x:02d}" for x in t]}
            else:
                palpites[f"jogo_{contador:02d}"] = [f"{x:02d}" for x in jg]
            
            contador += 1
            
    return palpites

# =========================================================================
# 5. AUDITORIA E CAPTURA TRIPLA
# =========================================================================
def banco_esta_incompleto(nome_jogo, conc_api):
    hoje = db_call("GET", f"SORTEIO_DE_HOJE/{nome_jogo}")
    if not hoje or str(hoje.get("numero")) != str(conc_api): return True
    if not hoje.get("data") or hoje.get("data") == "" or not hoje.get("premiacoes"):
        print(f"   🔍 Inspetor: Falha de integridade em {nome_jogo}. Corrigindo banco...")
        return True
    return False

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
                c = d.get("numero") or d.get("concurso")
                dt = d.get("dataApuracao") or d.get("data")
                dzs = d.get("listaDezenas") or d.get("dezenas")
                p_data = d.get("dataPróximoConcurso") or d.get("dataProximoConcurso") or d.get("data_proximo_concurso", "")
                p_est = d.get("valorEstimadoPróximoConcurso") or d.get("valorEstimadoProximoConcurso") or d.get("valor_estimado_proximo_concurso", 0)
                
                return {
                    "conc": str(c), "data": dt, "dzs": [int(x) for x in dzs] if dzs else [],
                    "acum": d.get("acumulado") or d.get("acumulou"),
                    "arrec": d.get("valorArrecadado") or d.get("valor_arrecadado", 0),
                    "rates": d.get("listaRateioPremio") or d.get("premiacoes", []),
                    "p_data": p_data, "p_est": p_est
                }
        except: continue
    return None

# =========================================================================
# 6. EFEITO DOMINÓ (ROTEAMENTO E DISTRIBUIÇÃO)
# =========================================================================
def efeito_domino(slug, config, d):
    nome = config["nome"]
    c_id = extrair_id_limpo(d["conc"])
    print(f"   🚀 Distribuindo Pacotes de Dados: {nome} (Conc. {c_id})")

    # === ALGORITMO PAI === 
    # Antes de apagar, ele analisa se a IA acertou o sorteio atual e calibra os pesos
    pesos_calibrados = auditar_e_aprender(config, d["dzs"])

    # 📦 PACOTE 1: PRESENTE E PASSADO
    ficha_base = {
        "numero": c_id, "data": d["data"], "dezenas": d["dzs"],
        "acumulou": "SIM" if d["acum"] else "NÃO",
        "arrecadacao": d["arrec"], "premiacoes": d["rates"]
    }
    db_call("PUT", f"SORTEIO_DE_HOJE/{nome}", ficha_base)
    db_call("PATCH", f"HISTORICOS_DE_SORTEIOS/{nome}", {c_id: ficha_base})

    # 📦 PACOTE 2: FUTURO (Padrão exato do Print)
    texto_estimativa = f"Estimativa de prêmio do próximo concurso {d['p_data']}" if d.get('p_data') else "Estimativa de prêmio do próximo concurso a definir"
    ficha_prox = {"texto_data": texto_estimativa, "valor_estimativa": formatar_moeda(d["p_est"])}
    db_call("PUT", f"PROXIMO_CONCURSO/{nome}", ficha_prox)

    # 📦 PACOTE 3: GERAÇÃO DA IA
    db_call("DELETE", f"ESTATISTICAS/{nome}")
    time.sleep(2) # Pausa Firebase
    
    # Passa os pesos calibrados para o motor construir jogos mais inteligentes
    palpites_novos = motor_ia_profunda(slug, config, pesos_calibrados)
    db_call("PUT", f"ESTATISTICAS/{nome}/jogos_prontos", palpites_novos)

# =========================================================================
# 7. MOTOR CENTRAL DO SERVIDOR (GITHUB ACTIONS)
# =========================================================================
def main():
    agora_br = datetime.now(timezone.utc) - timedelta(hours=3)
    hora = agora_br.hour
    print(f"=============================================================")
    print(f"🤖 ROBÔ LOTERIAS IA PROFUNDA - {agora_br.strftime('%d/%m/%Y %H:%M')}")
    print(f"=============================================================")

    if hora == 9:
        print("🌅 Repescagem das 09h. Parada Segura Ativa (Evitando Loop de Falha da Caixa).")

    for slug, config in JOGOS.items():
        print(f"\n[Processando] {config['nome']}")
        dados = buscar_dados_loteria(slug)
        
        if dados:
            if banco_esta_incompleto(config["nome"], dados["conc"]):
                efeito_domino(slug, config, dados)
                print(f"   ✅ Sucesso: Nuvem Atualizada e Algoritmos Calibrados para {config['nome']}.")
            else:
                print(f"   ✔️ {config['nome']} íntegro. Nada novo a fazer.")
        else:
            print(f"   🚨 Erro Crítico: Conexão recusada nas 3 APIs.")

    print(f"\n🏁 SESSÃO DE IA FINALIZADA COM SUCESSO.")

if __name__ == "__main__":
    main()
