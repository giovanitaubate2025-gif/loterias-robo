import requests
import json
import os
import random
import time
import traceback
from datetime import datetime, timedelta, timezone
from collections import Counter

# Desativa avisos de SSL (Garante estabilidade no GitHub Actions/Termux)
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Referer": "https://loterias.caixa.gov.br/"
}

sessao = requests.Session()

# =========================================================================
# 2. FUNÇÕES FIREBASE (A CONEXÃO)
# =========================================================================
def db_call(method, path, data=None):
    url = f"{URL_FIREBASE}{path}.json?auth={SECRET_FIREBASE}"
    try:
        if method == "GET": 
            return sessao.get(url, timeout=30, verify=False).json()
        dados_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        if method == "PUT": 
            return sessao.put(url, data=dados_json.encode('utf-8'), timeout=30, verify=False)
        if method == "PATCH": 
            return sessao.patch(url, data=dados_json.encode('utf-8'), timeout=30, verify=False)
    except Exception as e:
        return None

def formatar_moeda(v):
    try:
        return f"R$ {float(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return "R$ 0,00"

# =========================================================================
# 3. CAPTURA DE DADOS (MOTOR ANTI-CACHE)
# =========================================================================
def buscar_dados_loteria(slug):
    quebrador_cache = int(time.time() * 1000)
    fontes = [
        (f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{slug}?_={quebrador_cache}", "CAIXA OFICIAL"),
        (f"https://brasilapi.com.br/api/loterias/v1/{slug}", "BRASIL API")
    ]
    
    for url, nome_fonte in fontes:
        try:
            res = sessao.get(url, headers=HEADERS, verify=False, timeout=12)
            if res.status_code == 200:
                d = res.json()
                c = d.get("numero") or d.get("concurso")
                if not c: continue
                
                dt = d.get("dataApuracao") or d.get("data")
                dzs = d.get("listaDezenas") or d.get("dezenas") or []
                p_data = d.get("dataPróximoConcurso") or d.get("dataProximoConcurso") or d.get("data_proximo_concurso", "")
                
                # Regra salvadora de estimativa (evita zerar Lotofácil)
                est_bruta = d.get("valorEstimadoPróximoConcurso") or d.get("valorEstimadoProximoConcurso") or d.get("valor_estimado_proximo_concurso") or 0
                if float(est_bruta) == 0 and slug == "lotofacil": est_bruta = 1700000

                extra_str = ""
                trevos_lista = []
                
                if slug == "timemania": extra_str = d.get("nomeTimeCoracaoMessorte") or d.get("timeCoracao") or ""
                elif slug == "diadesorte": extra_str = d.get("nomeTimeCoracaoMessorte") or d.get("mesSorte") or ""
                elif slug == "maismilionaria":
                    tr = d.get("trevos") or d.get("listaTrevos") or []
                    trevos_lista = [int(x) for x in tr] if tr else []

                return {
                    "conc": str(c), "data": dt, "dzs": [int(x) for x in dzs] if dzs else [],
                    "acum": d.get("acumulado") or d.get("acumulou"),
                    "arrec": d.get("valorArrecadado") or d.get("valor_arrecadado", 0),
                    "rates": d.get("listaRateioPremio") or d.get("premiacoes", []),
                    "p_data": p_data, "p_est": est_bruta,
                    "extra": extra_str, "trevos": trevos_lista
                }
        except: continue
    return None

# =========================================================================
# 4. INFRAESTRUTURA E "O CÉREBRO" DA IA
# =========================================================================
def preparar_infraestrutura():
    # 📂 PASTA 6: SISTEMA_ADM (A Planta da Casa)
    config_atual = db_call("GET", "SISTEMA_ADM/CONFIG_VISUAL_GLOBAL")
    if not isinstance(config_atual, dict):
        db_call("PUT", "SISTEMA_ADM/CONFIG_VISUAL_GLOBAL", {
            "tema_metalico": "padrao", "rodape_ativo": False, "rodape_texto": "Gerador Oficial"
        })

    # 📂 PASTA 7: CADASTRO_DE_CLIENTES (O Check-in)
    cadastros = db_call("GET", "CADASTRO_DE_CLIENTES")
    if not isinstance(cadastros, dict):
        db_call("PUT", "CADASTRO_DE_CLIENTES/info_sistema", {"criado_por": "Robô IA Trator", "status": "Pronto"})

def auditar_e_aprender(config, dezenas_reais):
    # 📂 PASTA 5: EVOLUCAO_DA_IA (O Cérebro)
    nome = config["nome"]
    jogos_antigos = db_call("GET", f"ESTATISTICAS/{nome}/jogos_prontos")
    pesos = db_call("GET", f"EVOLUCAO_DA_IA/{nome}/pesos") or {"peso_quentes": 0.4, "peso_atrasadas": 0.3}

    if jogos_antigos and dezenas_reais:
        reais_set = set(int(x) for x in dezenas_reais)
        acertos = sum(len(set(int(x) for x in j["numeros"] if isinstance(j, dict)).intersection(reais_set)) for j in jogos_antigos.values())
        media = acertos / len(jogos_antigos) if jogos_antigos else 0
        
        # Ajusta os pesos se a IA foi mal (menos que 30% de acerto base)
        if media < (config["qtd"] * 0.3):
            pesos["peso_quentes"] = max(0.1, pesos["peso_quentes"] - 0.05)
            pesos["peso_atrasadas"] = min(0.6, pesos["peso_atrasadas"] + 0.05)
        else:
            pesos["peso_quentes"] = min(0.7, pesos["peso_quentes"] + 0.05)
            pesos["peso_atrasadas"] = max(0.1, pesos["peso_atrasadas"] - 0.05)
            
    db_call("PATCH", f"EVOLUCAO_DA_IA/{nome}/pesos", pesos)
    return pesos

def motor_ia_profunda(slug, config, pesos):
    nome = config["nome"]
    hist = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome}")
    if not hist: return {}
    
    # ==============================================================
    # CORREÇÃO APLICADA: Tratamento para retorno de Lista ou Dict
    # ==============================================================
    if isinstance(hist, dict):
        lista_concursos = hist.values()
    elif isinstance(hist, list):
        lista_concursos = [c for c in hist if c is not None]
    else:
        return {}
    # ==============================================================
    
    todas_dz = []
    atrasos = {}
    inicio = 0 if slug in ["lotomania", "supersete"] else 1
    fim = 99 if slug == "lotomania" else (9 if slug == "supersete" else config.get("total", 60))
    
    # Iterando agora sobre a "lista_concursos" segura
    for concurso in lista_concursos:
        if isinstance(concurso, dict) and "dezenas" in concurso:
            dzs = [int(x) for x in concurso["dezenas"]]
            todas_dz.extend(dzs)
            for num in range(inicio, fim + 1):
                atrasos[num] = 0 if num in dzs else atrasos.get(num, 0) + 1

    quentes = [x[0] for x in Counter(todas_dz).most_common(30)]
    atrasadas = sorted(atrasos.keys(), key=lambda k: atrasos[k], reverse=True)[:20]
    
    candidatos, jogos_unicos = [], set()
    qtd, p_q, p_a = config["qtd"], pesos.get("peso_quentes", 0.4), pesos.get("peso_atrasadas", 0.3)
    
    while len(candidatos) < 50:
        pool = set(random.sample(quentes, min(len(quentes), int(qtd * p_q))))
        pool.update(random.sample(atrasadas, min(len(atrasadas), int(qtd * p_a))))
        while len(pool) < qtd: pool.add(random.randint(inicio, fim))
        
        jg = sorted(list(pool)[:qtd])
        assinatura = "-".join(str(x) for x in jg)
        
        if assinatura not in jogos_unicos:
            jogos_unicos.add(assinatura)
            candidatos.append(jg)
            
    palpites = {}
    for i, jg in enumerate(candidatos):
        obj = {
            "numeros": [f"{x:02d}" for x in jg],
            "status": "🔥 JOGO QUENTE (TOP 3)" if i < 3 else "IA CLOUD BLINDADA"
        }
        if "trevos" in config: obj["trevos"] = [f"{x:02d}" for x in sorted(random.sample(range(1, 7), 2))]
        palpites[f"jogo_{i+1:02d}"] = obj
    return palpites

# =========================================================================
# 5. O INSPETOR (Gatilho de Atualização)
# =========================================================================
def banco_com_dados_faltantes(ficha_banco):
    # Verifica se a "gaveta" existe, mas está oca ou vazia
    if not isinstance(ficha_banco, dict): return True
    if not ficha_banco.get("data"): return True
    if not ficha_banco.get("premiacoes") or len(ficha_banco.get("premiacoes")) == 0: return True
    if not ficha_banco.get("dezenas") or len(ficha_banco.get("dezenas")) == 0: return True
    return False

# =========================================================================
# 6. O MOTOR DE DISTRIBUIÇÃO (Alimenta as Pastas Oficiais)
# =========================================================================
def processar_vitoria(slug, config, d):
    nome = config["nome"]
    c_id = d["conc"]
    print(f"   🚀 Atualizando Nuvem Blindada: {nome} (Conc. {c_id})")

    ficha_base = {
        "numero": c_id, "data": d["data"], "dezenas": d["dzs"],
        "acumulou": "SIM" if d["acum"] else "NÃO",
        "arrecadacao": formatar_moeda(d["arrec"]), "premiacoes": d["rates"]
    }
    if slug == "timemania": ficha_base["timeCoracao"] = d["extra"]
    elif slug == "diadesorte": ficha_base["mesSorte"] = d["extra"]
    elif slug == "maismilionaria": ficha_base["trevos"] = d["trevos"]

    # 📂 PASTA 1: SORTEIO_DE_HOJE (Substituição Total)
    db_call("PUT", f"SORTEIO_DE_HOJE/{nome}", ficha_base)
    
    # 📂 PASTA 2: HISTORICOS_DE_SORTEIOS (Acumulativo)
    db_call("PUT", f"HISTORICOS_DE_SORTEIOS/{nome}/{c_id}", ficha_base)

    # 📂 PASTA 3: PROXIMO_CONCURSO (Limpeza e Troca)
    texto_est = f"Estimativa para {d['p_data']}" if d.get('p_data') else "A definir"
    db_call("PUT", f"PROXIMO_CONCURSO/{nome}", {"texto_data": texto_est, "valor_estimativa": formatar_moeda(d["p_est"])})

    # 📂 PASTA 4: ESTATISTICAS (Faxina com 50 jogos e Atualização da IA)
    pesos = auditar_e_aprender(config, d["dzs"])
    palpites_novos = motor_ia_profunda(slug, config, pesos)
    db_call("PUT", f"ESTATISTICAS/{nome}/jogos_prontos", palpites_novos)
    
    print(f"   ✅ Processo Concluído! Dados salvos nos 4 quadrantes.")

# =========================================================================
# 7. GESTOR PRINCIPAL
# =========================================================================
def main():
    try:
        agora_br = datetime.now(timezone.utc) - timedelta(hours=3)
        print(f"=============================================================")
        print(f"🤖 ROBÔ NUVEM BLINDADA - {agora_br.strftime('%d/%m/%Y %H:%M')}")
        print(f"=============================================================")

        preparar_infraestrutura()

        for slug, config in JOGOS.items():
            print(f"\n[Varredura] {config['nome']}")
            dados_reais = buscar_dados_loteria(slug)
            
            if dados_reais:
                hoje_db = db_call("GET", f"SORTEIO_DE_HOJE/{config['nome']}")
                conc_banco = str(hoje_db.get("numero", "")) if hoje_db else ""
                
                # A Lógica de Ouro: Atualiza se for NOVO ou se a nuvem estiver FALTANDO DADOS
                if dados_reais["conc"] != conc_banco or banco_com_dados_faltantes(hoje_db):
                    if dados_reais["conc"] == conc_banco:
                        print(f"   ⚠️ Reparando dados incompletos/rompidos no banco...")
                    processar_vitoria(slug, config, dados_reais)
                else:
                    print(f"   ✔️ 100% Íntegro. Nuvem atualizada com Conc. {dados_reais['conc']}")
            else:
                print(f"   🚨 Erro: API indisponível ou em atraso.")

        print(f"\n🏁 SESSÃO FINALIZADA COM SUCESSO.")
    except Exception as e:
        print(f"\n🚨 ERRO CAPTURADO: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
