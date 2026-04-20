import requests
import json
import time
from datetime import datetime
import random
from collections import Counter

print("=============================================================")
print("🤖 ROBÔ LOTERIAS OFICIAL - SISTEMA MESTRE ATIVADO 🤖")
print("=============================================================")
print("Iniciando carregamento das regras de negócio...")

# =========================================================================
# 1. CONFIGURAÇÕES DO BANCO DE DADOS E JOGOS
# =========================================================================
URL_FIREBASE = "https://canal-da-loterias-default-rtdb.firebaseio.com/"
SECRET_FIREBASE = "7gS8ASjfG5ZGRVu55Yj5QRw58ZzLCMBzWFLOyrfd"

# Lista oficial com as regras para o Motor Matemático
JOGOS = {
    "megasena": {"nome": "MEGA-SENA", "total_bolas": 60, "sorteio": 6},
    "lotofacil": {"nome": "LOTOFACIL", "total_bolas": 25, "sorteio": 15},
    "quina": {"nome": "QUINA", "total_bolas": 80, "sorteio": 5},
    "lotomania": {"nome": "LOTOMANIA", "total_bolas": 100, "sorteio": 20}, # Lotomania vai de 00 a 99
    "timemania": {"nome": "TIMEMANIA", "total_bolas": 80, "sorteio": 7},
    "diadesorte": {"nome": "DIA-DE-SORTE", "total_bolas": 31, "sorteio": 7},
    "maismilionaria": {"nome": "MAIS-MILIONARIA", "total_bolas": 50, "sorteio": 6},
    "duplasena": {"nome": "DUPLA-SENA", "total_bolas": 50, "sorteio": 6},
    "supersete": {"nome": "SUPER-SETE", "total_bolas": 9, "sorteio": 7} # Colunas de 0 a 9
}

# Memória do robô: guarda quais jogos têm sorteio hoje
alvos_do_dia = [] 

# =========================================================================
# 2. FUNÇÕES DE COMUNICAÇÃO COM O FIREBASE (Criação Automática)
# =========================================================================
def db_get(caminho):
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try:
        res = requests.get(url, timeout=20)
        return res.json() if res.status_code == 200 else None
    except: return None

def db_put(caminho, dados):
    # PUT substitui tudo o que está na pasta ou CRIA a pasta se não existir
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try: requests.put(url, json=dados, timeout=20)
    except Exception as e: print(f"Erro ao salvar em {caminho}: {e}")

def db_patch(caminho, dados):
    # PATCH adiciona dados sem apagar os que já lá estão (Ideal para o Histórico)
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try: requests.patch(url, json=dados, timeout=20)
    except Exception as e: print(f"Erro ao atualizar {caminho}: {e}")

def db_delete(caminho):
    # Apaga uma pasta específica (Usado na faxina das estatísticas)
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try: requests.delete(url, timeout=20)
    except: pass

def moeda_br(valor):
    try:
        v = float(valor)
        return f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return "R$ 0,00"

# =========================================================================
# 3. O CÉREBRO MATEMÁTICO (Estatísticas e 50 Jogos)
# =========================================================================
def calcular_estatisticas(nome_jogo, config_jogo):
    print(f"   🧠 {nome_jogo}: Iniciando Matemática Profunda...")
    
    # Puxa o histórico completo para análise
    historico = db_get(f"HISTORICOS_DE_SORTEIOS/{nome_jogo}")
    if not historico:
        print(f"   ⚠️ {nome_jogo}: Histórico vazio. Não é possível gerar estatísticas.")
        return None

    todas_as_bolas_sorteadas = []
    
    # Ajuste de regras para Lotomania (0-99) e Super Sete (0-9)
    inicio_bola = 0 if nome_jogo in ["LOTOMANIA", "SUPER-SETE"] else 1
    fim_bola = 99 if nome_jogo == "LOTOMANIA" else (9 if nome_jogo == "SUPER-SETE" else config_jogo["total_bolas"])
    
    atrasos = {i: 0 for i in range(inicio_bola, fim_bola + 1)}

    concursos = sorted([int(k) for k in historico.keys()])
    
    # 1. Varredura do Começo ao Fim
    for num_conc in concursos:
        dados = historico[str(num_conc)]
        dezenas = dados.get("dezenas", [])
        
        todas_as_bolas_sorteadas.extend(dezenas)
        
        # Calcula o Delay (Atraso)
        for b in range(inicio_bola, fim_bola + 1):
            if b in dezenas:
                atrasos[b] = 0 # Zerou o atraso porque saiu
            else:
                atrasos[b] += 1 # Soma 1 concurso de atraso

    frequencia = Counter(todas_as_bolas_sorteadas)
    
    # 2. Define as Quentes e Atrasadas (Top 20%)
    limite = max(1, int((fim_bola - inicio_bola + 1) * 0.2))
    bolas_quentes = [b[0] for b in frequencia.most_common(limite)]
    bolas_atrasadas = sorted(atrasos, key=atrasos.get, reverse=True)[:limite]

    print(f"   🧪 Gerando 50 Jogos Prontos baseados em tendências...")
    jogos_prontos = []
    
    # 3. A Receita: Cria os 50 Jogos
    tentativas = 0
    while len(jogos_prontos) < 50 and tentativas < 1000:
        tentativas += 1
        novo_jogo = set()
        qtd_sorteio = config_jogo["sorteio"]
        
        # Mistura equilibrada: 30% Quentes, 20% Atrasadas, 50% Restante
        qtd_quentes = max(1, int(qtd_sorteio * 0.3))
        novo_jogo.update(random.sample(bolas_quentes, min(qtd_quentes, len(bolas_quentes))))
        
        disp_atrasadas = [b for b in bolas_atrasadas if b not in novo_jogo]
        qtd_atrasadas = max(1, int(qtd_sorteio * 0.2))
        novo_jogo.update(random.sample(disp_atrasadas, min(qtd_atrasadas, len(disp_atrasadas))))
        
        todas = list(range(inicio_bola, fim_bola + 1))
        disp_todas = [b for b in todas if b not in novo_jogo]
        falta = qtd_sorteio - len(novo_jogo)
        if falta > 0:
            novo_jogo.update(random.sample(disp_todas, falta))
        
        jogo_ordenado = sorted(list(novo_jogo))
        
        if jogo_ordenado not in jogos_prontos:
            jogos_prontos.append(jogo_ordenado)

    # Formata como você pediu: jogo_01, jogo_02...
    payload = {}
    for i, jg in enumerate(jogos_prontos, 1):
        # Formata com zero a esquerda se necessário (ex: 05)
        payload[f"jogo_{i:02d}"] = [f"{b:02d}" if b < 10 else str(b) for b in jg]

    return payload

# =========================================================================
# 4. O EFEITO DOMINÓ (A Atualização em Cadeia)
# =========================================================================
def executar_efeito_domino(api_nome, config_jogo, dados_api):
    nome_jogo = config_jogo["nome"]
    num_concurso = str(dados_api.get('concurso'))
    print(f"\n🔥 [EFEITO DOMINÓ ATIVADO] -> {nome_jogo} (Concurso {num_concurso})")

    # PREPARAÇÃO: Extrai os dados oficiais
    premiacoes = [{"faixa": str(p.get('descricao', '')), "valor": float(p.get('valorPremio', 0))} for p in dados_api.get('premiacoes', [])]
    dezenas = [int(x) for x in dados_api.get('dezenas', [])]
    data_sorteio = str(dados_api.get('data', ''))[:10]
    acumulou = "SIM" if dados_api.get('acumulou') else "NÃO"

    ficha_oficial = {
        "numero": num_concurso,
        "data": data_sorteio,
        "dezenas": dezenas,
        "premiacoes": premiacoes,
        "acumulou": acumulou
    }

    # REGRAS ESPECIAIS COMBINADAS (+Milionária, Timemania, Dia de Sorte)
    if "trevos" in dados_api and dados_api["trevos"]: 
        ficha_oficial["trevos"] = [int(x) for x in dados_api["trevos"]]
    if "time_do_coracao" in dados_api and dados_api["time_do_coracao"]: 
        ficha_oficial["time_do_coracao"] = dados_api["time_do_coracao"]
    if "mes_da_sorte" in dados_api and dados_api["mes_da_sorte"]: 
        ficha_oficial["mes_da_sorte"] = dados_api["mes_da_sorte"]

    # GAVETA 1 e 2: Vitrine de Hoje e Histórico Mestre
    print(f"   📁 Substituindo 'SORTEIO_DE_HOJE' e guardando no 'HISTORICOS_DE_SORTEIOS'...")
    db_put(f"SORTEIO_DE_HOJE/{nome_jogo}", ficha_oficial)
    db_patch(f"HISTORICOS_DE_SORTEIOS/{nome_jogo}", {num_concurso: ficha_oficial})

    # GAVETA 3: Próximo Concurso (A Expectativa Limpa)
    print(f"   🔮 Atualizando 'PROXIMO_CONCURSO' com dados limpos...")
    val_est = dados_api.get('valor_estimado_proximo_concurso', 0)
    data_prox = str(dados_api.get('data_proximo_concurso', 'A definir'))
    
    ficha_proximo = {
        "numero_concurso": str(int(num_concurso) + 1),
        "data_proximo_sorteio": data_prox if data_prox else "A definir",
        "estimativa_premio": moeda_br(val_est)
    }
    db_put(f"PROXIMO_CONCURSO/{nome_jogo}", ficha_proximo)

    # GAVETA 4: A Faxina e a Matemática das Estatísticas
    print(f"   🧹 Faxina: Apagando os 50 jogos velhos da pasta ESTATISTICAS...")
    db_delete(f"ESTATISTICAS/{nome_jogo}/jogos_prontos")
    
    jogos_novos = calcular_estatisticas(nome_jogo, config_jogo)
    if jogos_novos:
        print(f"   ✅ Salvando os 50 novos Jogos Prontos na pasta ESTATISTICAS...")
        db_put(f"ESTATISTICAS/{nome_jogo}/jogos_prontos", jogos_novos)
    
    print(f"🎯 SUCESSO! {nome_jogo} 100% atualizado e mastigado para o Aplicativo!")

# =========================================================================
# 5. O RELÓGIO INTELIGENTE E TOLERÂNCIA A FALHAS
# =========================================================================
def fase_de_reconhecimento():
    """ 16:00 - Verifica a pasta PROXIMO_CONCURSO para saber quem joga hoje """
    global alvos_do_dia
    print("\n🔍 [16:00] FASE DE RECONHECIMENTO: Mapeando os jogos de hoje...")
    alvos_do_dia = []
    
    hoje_str = datetime.now().strftime("%d/%m/%Y")
    proximos = db_get("PROXIMO_CONCURSO") or {}
    
    for api_nome, config in JOGOS.items():
        nome_jogo = config["nome"]
        dados_prox = proximos.get(nome_jogo, {})
        data_marcada = dados_prox.get("data_proximo_sorteio", "")
        
        if data_marcada == hoje_str or "definir" in data_marcada.lower():
            alvos_do_dia.append(api_nome)
            print(f"   🎯 ALVO CONFIRMADO: {nome_jogo}")
            
    if not alvos_do_dia:
        print("   😴 Nenhum alvo para hoje. Modo de espera ativado.")

def fase_da_cacada(hora_fase):
    """ Busca resultados na API e compara com a pasta SORTEIO_DE_HOJE """
    global alvos_do_dia
    if not alvos_do_dia:
        return
        
    print(f"\n🐺 [{hora_fase}] CAÇADA INICIADA! Buscando {len(alvos_do_dia)} jogos pendentes...")
    
    alvos_restantes = []
    
    for api_nome in alvos_do_dia:
        config = JOGOS[api_nome]
        nome_jogo = config["nome"]
        print(f"   -> Checando {nome_jogo}...")
        
        try:
            res = requests.get(f"https://brasilapi.com.br/api/loterias/v1/{api_nome}", timeout=15)
            if res.status_code == 200:
                dados_api = res.json()
                concurso_api = str(dados_api.get('concurso'))
                
                # Tira-teima: Olha para a pasta SORTEIO_DE_HOJE
                vitrine = db_get(f"SORTEIO_DE_HOJE/{nome_jogo}")
                concurso_vitrine = str(vitrine.get("numero", "")) if vitrine else ""
                
                if concurso_api != concurso_vitrine:
                    # Encontrou resultado novo!
                    executar_efeito_domino(api_nome, config, dados_api)
                else:
                    print(f"   ❌ {nome_jogo}: A Caixa ainda não atualizou (Continua no {concurso_api}).")
                    alvos_restantes.append(api_nome)
            else:
                print(f"   ⚠️ {nome_jogo}: API fora do ar. Tentarei depois.")
                alvos_restantes.append(api_nome)
        except Exception as e:
            print(f"   🚨 Erro de internet ao buscar {nome_jogo}.")
            alvos_restantes.append(api_nome)

    alvos_do_dia = alvos_restantes
    
    # REGRA DE PARADA SEGURA (09:00 do dia seguinte)
    if hora_fase == "09:00" and alvos_do_dia:
        print(f"\n🛑 PARADA SEGURA: Atingimos 09:00 e a Caixa não liberou {alvos_do_dia}.")
        print("   Missão abortada. O robô aguardará o novo reconhecimento às 16:00.")
        alvos_do_dia.clear()

# =========================================================================
# 6. INICIALIZAÇÃO E LOOP ETERNO
# =========================================================================
def iniciar_robo():
    print("\n🟢 CÉREBRO CONECTADO! Aguardando os horários programados.")
    print("   Horários de ação: 16:00, 21:30, 22:00, 23:30, 09:00.")
    
    # Faz uma checagem rápida ao ligar para garantir que não perdeu nada
    global alvos_do_dia
    alvos_do_dia = list(JOGOS.keys())
    fase_da_cacada("INICIALIZAÇÃO RÁPIDA")
    
    while True:
        agora = datetime.now()
        hora_atual = agora.strftime("%H:%M")
        
        if hora_atual == "16:00":
            fase_de_reconhecimento()
            time.sleep(65) # Espera virar o minuto
            
        elif hora_atual == "21:30":
            fase_da_cacada("21:30")
            time.sleep(65)
            
        elif hora_atual == "22:00":
            fase_da_cacada("22:00")
            time.sleep(65)
            
        elif hora_atual == "23:30":
            fase_da_cacada("23:30")
            time.sleep(65)
            
        elif hora_atual == "09:00":
            fase_da_cacada("09:00")
            time.sleep(65)
            
        # O robô pisca os olhos a cada 30 segundos
        time.sleep(30)

if __name__ == "__main__":
    iniciar_robo()
