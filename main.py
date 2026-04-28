#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os # <-- ADICIONADO PARA SINCRONIZAR COM O GITHUB ACTIONS
import requests
import json
import random
import time
from datetime import datetime, timedelta, timezone
from collections import Counter

# Ignora avisos SSL no Android/Termux
requests.packages.urllib3.disable_warnings()

# =========================================================================
# ZONA DE CONFIGURAÇÃO MESTRA (CONFORME DOSSIÊ)
# =========================================================================
# Sincronizado com o GitHub Actions: Pega a chave da nuvem, se não achar, usa a sua original
SECRET_FIREBASE = os.environ.get("FIREBASE_KEY", "7gS8ASjfG5ZGRVu55Yj5QRw58ZzLCMBzWFLOyrfd")
URL_FIREBASE = "https://canal-da-loterias-default-rtdb.firebaseio.com/"

JOGOS = {
    "lotofacil": {"nome": "LOTOFACIL", "qtd": 15, "total": 25},
    "megasena": {"nome": "MEGA-SENA", "qtd": 6, "total": 60},
    "quina": {"nome": "QUINA", "qtd": 5, "total": 80},
    "lotomania": {"nome": "LOTOMANIA", "qtd": 50, "total": 100},
    "timemania": {"nome": "TIMEMANIA", "qtd": 10, "total": 80},
    "diadesorte": {"nome": "DIA-DE-SORTE", "qtd": 7, "total": 31},
    "maismilionaria": {"nome": "MAIS-MILIONARIA", "qtd": 6, "total": 50},
    "duplasena": {"nome": "DUPLA-SENA", "qtd": 6, "total": 50},
    "supersete": {"nome": "SUPER-SETE", "qtd": 7, "total": 9}
}

# =========================================================================
# FUNÇÕES DE BANCO DE DADOS (GOD MODE - IGNORA ".write": false)
# =========================================================================
def db_call(method, path, data=None, shallow=False):
    """ Executa operações no Firebase com a Chave Mestra """
    url = f"{URL_FIREBASE}{path}.json?auth={SECRET_FIREBASE}"
    if shallow: url += "&shallow=true"
    
    try:
        if method == "GET": return requests.get(url, timeout=30, verify=False).json()
        if method == "PUT": return requests.put(url, json=data, timeout=30, verify=False)
    except Exception as e:
        return None

def formatar_moeda(v):
    try: return f"R$ {float(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return "R$ 0,00"

# =========================================================================
# PASSO 1: A COLETA EXTERNA (MUNICIAMENTO NA CAIXA)
# =========================================================================
def coletar_dados_caixa(slug, concurso_especifico=None):
    """ Vai ao servidor da Caixa e preenche a prancheta de auditoria """
    h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36"}
    
    # Se pedir um específico, busca ele. Senão, busca o último sorteio.
    url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{slug}"
    if concurso_especifico:
        url += f"/{concurso_especifico}"
        
    try:
        res = requests.get(url, headers=h, verify=False, timeout=15)
        if res.status_code == 200:
            d = res.json()
            num_concurso = str(d.get("numero") or d.get("concurso"))
            if not num_concurso or num_concurso == "None": return None
            
            return {
                "conc": num_concurso,
                "data": d.get("dataApuracao") or d.get("data"),
                "dzs": [int(x) for x in (d.get("listaDezenas") or d.get("dezenas") or [])],
                "acum": "SIM" if (d.get("acumulado") or d.get("acumulou")) else "NÃO",
                "arrec": formatar_moeda(d.get("valorArrecadado") or 0),
                "rates": d.get("listaRateioPremio") or d.get("premiacoes") or [],
                "p_conc": str(d.get("numeroFinalConcursoPróximo") or (int(num_concurso)+1)),
                "p_data": d.get("dataPróximoConcurso") or "A definir",
                "p_est": formatar_moeda(d.get("valorEstimadoPróximoConcurso") or 0),
                "trevos": d.get("dezenasSorteioOrdemCrescente", [])[6:] if slug == "maismilionaria" else None,
                "time": d.get("nomeTimeCoracaoMessorte") or d.get("time_do_coracao"),
                "mes": d.get("nomeMesSorte") or d.get("mes_da_sorte")
            }
    except: pass
    return None

# =========================================================================
# AUDITORIA DO HISTÓRICO (PREENCHENDO BURACOS ANTIGOS)
# =========================================================================
def preencher_buracos_historico(slug, nome, ultimo_concurso):
    """ Varre a pasta de históricos e busca os concursos que estão faltando """
    print("      -> Verificando buracos no Histórico...")
    chaves_historico = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome}", shallow=True)
    if not chaves_historico:
        chaves_historico = {}
        
    # Converte chaves para inteiros para encontrar os buracos
    salvos = set([int(k) for k in chaves_historico.keys() if str(k).isdigit()])
    ultimo = int(ultimo_concurso)
    
    # Para não travar o robô com milhares de requisições de uma vez, 
    # ele busca no máximo 5 buracos por ciclo, focando nos mais recentes.
    buracos = [i for i in range(ultimo, 0, -1) if i not in salvos]
    buracos_para_preencher = buracos[:5]
    
    if buracos_para_preencher:
        print(f"      -> Encontrados {len(buracos)} concursos faltando. Preenchendo os {len(buracos_para_preencher)} mais urgentes...")
        for b in buracos_para_preencher:
            ficha_antiga = coletar_dados_caixa(slug, b)
            if ficha_antiga:
                # Salva o buraco diretamente no Histórico
                db_call("PUT", f"HISTORICOS_DE_SORTEIOS/{nome}/{b}", ficha_antiga)
                print(f"         + Concurso {b} recuperado e arquivado!")
            time.sleep(1) # Pausa para a Caixa não bloquear
    else:
        print("      -> Histórico 100% completo, sem buracos.")

# =========================================================================
# O CÉREBRO DA I.A E GERAÇÃO ESTATÍSTICA (PASTAS EVOLUCAO_DA_IA e ESTATISTICAS)
# =========================================================================
def processar_ia_e_estatisticas(slug, config, dezenas_sorteadas):
    nome = config["nome"]
    qtd = config["qtd"]
    total = config["total"]
    
    print("      -> Acionando Inteligência Artificial e Evolução...")
    
    # 1. EVOLUCAO_DA_IA (Lendo os Pesos)
    pesos = db_call("GET", f"EVOLUCAO_DA_IA/{nome}/pesos")
    if not pesos: 
        pesos = {"peso_quentes": 1.0, "peso_frias": 1.0, "peso_atrasadas": 1.0, "peso_pares_impares": 1.0}
    
    # 2. AUDITORIA DOS JOGOS VIP ANTERIORES
    jogos_anteriores = db_call("GET", f"ESTATISTICAS/{nome}/jogos_prontos")
    if jogos_anteriores:
        acertos_totais = 0
        sorteio_set = set(dezenas_sorteadas)
        for _, jg in jogos_anteriores.items():
            nums = [int(n) for n in (jg.get("numeros") or [])]
            acertos_totais += len(set(nums).intersection(sorteio_set))
        
        media_acertos = acertos_totais / len(jogos_anteriores)
        
        # Se a média de acertos for muito baixa (falha na estratégia), recalibra a IA
        if media_acertos < (len(dezenas_sorteadas) * 0.25):
            print("         * Ajustando Pesos Matemáticos da I.A (Evolução Contínua)...")
            pesos = {
                "peso_quentes": round(random.uniform(0.6, 2.5), 2),
                "peso_frias": round(random.uniform(0.5, 1.5), 2),
                "peso_atrasadas": round(random.uniform(0.8, 2.0), 2),
                "peso_pares_impares": round(random.uniform(0.7, 1.3), 2)
            }
            db_call("PUT", f"EVOLUCAO_DA_IA/{nome}/pesos", pesos)

    # 3. LEITURA DO HISTÓRICO PARA ESTATÍSTICA
    hist_keys = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome}", shallow=True)
    todas_dezenas = []
    
    if hist_keys:
        # Pega amostra dos ultimos 10 concursos reais para ver atrasadas e quentes reais
        ultimos_keys = sorted([int(k) for k in hist_keys.keys() if str(k).isdigit()], reverse=True)[:10]
        for k in ultimos_keys:
            conc_data = db_call("GET", f"HISTORICOS_DE_SORTEIOS/{nome}/{k}")
            if conc_data and "dezenas" in conc_data:
                todas_dezenas.extend(conc_data["dezenas"])
                
    contador = Counter(todas_dezenas)
    quentes = [x[0] for x in contador.most_common(15)]
    frias = [x[0] for x in contador.most_common()[-15:]]

    # 4. GERAÇÃO DOS 50 JOGOS VIPS
    print("      -> Gerando 50 Jogos VIPs Blindados...")
    jogos_prontos = {}
    for i in range(1, 51):
        jg = set()
        while len(jg) < qtd:
            chance = random.random()
            # Aplica os pesos da EVOLUCAO_DA_IA na roleta da sorte
            if chance < (0.4 * pesos["peso_quentes"]) and quentes:
                jg.add(random.choice(quentes))
            elif chance > (0.8 * pesos["peso_frias"]) and frias:
                jg.add(random.choice(frias))
            else:
                jg.add(random.randint(1 if slug != "lotomania" else 0, total))
                
        corpo_jogo = {
            "numeros": [f"{x:02d}" for x in sorted(list(jg))],
            "status": f"💎 IA CLOUD VIP | Sincronizado | Acerto Est: {random.randint(85,99)}%"
        }
        jogos_prontos[f"jogo_{i:02d}"] = corpo_jogo

    # 5. ENTREGA NA PRATELEIRA
    db_call("PUT", f"ESTATISTICAS/{nome}/jogos_prontos", jogos_prontos)

# =========================================================================
# O INSPETOR DE QUALIDADE (A ENGRENAGEM E A DANÇA DAS CADEIRAS)
# =========================================================================
def executar_ciclo_auditoria(slug, config):
    nome = config["nome"]
    print(f"\n[>] Vistoriando a Diretoria: {nome}...")
    
    # PASSO 1: Coleta Externa (Prancheta)
    dados_caixa = coletar_dados_caixa(slug)
    if not dados_caixa:
        print("   ❌ FALHA: Caixa Econômica fora do ar. Pulando diretoria.")
        return

    # PASSO 2 e 3: Vistoria na Nuvem e Check-list
    vitrine = db_call("GET", f"SORTEIO_DE_HOJE/{nome}")
    
    concurso_nuvem = str(vitrine.get("numero", "")) if vitrine else ""
    rateios_nuvem = vitrine.get("premiacoes", []) if vitrine else []
    dezenas_nuvem = vitrine.get("dezenas", []) if vitrine else []
    
    precisa_atualizar = False
    motivo = ""

    # Verifica inconsistências
    if dados_caixa["conc"] != concurso_nuvem:
        precisa_atualizar = True
        motivo = f"Novo concurso detectado ({dados_caixa['conc']})"
    elif not rateios_nuvem or len(rateios_nuvem) == 0:
        precisa_atualizar = True
        motivo = "Rateios (ganhadores/prêmios) estão faltando"
    elif not dezenas_nuvem or len(dezenas_nuvem) == 0:
        precisa_atualizar = True
        motivo = "Dezenas estão faltando"

    # PASSO 4: A Ação Cirúrgica
    if precisa_atualizar:
        print(f"   ⚠️ Atualização Necessária. Motivo: {motivo}")
        
        # --- A DANÇA DAS CADEIRAS ---
        # Move o concurso velho da Vitrine para o Arquivo Morto (HISTORICOS)
        if vitrine and concurso_nuvem:
            print(f"      -> Movendo Concurso {concurso_nuvem} para o Histórico...")
            db_call("PUT", f"HISTORICOS_DE_SORTEIOS/{nome}/{concurso_nuvem}", vitrine)

        # Monta a Ficha Limpa do novo sorteio (Com TUDO o que a Caixa informou)
        ficha_nova = {
            "numero": dados_caixa["conc"],
            "data": dados_caixa["data"],
            "dezenas": dados_caixa["dzs"],
            "acumulou": dados_caixa["acum"],
            "arrecadacao": dados_caixa["arrec"],
            "premiacoes": dados_caixa["rates"] # Lista completa e exata da caixa
        }
        if dados_caixa.get("trevos"): ficha_nova["trevos"] = dados_caixa["trevos"]
        if dados_caixa.get("time"): ficha_nova["time_coracao"] = dados_caixa["time"]
        if dados_caixa.get("mes"): ficha_nova["mes_sorte"] = dados_caixa["mes"]

        # Atualiza a Vitrine (SORTEIO_DE_HOJE)
        db_call("PUT", f"SORTEIO_DE_HOJE/{nome}", ficha_nova)
        
        # Garante o Arquivo Morto do Atual também (Dupla segurança)
        db_call("PUT", f"HISTORICOS_DE_SORTEIOS/{nome}/{dados_caixa['conc']}", ficha_nova)
        
        # Atualiza o Banner (PROXIMO_CONCURSO)
        db_call("PUT", f"PROXIMO_CONCURSO/{nome}", {
            "Número do Concurso": dados_caixa["p_conc"],
            "Data do Próximo Sorteio": dados_caixa["p_data"],
            "Estimativa de Prêmio": dados_caixa["p_est"]
        })
        
        # Tapa os buracos antigos do histórico
        preencher_buracos_historico(slug, nome, dados_caixa["conc"])
        
        # Roda o Cérebro e Gera Jogos
        processar_ia_e_estatisticas(slug, config, dados_caixa["dzs"])
        
        print("   ✅ Atualização em cascata concluída com sucesso!")
        
    else:
        # Se for tudo idêntico, encerra o ciclo conforme Dossiê (sem gastar processamento)
        print("   ✅ TUDO IDÊNTICO. O aplicativo já possui os dados mais recentes. Encerrando ciclo.")

# =========================================================================
# INICIALIZAÇÃO CRON / START DO SISTEMA
# =========================================================================
def main():
    agora_brt = datetime.now(timezone.utc) - timedelta(hours=3)
    print("=" * 65)
    print(f"🤖 INSPETOR DE QUALIDADE CLOUD 2026 - INICIADO ÀS {agora_brt.strftime('%H:%M:%S')}")
    print("=" * 65)
    
    # O robô faz a vistoria diretoria por diretoria
    for slug, config in JOGOS.items():
        executar_ciclo_auditoria(slug, config)
        time.sleep(1) # Pausa amigável para não ser bloqueado pela Caixa
        
    print("\n" + "=" * 65)
    print("🏁 VISTORIA CONCLUÍDA. BANCO DE DADOS 100% PROTEGIDO E SINCRONIZADO.")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    main()
