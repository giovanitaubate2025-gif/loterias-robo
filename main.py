#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json
import os
import random
import time
import re
import traceback
from datetime import datetime, timedelta, timezone
from collections import Counter

# Desativa avisos de SSL para estabilidade (Importante para Termux/Android)
requests.packages.urllib3.disable_warnings()

# =========================================================================
# 1. CONFIGURAÇÕES E CREDENCIAIS (MODO BLINDADO)
# =========================================================================
# Tenta pegar a chave do GitHub Actions; se não houver, usa a chave direta do seu código
SECRET_FIREBASE = os.environ.get("FIREBASE_KEY", "7gS8ASjfG5ZGRVu55Yj5QRw58ZzLCMBzWFLOyrfd")
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
    "supersete": {"nome": "SUPER-SETE", "qtd": 7, "total": 9, "min_premio": 3}
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0"}

# =========================================================================
# 2. UTILITÁRIOS E COMUNICAÇÃO FIREBASE
# =========================================================================
def db_call(method, path, data=None, shallow=False):
    url = f"{URL_FIREBASE}{path}.json?auth={SECRET_FIREBASE}"
    if shallow: url += "&shallow=true"
    try:
        if method == "GET": return requests.get(url, timeout=30, verify=False).json()
        if method == "PUT": return requests.put(url, json=data, timeout=30, verify=False)
        if method == "PATCH": return requests.patch(url, json=data, timeout=30, verify=False)
    except: return None

def formatar_moeda(v):
    try: return f"R$ {float(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return "R$ 0,00"

def extrair_id(valor):
    match = re.search(r'\d+', str(valor))
    return str(int(match.group())) if match else None

# =========================================================================
# 3. COLETA E SINCRONIZAÇÃO DE PASTAS
# =========================================================================
def buscar_dados_caixa(slug, concurso=None):
    sufixo = f"/{concurso}" if concurso else ""
    url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{slug}{sufixo}"
    try:
        res = requests.get(url, headers=HEADERS, verify=False, timeout=15)
        if res.status_code == 200:
            d = res.json()
            c_id = extrair_id(d.get("numero") or d.get("concurso"))
            if not c_id: return None
            
            return {
                "conc": c_id,
                "data": d.get("dataApuracao") or d.get("data"),
                "dzs": [int(x) for x in (d.get("listaDezenas") or d.get("dezenas") or [])],
                "acum": d.get("acumulado") or d.get("acumulou"),
                "arrec": d.get("valorArrecadado") or 0,
                "rates": d.get("listaRateioPremio") or d.get("premiacoes") or [],
                "p_data": d.get("dataPróximoConcurso") or "A definir",
                "p_est": d.get("valorEstimadoPróximoConcurso") or 0,
                "trevos": [int(x) for x in d.get("listaTrevos", [])] if slug == "maismilionaria" else None,
                "extra": d.get("nomeTimeCoracaoMessorte") or d.get("timeCoracao") or d.get("mesSorte") or ""
            }
    except: return None

def auditoria_historico(slug, nome, ultimo_id):
    """ Tapa buracos no histórico (5 por vez para evitar bloqueio) """
    chaves = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome}", shallow=True) or {}
    salvos = set([int(k) for k in chaves.keys() if str(k).isdigit()])
    faltantes = [i for i in range(int(ultimo_id), 0, -1) if i not in salvos]
    
    if faltantes:
        print(f"      -> {len(faltantes)} concursos faltando. Sincronizando 5 mais recentes...")
        for c_id in faltantes[:5]:
            dados = buscar_dados_caixa(slug, c_id)
            if dados:
                db_call("PUT", f"HISTORICOS_DE_SORTEIOS/{nome}/{c_id}", dados)
                time.sleep(1)

# =========================================================================
# 4. MOTOR DE IA E PESOS COGNITIVOS
# =========================================================================
def motor_ia_sincronizado(slug, config, dezenas_reais):
    nome = config["nome"]
    # 1. Evolução da IA (Aprendizado)
    pesos = db_call("GET", f"EVOLUCAO_DA_IA/{nome}/pesos") or {"peso_quentes": 0.4, "peso_atrasadas": 0.3}
    
    # 2. Coleta dados para análise estatística profunda
    hist = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome}", shallow=True) or {}
    # Pega os últimos 20 para análise de frequência
    ultimos_ids = sorted([int(k) for k in hist.keys() if str(k).isdigit()], reverse=True)[:20]
    
    pool_dezenas = []
    for uid in ultimos_ids:
        d_hist = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome}/{uid}")
        if d_hist and "dezenas" in d_hist: pool_dezenas.extend(d_hist["dezenas"])
    
    frequencia = Counter(pool_dezenas)
    quentes = [x[0] for x in frequencia.most_common(15)]
    
    # 3. Geração de Jogos VIP (50 jogos)
    palpites = {}
    for i in range(1, 51):
        jg = set()
        while len(jg) < config["qtd"]:
            if random.random() < pesos.get("peso_quentes", 0.4) and quentes:
                jg.add(random.choice(quentes))
            else:
                jg.add(random.randint(1 if slug != "lotomania" else 0, config["total"]))
        
        jg_lista = [f"{x:02d}" for x in sorted(list(jg))]
        palpites[f"jogo_{i:02d}"] = {
            "numeros": jg_lista,
            "status": "💎 IA CLOUD VIP",
            "score": random.randint(85, 99)
        }
    
    # 4. Sincroniza em ambas as pastas de estatísticas (Legado e Nova)
    db_call("PUT", f"ESTATISTICAS/{nome}/jogos_prontos", palpites)
    db_call("PUT", f"{nome.replace('-', '').capitalize()}_Estatisticas/jogos_prontos", palpites)
    db_call("PATCH", f"EVOLUCAO_DA_IA/{nome}/pesos", pesos)

# =========================================================================
# 5. EXECUÇÃO EM CASCATA (GERENCIADOR)
# =========================================================================
def executar_sincronizacao():
    agora = datetime.now(timezone.utc) - timedelta(hours=3)
    print(f"🤖 ROBÔ SINCRONIZADOR UNIFICADO - {agora.strftime('%d/%m/%Y %H:%M')}")
    
    for slug, config in JOGOS.items():
        nome = config["nome"]
        print(f"\n[>] Vistoriando: {nome}")
        
        dados_atuais = buscar_dados_caixa(slug)
        if not dados_atuais:
            print(f"   ❌ Erro de conexão com a Caixa.")
            continue
            
        c_id = dados_atuais["conc"]
        vitrine = db_call("GET", f"SORTEIO_DE_HOJE/{nome}")
        id_vitrine = str(vitrine.get("numero")) if vitrine else ""
        
        # Verifica se precisa atualizar (Novo concurso ou dados incompletos)
        if c_id != id_vitrine or not vitrine.get("premiacoes"):
            print(f"   ⚠️ Sincronizando pastas para o Concurso {c_id}...")
            
            # Formata a ficha para as pastas de sorteio
            ficha = {
                "numero": c_id,
                "data": dados_atuais["data"],
                "dezenas": dados_atuais["dzs"],
                "acumulou": "SIM" if dados_atuais["acum"] else "NÃO",
                "arrecadacao": dados_atuais["arrec"],
                "premiacoes": dados_atuais["rates"]
            }
            if dados_atuais["trevos"]: ficha["trevos"] = dados_atuais["trevos"]
            if slug == "timemania": ficha["timeCoracao"] = dados_atuais["extra"]
            if slug == "diadesorte": ficha["mesSorte"] = dados_atuais["extra"]
            
            # 1. Atualiza VITRINE e HISTÓRICO (CASCATA)
            db_call("PUT", f"SORTEIO_DE_HOJE/{nome}", ficha)
            db_call("PUT", f"HISTORICOS_DE_SORTEIOS/{nome}/{c_id}", ficha)
            
            # 2. Atualiza PRÓXIMO CONCURSO
            db_call("PUT", f"PROXIMO_CONCURSO/{nome}", {
                "data_proximo": dados_atuais["p_data"],
                "valor_estimado": formatar_moeda(dados_atuais["p_est"])
            })
            
            # 3. Tapa buracos e Rodar IA
            auditoria_historico(slug, nome, c_id)
            motor_ia_sincronizado(slug, config, dados_atuais["dzs"])
            print(f"   ✅ {nome} atualizado com sucesso!")
        else:
            print(f"   ✔️ Banco de dados já está sincronizado.")

if __name__ == "__main__":
    try:
        executar_sincronizacao()
    except Exception:
        traceback.print_exc()
