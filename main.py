import requests
import json
import os
from datetime import datetime
import random
from collections import Counter

print("=============================================================")
print("☁️ ROBÔ LOTERIAS NUVEM (GITHUB ACTIONS) ATIVADO ☁️")
print("=============================================================")

# Pega a chave secreta do GitHub Secrets (como está no seu print) ou usa a fixa
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

def formatar_moeda(valor):
    try:
        v = float(valor)
        return f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return "R$ 0,00"

def calcular_estatisticas(nome_jogo, config_jogo):
    print(f"   🧠 {nome_jogo}: Calculando 50 Jogos...")
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

def executar_efeito_domino(api_nome, config_jogo, dados_api):
    nome_jogo = config_jogo["nome"]
    num_conc = str(dados_api.get('concurso'))
    print(f"\n🔥 [EFEITO DOMINÓ] -> {nome_jogo} (Concurso {num_conc})")

    ficha = {
        "numero": num_conc,
        "data": str(dados_api.get('data', ''))[:10],
        "dezenas": [int(x) for x in dados_api.get('dezenas', [])],
        "premiacoes": [{"faixa": str(p.get('descricao', '')), "valor": float(p.get('valorPremio', 0))} for p in dados_api.get('premiacoes', [])],
        "acumulou": "SIM" if dados_api.get('acumulou') else "NÃO"
    }

    if dados_api.get("trevos"): ficha["trevos"] = [int(x) for x in dados_api["trevos"]]
    if dados_api.get("time_do_coracao"): ficha["time_do_coracao"] = dados_api["time_do_coracao"]
    if dados_api.get("mes_da_sorte"): ficha["mes_da_sorte"] = dados_api["mes_da_sorte"]

    db_put(f"SORTEIO_DE_HOJE/{nome_jogo}", ficha)
    db_patch(f"HISTORICOS_DE_SORTEIOS/{nome_jogo}", {num_conc: ficha})

    val_est = dados_api.get('valor_estimado_proximo_concurso', 0)
    data_prox = str(dados_api.get('data_proximo_concurso', 'A definir'))
    db_put(f"PROXIMO_CONCURSO/{nome_jogo}", {
        "numero_concurso": str(int(num_conc) + 1),
        "data_proximo_sorteio": data_prox if data_prox else "A definir",
        "estimativa_premio": formatar_moeda(val_est)
    })

    db_delete(f"ESTATISTICAS/{nome_jogo}/jogos_prontos")
    jogos_novos = calcular_estatisticas(nome_jogo, config_jogo)
    if jogos_novos: db_put(f"ESTATISTICAS/{nome_jogo}/jogos_prontos", jogos_novos)
    print(f"✅ Atualização concluída para {nome_jogo}")

def rodar_robo_nuvem():
    hoje_str = datetime.now().strftime("%d/%m/%Y")
    proximos = db_get("PROXIMO_CONCURSO") or {}
    
    for api_nome, config in JOGOS.items():
        nome_jogo = config["nome"]
        data_marcada = proximos.get(nome_jogo, {}).get("data_proximo_sorteio", "")
        
        # Se tem sorteio hoje, atrasado ou indefinido, ele checa!
        if data_marcada == hoje_str or "definir" in data_marcada.lower() or not data_marcada:
            print(f"🔍 Checando alvo: {nome_jogo}")
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
                        print(f"   - Sorteio novo ainda não liberado pela Caixa.")
            except:
                print(f"   - Erro de conexão com a API para {nome_jogo}")

    print("🏁 Execução do GitHub Actions finalizada.")

if __name__ == "__main__":
    rodar_robo_nuvem()
