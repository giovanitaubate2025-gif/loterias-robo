import requests
import json
import os
import random
import time
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict

# Desativa avisos de SSL (Garante que o robô rode liso no GitHub Actions)
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
        # Timeout de 45s para garantir leitura de TODO o histórico (do 1 ao atual)
        if method == "GET": return requests.get(url, timeout=45).json()
        if method == "PUT": return requests.put(url, json=data, timeout=45)
        if method == "PATCH": return requests.patch(url, json=data, timeout=45)
        if method == "DELETE": return requests.delete(url, timeout=45)
    except Exception as e: 
        print(f"   [!] Erro de conexão com Firebase ({method} em {path}): {e}")
        return None

def formatar_moeda(v):
    try: return f"R$ {float(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return "R$ 0,00"

# =========================================================================
# 3. INTELIGÊNCIA ARTIFICIAL: MACHINE LEARNING & ESTATÍSTICA PROFUNDA
# =========================================================================
def auditar_e_aprender(nome, jogos_antigos, dezenas_sorteadas):
    """ AUDITORIA DA IA: Avalia se os palpites antigos acertaram o sorteio novo """
    pesos_atuais = db_call("GET", f"EVOLUCAO_DA_IA/{nome}/pesos")
    if not pesos_atuais:
        pesos_atuais = {"peso_quentes": 1.0, "peso_atrasadas": 1.0, "peso_frias": 1.0, "peso_cooc": 1.0}
    
    if not jogos_antigos: return pesos_atuais

    acertos_totais = 0
    sorteio_set = set(dezenas_sorteadas)
    
    for _, jogo in jogos_antigos.items():
        numeros = jogo["numeros"] if isinstance(jogo, dict) and "numeros" in jogo else jogo
        num_ints = [int(n) for n in numeros]
        acertos_totais += len(set(num_ints).intersection(sorteio_set))
        
    media_acertos = acertos_totais / len(jogos_antigos)
    print(f"   🧠 [Machine Learning] Média de Acertos passada: {media_acertos:.2f} dezenas.")
    
    # Se o desempenho foi fraco, a IA recalibra os multiplicadores
    if media_acertos < (len(dezenas_sorteadas) * 0.3):
        pesos_atuais["peso_quentes"] = round(random.uniform(0.5, 2.0), 2)
        pesos_atuais["peso_atrasadas"] = round(random.uniform(0.5, 2.0), 2)
        pesos_atuais["peso_frias"] = round(random.uniform(0.5, 1.5), 2)
        pesos_atuais["peso_cooc"] = round(random.uniform(0.5, 2.0), 2)
        print(f"   🔄 [Machine Learning] IA reajustou os pesos matemáticos para evoluir.")
    
    db_call("PUT", f"EVOLUCAO_DA_IA/{nome}/pesos", pesos_atuais)
    return pesos_atuais

def gerar_jogos_profundos(slug, config, pesos_ia):
    nome = config["nome"]
    hist = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome}")
    
    # Processa histórico (Aceita Lista ou Dicionário)
    data_h = {}
    if isinstance(hist, list):
        data_h = {str(i): v for i, v in enumerate(hist) if v}
    elif isinstance(hist, dict):
        data_h = hist

    concursos_ordenados = sorted(data_h.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)
    historico_puro = [c[1].get("dezenas", []) for c in concursos_ordenados if "dezenas" in c[1]]
    
    if not historico_puro: return {}

    inicio = 0 if slug in ["lotomania", "supersete"] else 1
    fim = 99 if slug == "lotomania" else (9 if slug == "supersete" else config.get("total", 60))
    
    # --- MAPEAMENTO DE BIG DATA ---
    frequencias = Counter()
    atrasos = {n: 0 for n in range(inicio, fim + 1)}
    cooc = defaultdict(Counter) # Coocorrência (Bolas que saem juntas)
    somas_historicas = []
    
    for sorteio in historico_puro:
        somas_historicas.append(sum(sorteio))
        for n in atrasos.keys(): atrasos[n] += 1
        for i in range(len(sorteio)):
            dezena = sorteio[i]
            frequencias[dezena] += 1
            atrasos[dezena] = 0
            if config.get("tipo") != "colunar":
                for j in range(i+1, len(sorteio)):
                    d1, d2 = sorteio[i], sorteio[j]
                    cooc[d1][d2] += 1
                    cooc[d2][d1] += 1

    todas_por_freq = frequencias.most_common()
    top_quentes = [x[0] for x in todas_por_freq[:int(len(todas_por_freq)*0.3)]]
    top_frias = [x[0] for x in todas_por_freq[-int(len(todas_por_freq)*0.3):]]
    top_atrasadas = sorted(atrasos.keys(), key=lambda k: atrasos[k], reverse=True)[:15]

    # --- FILTROS COMPORTAMENTAIS (SOMA E PARIDADE) ---
    media_soma = sum(somas_historicas) / len(somas_historicas)
    desvio_soma = (sum((s - media_soma)**2 for s in somas_historicas) / len(somas_historicas))**0.5
    limite_min_soma = media_soma - (desvio_soma * 1.5)
    limite_max_soma = media_soma + (desvio_soma * 1.5)

    ultimo_jogo = historico_puro[-1]
    pares_ultimo = sum(1 for d in ultimo_jogo if d % 2 == 0)
    qtd = config.get("qtd", 6)
    meta_pares = (qtd // 2) + (1 if pares_ultimo < (qtd // 2) else -1) # Alternância Dinâmica

    resultado_final = {}
    for i in range(1, 51):
        jogo_valido = False
        tentativas = 0
        
        while not jogo_valido:
            if config.get("tipo") == "colunar":
                jg = [random.randint(0, 9) for _ in range(7)]
                jogo_valido = True
            else:
                jg_set = set()
                # Escolha inicial baseada nos pesos da IA
                roleta = random.random()
                if roleta < (0.4 * pesos_ia["peso_quentes"]) and top_quentes: 
                    jg_set.add(random.choice(top_quentes))
                elif roleta < (0.7 * pesos_ia["peso_atrasadas"]) and top_atrasadas: 
                    jg_set.add(random.choice(top_atrasadas))
                elif top_frias: 
                    jg_set.add(random.choice(top_frias))
                else:
                    jg_set.add(random.randint(inicio, fim))
                
                # Preenchimento Mapeado (Afinidade)
                while len(jg_set) < qtd:
                    candidatos = []
                    for bola in jg_set:
                        amigos = [x[0] for x in cooc[bola].most_common(5)]
                        candidatos.extend(amigos)
                    
                    if candidatos and random.random() < (0.6 * pesos_ia["peso_cooc"]):
                        jg_set.add(random.choice(candidatos))
                    else:
                        jg_set.add(random.randint(inicio, fim))
                
                jg = sorted(list(jg_set))
                
                # JUIZ FINAL: Aprovação de Soma e Paridade
                soma_jogo = sum(jg)
                pares_jogo = sum(1 for d in jg if d % 2 == 0)
                
                passou_soma = limite_min_soma <= soma_jogo <= limite_max_soma
                passou_paridade = abs(pares_jogo - meta_pares) <= 2
                
                if passou_soma and passou_paridade:
                    jogo_valido = True
                else:
                    tentativas += 1
                    if tentativas > 150: jogo_valido = True # Condição de segurança contra loop

        # Formatação JSON exigida
        if "trevos" in config:
            t = sorted(random.sample(range(1, 7), 2))
            resultado_final[f"jogo_{i:02d}"] = {"numeros": [f"{x:02d}" for x in jg], "trevos": [f"{x:02d}" for x in t]}
        else:
            resultado_final[f"jogo_{i:02d}"] = [f"{x:02d}" for x in jg]
            
    return resultado_final

# =========================================================================
# 4. CAPTURA TRIPLA REDUNDANTE (CAIXA -> BRASIL API -> ESPELHO)
# =========================================================================
def buscar_dados_loteria(slug):
    fontes = [
        ("Caixa Oficial", f"https://servicebus2.caixa.gov.br/loterias/api/{slug}"),
        ("Brasil API", f"https://brasilapi.com.br/api/loterias/v1/{slug}"),
        ("API Espelho", f"https://loteriascaixa-api.herokuapp.com/api/{slug}/latest")
    ]
    
    for nome_fonte, url in fontes:
        print(f"   🔎 Tentando {nome_fonte}...")
        try:
            res = requests.get(url, headers=HEADERS, verify=False, timeout=15)
            if res.status_code == 200:
                d = res.json()
                concurso = str(d.get("numero") or d.get("concurso"))
                if not concurso or concurso == "None": continue

                return {
                    "conc": concurso,
                    "data": d.get("dataApuracao") or d.get("data"),
                    "dzs": [int(x) for x in (d.get("listaDezenas") or d.get("dezenas") or [])],
                    "acum": d.get("acumulado") or d.get("acumulou"),
                    "arrec": d.get("valorArrecadado") or d.get("valor_arrecadado") or 0,
                    "rates": d.get("listaRateioPremio") or d.get("premiacoes") or [],
                    "p_conc": str(d.get("numeroFinalConcursoPróximo") or (int(concurso) + 1)),
                    "p_data": d.get("dataPróximoConcurso") or d.get("data_proximo_concurso") or "A definir",
                    "p_est": d.get("valorEstimadoPróximoConcurso") or d.get("valor_estimado_proximo_concurso") or 0,
                    "trevos": (d.get("dezenasSorteioOrdemCrescente", [])[6:] if slug == "maismilionaria" and d.get("dezenasSorteioOrdemCrescente") else d.get("trevos")),
                    "time": d.get("nomeTimeCoracaoMessorte") or d.get("time_do_coracao"),
                    "mes": d.get("nomeTimeCoracaoMessorte") or d.get("mes_da_sorte")
                }
        except: pass
    return None

# =========================================================================
# 5. O EFEITO DOMINÓ (REPOSIÇÃO DAS 4 GAVETAS DE FORMA ESTRITA)
# =========================================================================
def processar_vitoria(slug, config, d):
    nome = config["nome"]
    c = d["conc"]
    print(f"   🚀 EFEITO DOMINÓ ATIVADO: {nome} (Conc. {c})")

    # 📁 GAVETA 1: SORTEIO DE HOJE (O Radar)
    ficha_hoje = {
        "numero": c, "data": d["data"], "dezenas": d["dzs"],
        "acumulou": "SIM" if d["acum"] else "NÃO",
        "arrecadacao": formatar_moeda(d["arrec"]), "premiacoes": d["rates"]
    }
    db_call("PUT", f"SORTEIO_DE_HOJE/{nome}", ficha_hoje)

    # 📁 GAVETA 2: HISTÓRICO DE SORTEIOS (O Mestre - Raiz > Nome > Numero)
    ficha_hist = ficha_hoje.copy()
    if slug == "maismilionaria" and d.get("trevos"): ficha_hist["trevos"] = d["trevos"]
    if slug == "timemania" and d.get("time"): ficha_hist["time_coracao"] = d["time"]
    if slug == "diadesorte" and d.get("mes"): ficha_hist["mes_sorte"] = d["mes"]
    db_call("PUT", f"HISTORICOS_DE_SORTEIOS/{nome}/{c}", ficha_hist)

    # 📁 GAVETA 3: PRÓXIMO CONCURSO (Exatamente como o Rascunho)
    ficha_prox = {
        "Data do Próximo Sorteio": d["p_data"],
        "Estimativa de Prêmio": formatar_moeda(d["p_est"]),
        "Número do Concurso": d["p_conc"]
    }
    db_call("PUT", f"PROXIMO_CONCURSO/{nome}", ficha_prox)

    # 📁 GAVETA 4: ESTATÍSTICAS (Machine Learning, Faxina e 50 Jogos Novos)
    jogos_antigos = db_call("GET", f"ESTATISTICAS/{nome}/jogos_prontos")
    pesos_ia = auditar_e_aprender(nome, jogos_antigos, d["dzs"])
    
    db_call("DELETE", f"ESTATISTICAS/{nome}")
    time.sleep(1.5) # Respiro de segurança
    novos_jogos = gerar_jogos_profundos(slug, config, pesos_ia)
    db_call("PUT", f"ESTATISTICAS/{nome}/jogos_prontos", novos_jogos)
    
    print(f"   ✅ Arquitetura de Nuvem Blindada atualizada com sucesso.")

# =========================================================================
# 6. REGRA DE NEGÓCIO: LISTA DE ALVOS E PARADA SEGURA
# =========================================================================
def determinar_alvos_do_dia(agora_brt):
    alvos = []
    data_hoje = agora_brt.strftime("%d/%m/%Y")
    data_ontem = (agora_brt - timedelta(days=1)).strftime("%d/%m/%Y")
    eh_repescagem = agora_brt.hour == 9
    
    print(f"📝 Fase de Reconhecimento (Lendo gaveta PROXIMO_CONCURSO)...")

    for slug, config in JOGOS.items():
        nome = config["nome"]
        prox = db_call("GET", f"PROXIMO_CONCURSO/{nome}")
        
        if not prox: # Banco vazio, processa tudo
            alvos.append(slug)
            continue
            
        data_esperada = prox.get("Data do Próximo Sorteio", "")
        
        if eh_repescagem:
            if data_esperada == data_ontem: alvos.append(slug)
        else:
            if data_esperada == data_hoje or data_esperada == data_ontem:
                alvos.append(slug)

    return alvos

# =========================================================================
# 7. MOTOR DE EXECUÇÃO PRINCIPAL
# =========================================================================
def main():
    agora_brt = datetime.now(timezone.utc) - timedelta(hours=3)
    print(f"=============================================================")
    print(f"🤖 ROBÔ LOTERIAS NUVEM BLINDADA - {agora_brt.strftime('%d/%m/%Y %H:%M')}")
    print(f"=============================================================")

    # Segurança: Cria Estatísticas se o banco for novo e a pasta não existir
    for slug, config in JOGOS.items():
        if not db_call("GET", f"ESTATISTICAS/{config['nome']}/jogos_prontos"):
            print(f"🛠️  Inicializando banco de ESTATÍSTICAS dinâmico para {config['nome']}...")
            p = gerar_jogos_profundos(slug, config, {"peso_quentes": 1, "peso_atrasadas": 1, "peso_frias": 1, "peso_cooc": 1})
            db_call("PUT", f"ESTATISTICAS/{config['nome']}/jogos_prontos", p)

    # 1. Determina quem vai ser buscado hoje (Lista de Alvos)
    alvos = determinar_alvos_do_dia(agora_brt)
    
    if not alvos:
        print("🛑 Nenhum alvo agendado para este horário. Encerrando expediente.")
        return
        
    print(f"🎯 Alvos detectados: {', '.join([JOGOS[s]['nome'] for s in alvos])}\n")

    # 2. A Caçada Tripla
    for slug in alvos:
        config = JOGOS[slug]
        print(f"[SISTEMA] Varredura ativa: {config['nome']}")
        dados = buscar_dados_loteria(slug)
        
        if dados:
            hoje_db = db_call("GET", f"SORTEIO_DE_HOJE/{config['nome']}")
            conc_banco = str(hoje_db.get("numero", "")) if hoje_db else ""
            
            # Condição de Atualização
            if dados["conc"] != conc_banco:
                processar_vitoria(slug, config, dados)
            else:
                print(f"   ✔️ Atualizado. Nada a fazer (Conc. atual: {dados['conc']}).")
                
                # REGRA DA PARADA SEGURA (Joga a toalha se for de manhã)
                if agora_brt.hour == 9:
                    print(f"   🛑 [Repescagem 09:00] Sorteio não liberado pela Caixa. Jogando a toalha.")
        else:
            print(f"   🚨 ALERTA: Falha total nas 3 fontes para {config['nome']}.")

    print(f"\n🏁 CICLO FINALIZADO. NUVEM BLINDADA.")

if __name__ == "__main__":
    main()
