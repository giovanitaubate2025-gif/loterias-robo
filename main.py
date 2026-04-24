 


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
# 2. FUNÇÕES DE APOIO E COMUNICAÇÃO FIREBASE
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
# 3. PREPARAÇÃO DA NUVEM PARA OS NOVOS RECURSOS DO APP (NOVO)
# =========================================================================
def preparar_infraestrutura_frontend():
    """
    Cria as gavetas na nuvem para as novas funções visuais e de segurança 
    do aplicativo (Bolões, Cadastro, Cores Metálicas, Imagem de Fundo).
    """
    print("   ⚙️ Verificando infraestrutura de Design e Segurança do App...")
    
    # 1. Configurações Visuais e de Botões
    config_atual = db_call("GET", "SISTEMA_ADM/CONFIG_VISUAL_GLOBAL")
    if not config_atual:
        config_padrao = {
            "tema_metalico": "padrao", # opções: ouro, prata, azul_royal, preto_carbono, padrao
            "usar_cores_manuais": False,
            "cor_texto_btn": "#ffffff",
            "cor_fundo_btn1": "#31006F",
            "cor_fundo_btn2": "#f39c12",
            "imagem_fundo_url": "", # Link da imagem que vai cobrir 100% da tela
            "boloes_status": "oculto", # opções: oculto, visivel, bloqueado, senha, cadastro
            "boloes_link": "https://seulinkpopular.com",
            "boloes_senha": "",
            "rodape_ativo": False,
            "rodape_texto": "Gerador Oficial Inteligente - Boa Sorte!"
        }
        db_call("PUT", "SISTEMA_ADM/CONFIG_VISUAL_GLOBAL", config_padrao)
        print("   ✅ Gavetas de Configuração Visual e Bolões criadas com sucesso!")

    # 2. Pasta de Cadastro de Clientes Exclusiva
    cadastros = db_call("GET", "CADASTRO_DE_CLIENTES")
    if cadastros is None:
        # Inicializa a pasta vazia para evitar erros no aplicativo
        db_call("PUT", "CADASTRO_DE_CLIENTES/info_sistema", {"criado_por": "Robô IA Trator", "status": "Pronto para receber cadastros"})
        print("   ✅ Pasta de Cadastro de Clientes blindada e pronta!")

# =========================================================================
# 4. MOTOR 6: MACHINE LEARNING (O ALGORITMO PAI QUE APRENDE)
# =========================================================================
def auditar_e_aprender(config, dezenas_reais):
    nome = config["nome"]
    print(f"   🧠 ML-Auditor: Avaliando taxa de acerto do robô para {nome}...")
    
    jogos_antigos = db_call("GET", f"ESTATISTICAS/{nome}/jogos_prontos")
    pesos_atuais = db_call("GET", f"EVOLUCAO_DA_IA/{nome}/pesos")
    
    if not pesos_atuais:
        pesos_atuais = {"peso_quentes": 0.4, "peso_atrasadas": 0.3, "peso_cooc": 0.3}

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

    print(f"   📈 Evolução: Média de Acertos: {media_acertos:.2f} | Novos Pesos: {pesos_atuais}")
    
    db_call("PATCH", f"EVOLUCAO_DA_IA/{nome}/pesos", pesos_atuais)
    return pesos_atuais

# =========================================================================
# 5. OS 5 MOTORES DE IA PROFUNDA (ESTATÍSTICA E MONTAGEM)
# =========================================================================
def motor_ia_profunda(slug, config, pesos_cognitivos):
    nome = config["nome"]
    print(f"   ⚙️ Motor IA Profunda: Calculando Probabilidades Múltiplas (Análise Global)...")
    
    hist = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome}")
    if not hist: return {}
    dados_h = hist if isinstance(hist, dict) else {str(i): v for i, v in enumerate(hist) if v}
    
    todas_dz = []
    matriz_afinidade = Counter()
    atrasos = {} 
    somas_historicas = []
    
    concursos_ordenados = sorted(dados_h.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)
    
    for c_id, concurso in concursos_ordenados:
        if not concurso: continue
        
        dzs_int = []
        if isinstance(concurso, dict) and "Bola1" in concurso:
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
        todas_dz.extend(dzs_int)
        somas_historicas.append(sum(dzs_int))
        
        for num in range(1 if slug not in ["lotomania", "supersete"] else 0, config.get("total", 60) + 1):
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

    palpites = {}
    inicio = 0 if slug in ["lotomania", "supersete"] else 1
    fim = 99 if slug == "lotomania" else (9 if slug == "supersete" else config.get("total", 60))
    jogos_unicos = set()
    
    contador = 1
    tentativas = 0
    qtd = config["qtd"]
    
    p_quentes = pesos_cognitivos.get("peso_quentes", 0.4)
    p_atrasadas = pesos_cognitivos.get("peso_atrasadas", 0.3)
    
    print(f"   🔨 Montador: Aplicando Filtro de Soma e Exclusividade...")
    while contador <= 50 and tentativas < 5000:
        tentativas += 1
        pool = set()
        
        qtd_quentes = int(qtd * p_quentes)
        pool.update(random.sample(quentes[:30], min(30, qtd_quentes)))
        
        qtd_atrasadas = int(qtd * p_atrasadas)
        pool.update(random.sample(atrasadas[:20], min(20, qtd_atrasadas)))
        
        if pool:
            bola_base = list(pool)[0]
            amigos = [par for par in matriz_afinidade.keys() if bola_base in par]
            if amigos:
                amigos.sort(key=lambda x: matriz_afinidade[x], reverse=True)
                melhor_amigo = amigos[0][1] if amigos[0][0] == bola_base else amigos[0][0]
                pool.add(melhor_amigo)
        
        while len(pool) < qtd:
            pool.add(random.randint(inicio, fim))
            
        jg = sorted(list(pool)[:qtd])
        soma_jogo = sum(jg)
        
        passou_juiz_soma = (media_soma - margem_soma) <= soma_jogo <= (media_soma + margem_soma)
        assinatura = "-".join(str(x) for x in jg)
        
        if assinatura not in jogos_unicos and (passou_juiz_soma or tentativas > 3000):
            jogos_unicos.add(assinatura)
            
            if "trevos" in config:
                t = sorted(random.sample(range(1, 7), 2))
                palpites[f"jogo_{contador:02d}"] = {"numeros": [f"{x:02d}" for x in jg], "trevos": [f"{x:02d}" for x in t]}
            else:
                palpites[f"jogo_{contador:02d}"] = [f"{x:02d}" for x in jg]
            
            contador += 1
            
    return palpites

# =========================================================================
# 6. O TRATOR DE VISTORIA (INSPETOR IMPLACÁVEL DE ERROS DA NUVEM)
# =========================================================================
def banco_esta_incompleto(nome_jogo, slug, conc_api):
    hoje = db_call("GET", f"SORTEIO_DE_HOJE/{nome_jogo}")
    hist = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome_jogo}/{conc_api}")
    
    if not hoje or str(hoje.get("numero")) != str(conc_api): return True
    if not hist: return True

    for base in [hoje, hist]:
        if not base.get("data") or base.get("data") == "":
            print(f"   🔍 Inspetor: 'Data' em branco em {nome_jogo}. Corrigindo banco...")
            return True
            
        if not base.get("premiacoes") or len(base.get("premiacoes")) == 0:
            print(f"   🔍 Inspetor: Tabela de 'Premiações' vazia em {nome_jogo}.")
            return True
            
        if "Bola1" in base or "Cidade UF" in base:
            print(f"   🔍 Inspetor: Lixo antigo do Excel detectado em {nome_jogo}.")
            return True
            
        if slug == "timemania" and not base.get("timeCoracao"):
            print(f"   🔍 Inspetor: Falta o 'Time do Coração' na Timemania!")
            return True
            
        if slug == "diadesorte" and not base.get("mesSorte"):
            print(f"   🔍 Inspetor: Falta o 'Mês da Sorte' no Dia de Sorte!")
            return True
            
        if slug == "maismilionaria" and not base.get("trevos"):
            print(f"   🔍 Inspetor: Falta os 'Trevos' na +Milionária!")
            return True
            
    return False

# =========================================================================
# 7. CAPTURA DE DADOS REAIS COM EXTRAÇÃO PROFUNDA (TIMES E TREVOS)
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
                c = d.get("numero") or d.get("concurso")
                dt = d.get("dataApuracao") or d.get("data")
                dzs = d.get("listaDezenas") or d.get("dezenas")
                p_data = d.get("dataPróximoConcurso") or d.get("dataProximoConcurso") or d.get("data_proximo_concurso", "")
                p_est = d.get("valorEstimadoPróximoConcurso") or d.get("valorEstimadoProximoConcurso") or d.get("valor_estimado_proximo_concurso", 0)
                
                extra_str = ""
                trevos_lista = []
                
                if slug == "timemania":
                    extra_str = d.get("nomeTimeCoracaoMessorte") or d.get("time_do_coracao") or d.get("timeCoracao") or ""
                elif slug == "diadesorte":
                    extra_str = d.get("nomeTimeCoracaoMessorte") or d.get("mes_da_sorte") or d.get("mesSorte") or ""
                elif slug == "maismilionaria":
                    tr = d.get("trevos") or d.get("listaTrevos") or []
                    trevos_lista = [int(x) for x in tr] if tr else []

                return {
                    "conc": str(c), "data": dt, "dzs": [int(x) for x in dzs] if dzs else [],
                    "acum": d.get("acumulado") or d.get("acumulou"),
                    "arrec": d.get("valorArrecadado") or d.get("valor_arrecadado", 0),
                    "rates": d.get("listaRateioPremio") or d.get("premiacoes", []),
                    "p_data": p_data, "p_est": p_est,
                    "extra": extra_str, "trevos": trevos_lista
                }
        except: continue
    return None

# =========================================================================
# 8. EFEITO DOMINÓ (ROTEAMENTO E DISTRIBUIÇÃO BLINDADOS)
# =========================================================================
def efeito_domino(slug, config, d):
    nome = config["nome"]
    c_id = extrair_id_limpo(d["conc"])
    print(f"   🚀 Distribuindo Pacotes e Limpando Lixo Antigo: {nome} (Conc. {c_id})")

    pesos_calibrados = auditar_e_aprender(config, d["dzs"])

    ficha_base = {
        "numero": c_id, "data": d["data"], "dezenas": d["dzs"],
        "acumulou": "SIM" if d["acum"] else "NÃO",
        "arrecadacao": d["arrec"], "premiacoes": d["rates"]
    }
    
    if slug == "timemania":
        ficha_base["timeCoracao"] = d.get("extra", "")
    elif slug == "diadesorte":
        ficha_base["mesSorte"] = d.get("extra", "")
    elif slug == "maismilionaria":
        ficha_base["trevos"] = d.get("trevos", [])

    db_call("PUT", f"SORTEIO_DE_HOJE/{nome}", ficha_base)
    db_call("PUT", f"HISTORICOS_DE_SORTEIOS/{nome}/{c_id}", ficha_base)

    texto_estimativa = f"Estimativa de prêmio do próximo concurso {d['p_data']}" if d.get('p_data') else "Estimativa de prêmio do próximo concurso a definir"
    ficha_prox = {"texto_data": texto_estimativa, "valor_estimativa": formatar_moeda(d["p_est"])}
    db_call("PUT", f"PROXIMO_CONCURSO/{nome}", ficha_prox)

    db_call("DELETE", f"ESTATISTICAS/{nome}")
    time.sleep(2) 
    
    palpites_novos = motor_ia_profunda(slug, config, pesos_calibrados)
    db_call("PUT", f"ESTATISTICAS/{nome}/jogos_prontos", palpites_novos)

# =========================================================================
# 9. MOTOR CENTRAL DO SERVIDOR (GITHUB ACTIONS)
# =========================================================================
def main():
    agora_br = datetime.now(timezone.utc) - timedelta(hours=3)
    hora = agora_br.hour
    print(f"=============================================================")
    print(f"🤖 ROBÔ LOTERIAS IA PROFUNDA (INSPETOR) - {agora_br.strftime('%d/%m/%Y %H:%M')}")
    print(f"=============================================================")

    # EXECUTANDO A PREPARAÇÃO DO NOVO APLICATIVO ANTES DE QUALQUER COISA
    preparar_infraestrutura_frontend()

    if hora == 9:
        print("🌅 Repescagem das 09h. Parada Segura Ativa (Evitando Loop de Falha da Caixa).")

    for slug, config in JOGOS.items():
        print(f"\n[Processando] {config['nome']}")
        dados = buscar_dados_loteria(slug)
        
        if dados:
            if banco_esta_incompleto(config["nome"], slug, dados["conc"]):
                efeito_domino(slug, config, dados)
                print(f"   ✅ Sucesso: Lixo excluído! Nuvem formatada e Algoritmos Calibrados para {config['nome']}.")
            else:
                print(f"   ✔️ {config['nome']} 100% íntegro. Nada de errado encontrado.")
        else:
            print(f"   🚨 Erro Crítico: Conexão recusada nas 3 APIs.")

    print(f"\n🏁 SESSÃO DE IA FINALIZADA COM SUCESSO.")

if __name__ == "__main__":
    main()
