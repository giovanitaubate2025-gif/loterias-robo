import requests
import json
import os
import random
from datetime import datetime, timedelta
from collections import Counter

print("=============================================================")
print("☁️ ROBÔ LOTERIAS NUVEM - SISTEMA DEFINITIVO CORRIGIDO ☁️")
print("=============================================================")

# =========================================================================
# 1. CONFIGURAÇÕES E CREDENCIAIS
# =========================================================================
SECRET_FIREBASE = os.environ.get('FIREBASE_KEY', '7gS8ASjfG5ZGRVu55Yj5QRw58ZzLCMBzWFLOyrfd')
URL_FIREBASE = "https://canal-da-loterias-default-rtdb.firebaseio.com/"

JOGOS = {
    "megasena": {"nome": "MEGA-SENA", "total_bolas": 60, "sorteio": 6},
    "lotofacil": {"nome": "LOTOFACIL", "total_bolas": 25, "sorteio": 15},
    "quina": {"nome": "QUINA", "total_bolas": 80, "sorteio": 5},
    "lotomania": {"nome": "LOTOMANIA", "total_bolas": 100, "sorteio": 20},
    "timemania": {"nome": "TIMEMANIA", "total_bolas": 80, "sorteio": 7},
    "diadesorte": {"nome": "DIA-DE-SORTE", "total_bolas": 31, "sorteio": 7},
    "maismilionaria": {"nome": "MAIS-MILIONARIA", "total_bolas": 50, "sorteio": 6},
    "duplasena": {"nome": "DUPLA-SENA", "total_bolas": 50, "sorteio": 6},
    "supersete": {"nome": "SUPER-SETE", "total_bolas": 9, "sorteio": 7}
}

# =========================================================================
# 2. FUNÇÕES DO FIREBASE (AS 4 GAVETAS)
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

def obter_data_hoje_brt():
    agora_utc = datetime.utcnow()
    agora_brt = agora_utc - timedelta(hours=3)
    return agora_brt.strftime("%d/%m/%Y")

def formatar_moeda(valor):
    try:
        v = float(valor)
        return f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return "R$ 0,00"

# =========================================================================
# 3. O CÉREBRO MATEMÁTICO (GERADOR DE 50 JOGOS)
# =========================================================================
def calcular_estatisticas(nome_jogo, config_jogo):
    historico = db_get(f"HISTORICOS_DE_SORTEIOS/{nome_jogo}")
    if not historico: return None

    todas_bolas = []
    inicio_bola = 0 if nome_jogo in ["LOTOMANIA", "SUPER-SETE"] else 1
    fim_bola = 99 if nome_jogo == "LOTOMANIA" else (9 if nome_jogo == "SUPER-SETE" else config_jogo["total_bolas"])
    atrasos = {i: 0 for i in range(inicio_bola, fim_bola + 1)}

    concursos = sorted([int(k) for k in historico.keys()])
    
    for num_conc in concursos:
        dezenas = historico[str(num_conc)].get("dezenas", [])
        todas_bolas.extend(dezenas)
        for b in range(inicio_bola, fim_bola + 1):
            if b in dezenas: atrasos[b] = 0
            else: atrasos[b] += 1

    frequencia = Counter(todas_bolas)
    limite = max(1, int((fim_bola - inicio_bola + 1) * 0.2))
    bolas_quentes = [b[0] for b in frequencia.most_common(limite)]
    bolas_atrasadas = sorted(atrasos, key=atrasos.get, reverse=True)[:limite]

    jogos_prontos = []
    tentativas = 0
    
    while len(jogos_prontos) < 50 and tentativas < 1000:
        tentativas += 1
        novo_jogo = set()
        qtd = config_jogo["sorteio"]
        
        novo_jogo.update(random.sample(bolas_quentes, min(max(1, int(qtd * 0.3)), len(bolas_quentes))))
        disp_atr = [b for b in bolas_atrasadas if b not in novo_jogo]
        novo_jogo.update(random.sample(disp_atr, min(max(1, int(qtd * 0.2)), len(disp_atr))))
        
        todas = list(range(inicio_bola, fim_bola + 1))
        disp_todas = [b for b in todas if b not in novo_jogo]
        falta = qtd - len(novo_jogo)
        if falta > 0: novo_jogo.update(random.sample(disp_todas, falta))
        
        jogo_ord = sorted(list(novo_jogo))
        if jogo_ord not in jogos_prontos: jogos_prontos.append(jogo_ord)

    payload = {}
    for i, jg in enumerate(jogos_prontos, 1):
        payload[f"jogo_{i:02d}"] = [f"{b:02d}" if b < 10 else str(b) for b in jg]
    return payload

# =========================================================================
# 4. FORÇAR CRIAÇÃO DAS ESTATÍSTICAS INICIAIS (A CORREÇÃO DO ERRO)
# =========================================================================
def forcar_criacao_estatisticas():
    print("\n🛠️ VERIFICANDO SE A GAVETA 'ESTATISTICAS' EXISTE NO FIREBASE...")
    for api_nome, config in JOGOS.items():
        nome_jogo = config["nome"]
        
        # O robô olha no banco de dados
        pasta_existe = db_get(f"ESTATISTICAS/{nome_jogo}/jogos_prontos")
        
        # Se a pasta não existir, ele vai ler o histórico que VOCÊ subiu e vai criar!
        if not pasta_existe:
            print(f"   ⚠️ Pasta ESTATISTICAS faltando para {nome_jogo}. Criando na marra agora!")
            jogos_novos = calcular_estatisticas(nome_jogo, config)
            if jogos_novos:
                db_put(f"ESTATISTICAS/{nome_jogo}/jogos_prontos", jogos_novos)
                print(f"   ✅ Pasta criada e 50 jogos salvos para {nome_jogo}!")
        else:
            print(f"   ✔️ {nome_jogo}: A pasta ESTATISTICAS já está lá.")

# =========================================================================
# 5. O EFEITO DOMINÓ (A REAÇÃO EM CADEIA PARA NOVOS SORTEIOS)
# =========================================================================
def executar_efeito_domino(api_nome, config_jogo, dados_api):
    nome_jogo = config_jogo["nome"]
    num_conc = str(dados_api.get('concurso'))
    print(f"\n🔥 [EFEITO DOMINÓ] -> {nome_jogo} (Concurso {num_conc})")

    faixas_premio = []
    for p in dados_api.get('premiacoes', []):
        faixas_premio.append({
            "faixa": str(p.get('descricao', '')),
            "ganhadores": p.get('ganhadores', 0),
            "valor": float(p.get('valorPremio', 0))
        })

    ficha_completa = {
        "numero": num_conc,
        "data": str(dados_api.get('data', ''))[:10],
        "dezenas": [int(x) for x in dados_api.get('dezenas', [])],
        "premiacoes": faixas_premio,
        "acumulou": "SIM" if dados_api.get('acumulou') else "NÃO",
        "arrecadacao_total": float(dados_api.get('valorArrecadado', 0))
    }

    if dados_api.get("trevos"): ficha_completa["trevos"] = [int(x) for x in dados_api["trevos"]]
    if dados_api.get("time_do_coracao"): ficha_completa["time_do_coracao"] = dados_api["time_do_coracao"]
    if dados_api.get("mes_da_sorte"): ficha_completa["mes_da_sorte"] = dados_api["mes_da_sorte"]

    db_put(f"SORTEIO_DE_HOJE/{nome_jogo}", ficha_completa)
    db_patch(f"HISTORICOS_DE_SORTEIOS/{nome_jogo}", {num_conc: ficha_completa})

    val_est = dados_api.get('valor_estimado_proximo_concurso', 0)
    data_prox = str(dados_api.get('data_proximo_concurso', 'A definir'))
    db_put(f"PROXIMO_CONCURSO/{nome_jogo}", {
        "numero_concurso": str(int(num_conc) + 1),
        "data_proximo_sorteio": data_prox if data_prox else "A definir",
        "estimativa_premio": formatar_moeda(val_est)
    })

    db_delete(f"ESTATISTICAS/{nome_jogo}/jogos_prontos")
    jogos_novos = calcular_estatisticas(nome_jogo, config_jogo)
    if jogos_novos:
        db_put(f"ESTATISTICAS/{nome_jogo}/jogos_prontos", jogos_novos)
    
    print(f"🎯 SUCESSO ABSOLUTO! {nome_jogo} está 100% atualizado.")

# =========================================================================
# 6. O MOTOR PRINCIPAL DA NUVEM
# =========================================================================
def rodar_robo_nuvem():
    hoje_str = obter_data_hoje_brt()
    print(f"📅 Data atual (Brasília): {hoje_str}")
    
    # 1º Passo: Força a criação das estatísticas se faltarem (A correção)
    forcar_criacao_estatisticas()
    
    # 2º Passo: Segue a vida normal caçando sorteios novos
    proximos = db_get("PROXIMO_CONCURSO") or {}
    
    for api_nome, config in JOGOS.items():
        nome_jogo = config["nome"]
        data_marcada = proximos.get(nome_jogo, {}).get("data_proximo_sorteio", "")
        
        if data_marcada == hoje_str or "definir" in data_marcada.lower() or not data_marcada:
            print(f"\n🔍 Verificando alvo: {nome_jogo}")
            try:
                res = requests.get(f"https://brasilapi.com.br/api/loterias/v1/{api_nome}", timeout=15)
                if res.status_code == 200:
                    dados_api = res.json()
                    conc_api = str(dados_api.get('concurso'))
                    
                    vitrine = db_get(f"SORTEIO_DE_HOJE/{nome_jogo}")
                    conc_vitrine = str(vitrine.get("numero", "")) if vitrine else ""
                    
                    if conc_api != conc_vitrine:
                        executar_efeito_domino(api_nome, config, dados_api)
                    else:
                        print(f"   ⏳ Sem sorteio novo para {nome_jogo}.")
            except Exception as e:
                print(f"   🚨 Falha na API: {e}")

    print("\n🏁 TAREFA CONCLUÍDA! Desligando...")

if __name__ == "__main__":
    rodar_robo_nuvem()
