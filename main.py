import requests
import json
import os
import random
import time
import re
import traceback
from datetime import datetime, timedelta, timezone
from collections import Counter

# Desativa avisos de SSL
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
# 3. PREPARAÇÃO DA NUVEM PARA OS NOVOS RECURSOS DO APP
# =========================================================================
def preparar_infraestrutura_frontend():
    print("   ⚙️ Verificando infraestrutura do App...")
    config_atual = db_call("GET", "SISTEMA_ADM/CONFIG_VISUAL_GLOBAL")
    if not isinstance(config_atual, dict):
        config_padrao = {
            "tema_metalico": "padrao", "usar_cores_manuais": False,
            "cor_texto_btn": "#ffffff", "cor_fundo_btn1": "#31006F",
            "cor_fundo_btn2": "#f39c12", "imagem_fundo_url": "", 
            "boloes_status": "oculto", "boloes_link": "https://seulinkpopular.com",
            "boloes_senha": "", "rodape_ativo": False,
            "rodape_texto": "Gerador Oficial Inteligente - Boa Sorte!"
        }
        db_call("PUT", "SISTEMA_ADM/CONFIG_VISUAL_GLOBAL", config_padrao)
        print("   ✅ Gavetas criadas!")

    cadastros = db_call("GET", "CADASTRO_DE_CLIENTES")
    if not isinstance(cadastros, dict):
        db_call("PUT", "CADASTRO_DE_CLIENTES/info_sistema", {"criado_por": "Robô IA Trator", "status": "Pronto para receber cadastros"})

# =========================================================================
# 4. MOTOR 6: MACHINE LEARNING E IA PROFUNDA (CÓDIGO INTACTO)
# =========================================================================
def auditar_e_aprender(config, dezenas_reais):
    nome = config["nome"]
    jogos_antigos = db_call("GET", f"ESTATISTICAS/{nome}/jogos_prontos")
    pesos_atuais = db_call("GET", f"EVOLUCAO_DA_IA/{nome}/pesos")
    
    if not isinstance(pesos_atuais, dict): pesos_atuais = {}
        
    p_quentes = pesos_atuais.get("peso_quentes", 0.4)
    p_atrasadas = pesos_atuais.get("peso_atrasadas", 0.3)
    p_cooc = pesos_atuais.get("peso_cooc", 0.3)
    pesos_atuais = {"peso_quentes": p_quentes, "peso_atrasadas": p_atrasadas, "peso_cooc": p_cooc}

    if not jogos_antigos or not dezenas_reais:
        db_call("PATCH", f"EVOLUCAO_DA_IA/{nome}/pesos", pesos_atuais)
        return pesos_atuais

    dezenas_reais_set = set(int(x) for x in dezenas_reais)
    total_acertos = 0
    qtd_jogos = len(jogos_antigos)

    for chave, jogo in jogos_antigos.items():
        dzs_jogo = jogo["numeros"] if isinstance(jogo, dict) else jogo
        dzs_int = set(int(x) for x in dzs_jogo)
        acertos = len(dzs_int.intersection(dezenas_reais_set))
        total_acertos += acertos

    media_acertos = total_acertos / qtd_jogos if qtd_jogos > 0 else 0
    alvo_esperado = config["qtd"] * 0.3 
    
    if media_acertos < alvo_esperado:
        pesos_atuais["peso_quentes"] = max(0.1, pesos_atuais["peso_quentes"] - 0.05)
        pesos_atuais["peso_atrasadas"] = min(0.6, pesos_atuais["peso_atrasadas"] + 0.05)
    else:
        pesos_atuais["peso_quentes"] = min(0.7, pesos_atuais["peso_quentes"] + 0.05)
        pesos_atuais["peso_atrasadas"] = max(0.1, pesos_atuais["peso_atrasadas"] - 0.05)

    db_call("PATCH", f"EVOLUCAO_DA_IA/{nome}/pesos", pesos_atuais)
    return pesos_atuais

def motor_ia_profunda(slug, config, pesos_cognitivos):
    nome = config["nome"]
    hist = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome}")
    if not hist or (not isinstance(hist, dict) and not isinstance(hist, list)): return {}
    
    dados_h = hist if isinstance(hist, dict) else {str(i): v for i, v in enumerate(hist) if v}
    todas_dz = []
    matriz_afinidade = Counter()
    atrasos = {} 
    somas_historicas = []
    pares_impares = Counter()
    historico_sets = []
    
    concursos_ordenados = sorted(dados_h.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)
    inicio = 0 if slug in ["lotomania", "supersete"] else 1
    fim = 99 if slug == "lotomania" else (9 if slug == "supersete" else config.get("total", 60))
    
    for c_id, concurso in concursos_ordenados:
        if not isinstance(concurso, dict): continue
        dzs_int = []
        if "Bola1" in concurso:
            for i in range(1, 100):
                b_chave = f"Bola{i}"
                if b_chave in concurso:
                    try: dzs_int.append(int(concurso[b_chave]))
                    except: pass
        else:
            dzs = concurso.get("dezenas", [])
            dzs_int = [int(x) for x in dzs] if dzs else []
            
        if not dzs_int: continue
        dzs_int = sorted(list(set(dzs_int)))
        historico_sets.append(set(dzs_int))
        todas_dz.extend(dzs_int)
        somas_historicas.append(sum(dzs_int))
        impares = len([n for n in dzs_int if n % 2 != 0])
        pares_impares[f"{impares}i"] += 1
        
        for num in range(inicio, fim + 1):
            if num in dzs_int: atrasos[num] = 0
            else: atrasos[num] = atrasos.get(num, 0) + 1
            
        for i in range(len(dzs_int)):
            for j in range(i + 1, len(dzs_int)):
                matriz_afinidade[tuple(sorted((dzs_int[i], dzs_int[j])))] += 1

    freq = Counter(todas_dz)
    quentes = [x[0] for x in freq.most_common()]
    atrasadas = sorted(atrasos.keys(), key=lambda k: atrasos[k], reverse=True)
    media_soma = sum(somas_historicas) / len(somas_historicas) if somas_historicas else 0
    margem_soma = media_soma * 0.25 
    padrao_frequente = pares_impares.most_common(1)
    imp_target = int(padrao_frequente[0][0].replace('i','')) if padrao_frequente else (config["qtd"] // 2)

    candidatos = []
    jogos_unicos = set()
    tentativas = 0
    qtd = config["qtd"]
    p_quentes = pesos_cognitivos.get("peso_quentes", 0.4)
    p_atrasadas = pesos_cognitivos.get("peso_atrasadas", 0.3)
    
    while len(candidatos) < 150 and tentativas < 5000:
        tentativas += 1
        pool = set()
        pool.update(random.sample(quentes[:30], min(30, int(qtd * p_quentes))))
        pool.update(random.sample(atrasadas[:20], min(20, int(qtd * p_atrasadas))))
        if pool:
            bola_base = list(pool)[0]
            amigos = [par for par in matriz_afinidade.keys() if bola_base in par]
            if amigos:
                amigos.sort(key=lambda x: matriz_afinidade[x], reverse=True)
                melhor_amigo = amigos[0][1] if amigos[0][0] == bola_base else amigos[0][0]
                pool.add(melhor_amigo)
        while len(pool) < qtd: pool.add(random.randint(inicio, fim))
            
        jg = sorted(list(pool)[:qtd])
        soma_jogo = sum(jg)
        qtd_impares = len([n for n in jg if n % 2 != 0])
        passou_juiz_soma = (media_soma - margem_soma) <= soma_jogo <= (media_soma + margem_soma)
        passou_impares = abs(qtd_impares - imp_target) <= 1
        assinatura = "-".join(str(x) for x in jg)
        
        if assinatura not in jogos_unicos and ((passou_juiz_soma and passou_impares) or tentativas > 3000):
            jogos_unicos.add(assinatura)
            candidatos.append(jg)
            
    ranking = []
    min_premio = config.get("min_premio", 11)
    for jg in candidatos:
        jogo_set = set(jg)
        score = 0
        for hist_set in historico_sets:
            acertos = len(jogo_set.intersection(hist_set))
            if acertos >= min_premio: score += (acertos - min_premio + 1) ** 4
        ranking.append({ "numeros": jg, "score": score })
        
    ranking.sort(key=lambda x: x["score"], reverse=True)
    palpites = {}
    for i in range(min(50, len(ranking))):
        idx = i + 1
        jg_obj = ranking[i]
        status_txt = "🔥 JOGO QUENTE (TOP 3)" if idx <= 3 else "IA CLOUD BLINDADA"
        p_obj = {"numeros": [f"{x:02d}" for x in jg_obj["numeros"]], "taxa_acerto": jg_obj["score"], "status": status_txt}
        if "trevos" in config:
            t = sorted(random.sample(range(1, 7), 2))
            p_obj["trevos"] = [f"{x:02d}" for x in t]
        palpites[f"jogo_{idx:02d}"] = p_obj
            
    return palpites

# =========================================================================
# 6. INSPETOR DE ERROS (O X-9 DO BANCO DE DADOS)
# =========================================================================
def banco_esta_incompleto(nome_jogo, slug, conc_api):
    hoje = db_call("GET", f"SORTEIO_DE_HOJE/{nome_jogo}")
    hist = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome_jogo}/{conc_api}")
    
    num_banco = str(hoje.get("numero")) if isinstance(hoje, dict) else "Nenhum"
    print(f"   📊 Verificando: Sorteio no Firebase é o [{num_banco}]. Sorteio puxado da API é o [{conc_api}].")

    if not isinstance(hoje, dict) or str(hoje.get("numero")) != str(conc_api): 
        return True
    if not isinstance(hist, dict): 
        return True

    for base in [hoje, hist]:
        if not base.get("data") or base.get("data") == "": return True
        if not base.get("premiacoes") or len(base.get("premiacoes")) == 0: return True
        if "Bola1" in base or "Cidade UF" in base: return True
        if slug == "timemania" and not base.get("timeCoracao"): return True
        if slug == "diadesorte" and not base.get("mesSorte"): return True
        if slug == "maismilionaria" and not base.get("trevos"): return True
            
    return False

# =========================================================================
# 7. CAPTURA DE DADOS REAIS (MODO SIMPLES PARA PASSAR NO PLANO GRÁTIS)
# =========================================================================
def buscar_dados_loteria(slug):
    SCRAPER_KEY = os.environ.get('SCRAPER_API_KEY', '').strip()
    quebrador_cache = int(time.time() * 1000)
    url_caixa = f"https://servicebus2.caixa.gov.br/loterias/api/{slug}?_={quebrador_cache}"
    
    fontes = []
    
    if SCRAPER_KEY:
        # ATENÇÃO: Retiramos o premium=true e country_code. Planos grátis bloqueiam eles.
        proxy_simples = f"http://api.scraperapi.com?api_key={SCRAPER_KEY}&url={url_caixa}"
        fontes.append((proxy_simples, "PROXY CAIXA (Simples)"))
    
    # BRASIL API é a nossa principal carta na manga além da Caixa.
    # Removemos as outras (Guidi, Heroku) porque elas mentem resultados velhos!
    fontes.append((f"https://brasilapi.com.br/api/loterias/v1/{slug}", "BRASIL API"))
    
    resultados_obtidos = []
    
    for url, nome_fonte in fontes:
        try:
            print(f"   🔎 Tentando {nome_fonte}...")
            # Algumas APIs quebram se mandarmos Headers de navegador, então limpamos para a Brasil API
            headers_usar = HEADERS if "PROXY" in nome_fonte else {}
            res = sessao.get(url, headers=headers_usar, verify=False, timeout=25)
            
            if res.status_code == 200:
                try: d = res.json()
                except: continue
                
                c = d.get("numero") or d.get("concurso")
                if not c: continue
                
                dt = d.get("dataApuracao") or d.get("data")
                dzs = d.get("listaDezenas") or d.get("dezenas")
                p_data = d.get("dataPróximoConcurso") or d.get("dataProximoConcurso") or d.get("data_proximo_concurso", "")
                p_est = d.get("valorEstimadoPróximoConcurso") or d.get("valorEstimadoProximoConcurso") or d.get("valor_estimado_proximo_concurso", 0)
                
                extra_str = ""
                trevos_lista = []
                
                if slug == "timemania": extra_str = d.get("nomeTimeCoracaoMessorte") or d.get("time_do_coracao") or d.get("timeCoracao") or ""
                elif slug == "diadesorte": extra_str = d.get("nomeTimeCoracaoMessorte") or d.get("mes_da_sorte") or d.get("mesSorte") or ""
                elif slug == "maismilionaria":
                    tr = d.get("trevos") or d.get("listaTrevos") or []
                    trevos_lista = [int(x) for x in tr] if tr else []

                resultado_formatado = {
                    "conc": str(c), "data": dt, "dzs": [int(x) for x in dzs] if dzs else [],
                    "acum": d.get("acumulado") or d.get("acumulou"),
                    "arrec": d.get("valorArrecadado") or d.get("valor_arrecadado", 0),
                    "rates": d.get("listaRateioPremio") or d.get("premiacoes", []),
                    "p_data": p_data, "p_est": p_est,
                    "extra": extra_str, "trevos": trevos_lista,
                    "fonte_oficial": nome_fonte
                }
                resultados_obtidos.append(resultado_formatado)
                break # Achou o resultado fresco? Para de procurar imediatamente.
            else:
                print(f"   [!] {nome_fonte} falhou (HTTP {res.status_code})")
        except Exception as e:
            print(f"   [!] Erro de conexão com {nome_fonte}.")
            continue

    if resultados_obtidos:
        def rankeador(x):
            num_concurso = int(extrair_id_limpo(x["conc"]) or 0)
            tem_rateio = 1 if len(x.get("rates", [])) > 0 else 0
            return (num_concurso, tem_rateio)
            
        resultados_obtidos.sort(key=rankeador, reverse=True)
        campeao = resultados_obtidos[0]
        
        print(f"   🏆 SUCESSO: O resultado mais novo encontrado foi da {campeao['fonte_oficial']} (Concurso {campeao['conc']})")
        return campeao
        
    return None

# =========================================================================
# 8. EFEITO DOMINÓ (SALVANDO NA NUVEM)
# =========================================================================
def efeito_domino(slug, config, d):
    nome = config["nome"]
    c_id = extrair_id_limpo(d["conc"])
    print(f"   🚀 Salvando Sorteio [{c_id}] no Firebase para {nome}...")

    pesos_calibrados = auditar_e_aprender(config, d["dzs"])

    ficha_base = {
        "numero": c_id, "data": d["data"], "dezenas": d["dzs"],
        "acumulou": "SIM" if d["acum"] else "NÃO",
        "arrecadacao": d["arrec"], "premiacoes": d["rates"]
    }
    
    if slug == "timemania": ficha_base["timeCoracao"] = d.get("extra", "")
    elif slug == "diadesorte": ficha_base["mesSorte"] = d.get("extra", "")
    elif slug == "maismilionaria": ficha_base["trevos"] = d.get("trevos", [])

    db_call("PUT", f"SORTEIO_DE_HOJE/{nome}", ficha_base)
    db_call("PUT", f"HISTORICOS_DE_SORTEIOS/{nome}/{c_id}", ficha_base)

    texto_estimativa = f"Estimativa de prêmio do próximo concurso {d['p_data']}" if d.get('p_data') else "Estimativa de prêmio a definir"
    ficha_prox = {"texto_data": texto_estimativa, "valor_estimativa": formatar_moeda(d["p_est"])}
    db_call("PUT", f"PROXIMO_CONCURSO/{nome}", ficha_prox)

    db_call("DELETE", f"ESTATISTICAS/{nome}")
    time.sleep(2) 
    
    palpites_novos = motor_ia_profunda(slug, config, pesos_calibrados)
    db_call("PUT", f"ESTATISTICAS/{nome}/jogos_prontos", palpites_novos)
    pasta_isolada = f"{nome.replace('-', '').capitalize()}_Estatisticas/jogos_prontos"
    db_call("PUT", pasta_isolada, palpites_novos)
    print(f"   ✅ Atualização 100% Completa para {nome}!")

# =========================================================================
# 9. MOTOR CENTRAL DO SERVIDOR
# =========================================================================
def main():
    try:
        agora_br = datetime.now(timezone.utc) - timedelta(hours=3)
        hora = agora_br.hour
        print(f"=============================================================")
        print(f"🤖 ROBÔ LOTERIAS IA PROFUNDA - {agora_br.strftime('%d/%m/%Y %H:%M')}")
        print(f"=============================================================")

        preparar_infraestrutura_frontend()

        if hora == 9: print("🌅 Repescagem das 09h.")

        for slug, config in JOGOS.items():
            print(f"\n[Buscando] {config['nome']}...")
            dados = buscar_dados_loteria(slug)
            
            if dados:
                if banco_esta_incompleto(config["nome"], slug, dados["conc"]):
                    efeito_domino(slug, config, dados)
                else:
                    print(f"   ✔️ O concurso {dados['conc']} já está no banco. Nenhuma atualização necessária.")
            else:
                print(f"   🚨 Erro Crítico: O robô não conseguiu acessar os resultados oficiais novos hoje.")

        print(f"\n🏁 SESSÃO FINALIZADA.")
        
    except Exception as e:
        print(f"\n🚨 ERRO FATAL: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
