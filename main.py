import requests
import json
import os
import random
import time
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict

# Desativa avisos de SSL (Garante estabilidade no GitHub Actions)
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
        # Timeout longo (45s) para aguentar Big Data (Histórico do 1 ao atual)
        if method == "GET": return requests.get(url, timeout=45).json()
        if method == "PUT": return requests.put(url, json=data, timeout=45)
        if method == "PATCH": return requests.patch(url, json=data, timeout=45)
        if method == "DELETE": return requests.delete(url, timeout=45)
    except Exception as e: 
        print(f"   [!] Erro Firebase ({method} em {path}): {e}")
        return None

def formatar_moeda(v):
    try: return f"R$ {float(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return "R$ 0,00"

def banco_com_dados_faltantes(dados_db):
    """ O FISCAL: Varre a ficha para ver se há buracos (Data, Rateio, Dezenas vazios) """
    if not dados_db: return True
    # Validações estritas de existência e preenchimento
    if not dados_db.get("data") or str(dados_db.get("data")).strip() == "": return True
    if not dados_db.get("dezenas") or len(dados_db.get("dezenas")) == 0: return True
    # Se "premiacoes" não existe como chave na ficha, está incompleto
    if "premiacoes" not in dados_db: return True
    return False

# =========================================================================
# 3. INTELIGÊNCIA ARTIFICIAL E BIG DATA (OS 6 MOTORES)
# =========================================================================
def auditar_e_aprender(nome, jogos_antigos, dezenas_sorteadas):
    """ MOTOR 6 (MACHINE LEARNING): Avalia o passado e ajusta a fórmula da I.A. """
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
    
    # Recalibragem Automática
    if media_acertos < (len(dezenas_sorteadas) * 0.3):
        pesos_atuais["peso_quentes"] = round(random.uniform(0.5, 2.0), 2)
        pesos_atuais["peso_atrasadas"] = round(random.uniform(0.5, 2.0), 2)
        pesos_atuais["peso_frias"] = round(random.uniform(0.5, 1.5), 2)
        pesos_atuais["peso_cooc"] = round(random.uniform(0.5, 2.0), 2)
        print(f"   🔄 [Machine Learning] I.A. reajustou os pesos matemáticos para evoluir.")
    
    db_call("PUT", f"EVOLUCAO_DA_IA/{nome}/pesos", pesos_atuais)
    return pesos_atuais

def gerar_jogos_profundos(slug, config, pesos_ia):
    nome = config["nome"]
    hist = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome}")
    
    # MOTOR 1: Mineração Total (Varrer do 1º ao Atual)
    data_h = {}
    if isinstance(hist, list):
        data_h = {str(i): v for i, v in enumerate(hist) if v}
    elif isinstance(hist, dict):
        data_h = hist

    concursos_ordenados = sorted(data_h.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)
    
    # Deduplicação Nível 2: Limpa dezenas clonadas dentro de um mesmo sorteio antigo
    historico_puro = []
    for c in concursos_ordenados:
        if "dezenas" in c[1]:
            # Usa 'set' para remover repetidas no mesmo concurso
            dezenas_unicas = sorted(list(set(c[1]["dezenas"])))
            historico_puro.append(dezenas_unicas)
    
    if not historico_puro: return {}

    inicio = 0 if slug in ["lotomania", "supersete"] else 1
    fim = 99 if slug == "lotomania" else (9 if slug == "supersete" else config.get("total", 60))
    
    # MOTORES 2 E 3: Termômetro (Frias/Quentes) e Coocorrência (Matriz)
    frequencias = Counter()
    atrasos = {n: 0 for n in range(inicio, fim + 1)}
    cooc = defaultdict(Counter)
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

    # MOTOR 4: Juiz de Balanceamento (Soma Média e Paridade Dinâmica)
    media_soma = sum(somas_historicas) / len(somas_historicas)
    desvio_soma = (sum((s - media_soma)**2 for s in somas_historicas) / len(somas_historicas))**0.5
    limite_min_soma = media_soma - (desvio_soma * 1.5)
    limite_max_soma = media_soma + (desvio_soma * 1.5)

    ultimo_jogo = historico_puro[-1]
    pares_ultimo = sum(1 for d in ultimo_jogo if d % 2 == 0)
    qtd = config.get("qtd", 6)
    meta_pares = (qtd // 2) + (1 if pares_ultimo < (qtd // 2) else -1)

    # MOTOR 5: Montador Estruturado com Deduplicação Final
    resultado_final = {}
    jogos_gerados_hashes = set() # Memória anti-duplicação de jogos
    
    i = 1
    while i <= 50:
        jogo_valido = False
        tentativas = 0
        
        while not jogo_valido:
            if config.get("tipo") == "colunar":
                jg = [random.randint(0, 9) for _ in range(7)]
                jogo_valido = True
            else:
                jg_set = set()
                # Escolha da semente (Quente, Fria ou Atrasada)
                roleta = random.random()
                if roleta < (0.4 * pesos_ia["peso_quentes"]) and top_quentes: 
                    jg_set.add(random.choice(top_quentes))
                elif roleta < (0.7 * pesos_ia["peso_atrasadas"]) and top_atrasadas: 
                    jg_set.add(random.choice(top_atrasadas))
                elif top_frias: 
                    jg_set.add(random.choice(top_frias))
                else:
                    jg_set.add(random.randint(inicio, fim))
                
                # Preenchimento Cruzado (Coocorrência)
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
                
                # JUIZ: Filtro Comportamental
                soma_jogo = sum(jg)
                pares_jogo = sum(1 for d in jg if d % 2 == 0)
                passou_soma = limite_min_soma <= soma_jogo <= limite_max_soma
                passou_paridade = abs(pares_jogo - meta_pares) <= 2
                
                # JUIZ: Deduplicação Nível 3 (Garante 50 opções ÚNICAS)
                jogo_hash = str(jg)
                passou_duplicata = jogo_hash not in jogos_gerados_hashes
                
                if passou_soma and passou_paridade and passou_duplicata:
                    jogo_valido = True
                    jogos_gerados_hashes.add(jogo_hash) # Memoriza para não repetir
                else:
                    tentativas += 1
                    # Quebra-Ciclo de Segurança
                    if tentativas > 150 and passou_duplicata: 
                        jogo_valido = True
                        jogos_gerados_hashes.add(jogo_hash)

        # Formatação JSON exigida
        if "trevos" in config:
            t = sorted(random.sample(range(1, 7), 2))
            resultado_final[f"jogo_{i:02d}"] = {"numeros": [f"{x:02d}" for x in jg], "trevos": [f"{x:02d}" for x in t]}
        else:
            resultado_final[f"jogo_{i:02d}"] = [f"{x:02d}" for x in jg]
            
        i += 1
            
    return resultado_final

# =========================================================================
# 4. CAPTURA TRIPLA REDUNDANTE (FONTES DE BUSCA)
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

                # Normalização estrita da ficha
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
    print(f"   🚀 EFEITO DOMINÓ ATIVADO: Consertando/Atualizando {nome} (Conc. {c})")

    # 📁 GAVETA 1: SORTEIO DE HOJE (Ficha Completa)
    ficha_hoje = {
        "numero": c, "data": d["data"], "dezenas": d["dzs"],
        "acumulou": "SIM" if d["acum"] else "NÃO",
        "arrecadacao": formatar_moeda(d["arrec"]), "premiacoes": d["rates"]
    }
    db_call("PUT", f"SORTEIO_DE_HOJE/{nome}", ficha_hoje)

    # 📁 GAVETA 2: HISTÓRICO DE SORTEIOS (Raiz > Jogo > Num com deduplicação de ID por chaves)
    ficha_hist = ficha_hoje.copy()
    if slug == "maismilionaria" and d.get("trevos"): ficha_hist["trevos"] = d["trevos"]
    if slug == "timemania" and d.get("time"): ficha_hist["time_coracao"] = d["time"]
    if slug == "diadesorte" and d.get("mes"): ficha_hist["mes_sorte"] = d["mes"]
    db_call("PUT", f"HISTORICOS_DE_SORTEIOS/{nome}/{c}", ficha_hist)

    # 📁 GAVETA 3: PRÓXIMO CONCURSO (Estritamente 3 informações - Limpeza da gaveta)
    ficha_prox = {
        "Data do Próximo Sorteio": d["p_data"],
        "Estimativa de Prêmio": formatar_moeda(d["p_est"]),
        "Número do Concurso": d["p_conc"]
    }
    db_call("PUT", f"PROXIMO_CONCURSO/{nome}", ficha_prox)

    # 📁 GAVETA 4: ESTATÍSTICAS (Machine Learning, Faxina e 50 Jogos Únicos)
    jogos_antigos = db_call("GET", f"ESTATISTICAS/{nome}/jogos_prontos")
    pesos_ia = auditar_e_aprender(nome, jogos_antigos, d["dzs"])
    
    db_call("DELETE", f"ESTATISTICAS/{nome}")
    time.sleep(1.5) # Respiro seguro para banco
    novos_jogos = gerar_jogos_profundos(slug, config, pesos_ia)
    db_call("PUT", f"ESTATISTICAS/{nome}/jogos_prontos", novos_jogos)
    
    print(f"   ✅ Arquitetura Blindada: Dados e Estatísticas perfeitamente alinhados.")

# =========================================================================
# 6. O CÃO DE GUARDA (LISTA DE ALVOS E PARADA SEGURA)
# =========================================================================
def determinar_alvos_do_dia(agora_brt):
    alvos = []
    data_hoje = agora_brt.strftime("%d/%m/%Y")
    data_ontem = (agora_brt - timedelta(days=1)).strftime("%d/%m/%Y")
    eh_repescagem = agora_brt.hour == 9
    
    print(f"📝 Fase de Reconhecimento (Analisando gaveta PROXIMO_CONCURSO)...")

    for slug, config in JOGOS.items():
        nome = config["nome"]
        prox = db_call("GET", f"PROXIMO_CONCURSO/{nome}")
        
        if not prox: # Banco vazio
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
    print(f"🤖 ROBÔ LOTERIAS DEEP IA MESTRE - {agora_brt.strftime('%d/%m/%Y %H:%M')}")
    print(f"=============================================================")

    # Segurança: Instala Estatísticas caso o banco seja novo/pasta inexistente
    for slug, config in JOGOS.items():
        if not db_call("GET", f"ESTATISTICAS/{config['nome']}/jogos_prontos"):
            print(f"🛠️  Inicializando banco ESTATÍSTICO blindado para {config['nome']}...")
            p = gerar_jogos_profundos(slug, config, {"peso_quentes": 1, "peso_atrasadas": 1, "peso_frias": 1, "peso_cooc": 1})
            db_call("PUT", f"ESTATISTICAS/{config['nome']}/jogos_prontos", p)

    # Cão de Guarda: Lista de Alvos
    alvos = determinar_alvos_do_dia(agora_brt)
    
    if not alvos:
        print("🛑 Nenhum alvo agendado. Encerrando expediente para poupar servidor.")
        return
        
    print(f"🎯 Alvos detectados: {', '.join([JOGOS[s]['nome'] for s in alvos])}\n")

    # A Caçada Tripla e Auditoria de Falhas Passadas
    for slug in alvos:
        config = JOGOS[slug]
        print(f"[SISTEMA] Varredura Ativa: {config['nome']}")
        dados_reais = buscar_dados_loteria(slug)
        
        if dados_reais:
            hoje_db = db_call("GET", f"SORTEIO_DE_HOJE/{config['nome']}")
            conc_banco = str(hoje_db.get("numero", "")) if hoje_db else ""
            
            # Auditoria de Integridade Implacável:
            # Substitui se o concurso for novo OU se a ficha atual tiver buracos (Data/Rateio vazios)
            if dados_reais["conc"] != conc_banco or banco_com_dados_faltantes(hoje_db):
                if dados_reais["conc"] == conc_banco:
                    print(f"   ⚠️ Auditoria detectou dados corrompidos/faltantes na nuvem. Restaurando integridade...")
                processar_vitoria(slug, config, dados_reais)
            else:
                print(f"   ✔️ Atualizado e 100% Íntegro. (Conc. atual: {dados_reais['conc']}).")
                
                # PARADA SEGURA (09:00 - Abandona caso governo não atualize)
                if agora_brt.hour == 9:
                    print(f"   🛑 [Repescagem 09:00] Sorteio retido pela Caixa. Jogando a toalha.")
        else:
            print(f"   🚨 ALERTA: Conexões das 3 fontes falharam para {config['nome']}.")

    print(f"\n🏁 CICLO DA INTELIGÊNCIA ARTIFICIAL FINALIZADO.")

if __name__ == "__main__":
    main()
