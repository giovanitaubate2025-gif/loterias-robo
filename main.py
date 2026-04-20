import requests
import json
import time
from datetime import datetime
import random
from collections import Counter

print("=============================================================")
print("🤖 ROBÔ LOTERIAS OFICIAL - CÉREBRO MATEMÁTICO ATIVADO 🤖")
print("=============================================================")

# =========================================================================
# CONFIGURAÇÕES DO BANCO DE DADOS
# =========================================================================
URL_FIREBASE = "https://canal-da-loterias-default-rtdb.firebaseio.com/"
SECRET_FIREBASE = "7gS8ASjfG5ZGRVu55Yj5QRw58ZzLCMBzWFLOyrfd"

# Lista oficial de jogos suportados pela Brasil API
JOGOS = {
    "megasena": {"nome": "MEGA-SENA", "total_bolas": 60, "sorteio": 6},
    "lotofacil": {"nome": "LOTOFACIL", "total_bolas": 25, "sorteio": 15},
    "quina": {"nome": "QUINA", "total_bolas": 80, "sorteio": 5},
    "lotomania": {"nome": "LOTOMANIA", "total_bolas": 100, "sorteio": 20},
    "timemania": {"nome": "TIMEMANIA", "total_bolas": 80, "sorteio": 7},
    "diadesorte": {"nome": "DIA-DE-SORTE", "total_bolas": 31, "sorteio": 7},
    "maismilionaria": {"nome": "MAIS-MILIONARIA", "total_bolas": 50, "sorteio": 6}
}

alvos_do_dia = [] # Memória do robô: guarda quem tem sorteio hoje

# =========================================================================
# FUNÇÕES DE COMUNICAÇÃO COM O FIREBASE
# =========================================================================
def db_get(caminho):
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try:
        res = requests.get(url, timeout=15)
        return res.json() if res.status_code == 200 else None
    except: return None

def db_put(caminho, dados):
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try: requests.put(url, json=dados, timeout=15)
    except: pass

def db_patch(caminho, dados):
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try: requests.patch(url, json=dados, timeout=15)
    except: pass

def db_delete(caminho):
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try: requests.delete(url, timeout=15)
    except: pass

def formatar_moeda(valor):
    try: return float(valor) if valor else 0.0
    except: return 0.0

def moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# =========================================================================
# O MOTOR MATEMÁTICO (ESTATÍSTICAS PROFUNDAS)
# =========================================================================
def calcular_estatisticas(nome_jogo, config_jogo):
    print(f"   🧠 {nome_jogo}: Analisando toda a base histórica...")
    historico = db_get(f"HISTORICOS_DE_SORTEIOS/{nome_jogo}")
    
    if not historico:
        print(f"   ⚠️ {nome_jogo}: Sem histórico suficiente para calcular.")
        return []

    todas_as_bolas_sorteadas = []
    atrasos = {i: 0 for i in range(1, config_jogo["total_bolas"] + (0 if nome_jogo == "LOTOMANIA" else 1))}
    
    # Lotomania vai de 0 a 99. Os outros geralmente de 1 a N.
    inicio_bola = 0 if nome_jogo == "LOTOMANIA" else 1
    fim_bola = 99 if nome_jogo == "LOTOMANIA" else config_jogo["total_bolas"]

    concursos_ordenados = sorted([int(k) for k in historico.keys()])
    
    # Varredura para calcular Frequência (Quentes) e Atraso (Delay)
    for num_conc in concursos_ordenados:
        dados = historico[str(num_conc)]
        dezenas = dados.get("dezenas", [])
        
        # Frequência
        todas_as_bolas_sorteadas.extend(dezenas)
        
        # Atraso: soma 1 pra todo mundo, zera quem saiu
        for b in range(inicio_bola, fim_bola + 1):
            if b in dezenas: atrasos[b] = 0
            else: atrasos[b] += 1

    frequencia = Counter(todas_as_bolas_sorteadas)
    
    # Define as Bolas Quentes (Top 20% mais sorteadas)
    bolas_quentes = [b[0] for b in frequencia.most_common(int(fim_bola * 0.2))]
    if not bolas_quentes: bolas_quentes = list(range(inicio_bola, fim_bola + 1))

    # Define as Bolas Atrasadas (Top 20% com maior atraso)
    bolas_atrasadas = sorted(atrasos, key=atrasos.get, reverse=True)[:int(fim_bola * 0.2)]

    print(f"   🧪 Gerando 50 Jogos Prontos combinando matemática e tendências...")
    jogos_prontos = []
    
    # A Receita: Cria 50 jogos misturando quentes, atrasadas e aleatórias
    while len(jogos_prontos) < 50:
        novo_jogo = set()
        qtd_sorteio = config_jogo["sorteio"]
        
        # Pega um pouco das quentes (ex: 30% do bilhete)
        qtd_quentes = max(1, int(qtd_sorteio * 0.3))
        novo_jogo.update(random.sample(bolas_quentes, min(qtd_quentes, len(bolas_quentes))))
        
        # Pega um pouco das atrasadas (ex: 20% do bilhete)
        qtd_atrasadas = max(1, int(qtd_sorteio * 0.2))
        # Remove as que já pegou das quentes para não dar erro
        disp_atrasadas = [b for b in bolas_atrasadas if b not in novo_jogo]
        novo_jogo.update(random.sample(disp_atrasadas, min(qtd_atrasadas, len(disp_atrasadas))))
        
        # Completa com o resto para dar o equilíbrio (Bolas médias)
        todas = list(range(inicio_bola, fim_bola + 1))
        disp_todas = [b for b in todas if b not in novo_jogo]
        falta = qtd_sorteio - len(novo_jogo)
        if falta > 0:
            novo_jogo.update(random.sample(disp_todas, falta))
        
        jogo_ordenado = sorted(list(novo_jogo))
        
        if jogo_ordenado not in jogos_prontos:
            jogos_prontos.append(jogo_ordenado)

    # Formata para enviar pra nuvem
    payload_estatisticas = {}
    for i, jg in enumerate(jogos_prontos, 1):
        payload_estatisticas[f"jogo_{i:02d}"] = jg

    return payload_estatisticas

# =========================================================================
# O EFEITO DOMINÓ (A REAÇÃO EM CADEIA)
# =========================================================================
def executar_efeito_domino(api_nome, config_jogo, dados_api):
    nome_jogo = config_jogo["nome"]
    num_concurso = str(dados_api.get('concurso'))
    print(f"\n🔥 [EFEITO DOMINÓ ATIVADO] -> {nome_jogo} (Concurso {num_concurso})")

    # 1. Estrutura a ficha oficial do sorteio
    premiacoes = [{"faixa": str(p.get('descricao', '')), "valor": formatar_moeda(p.get('valorPremio', 0))} for p in dados_api.get('premiacoes', [])]
    
    ficha_oficial = {
        "numero": num_concurso,
        "data": str(dados_api.get('data', ''))[:10],
        "dezenas": [int(x) for x in dados_api.get('dezenas', [])],
        "premiacoes": premiacoes,
        "acumulou": "SIM" if dados_api.get('acumulou') else "NÃO"
    }

    # REGRAS ESPECIAIS (Trevos, Time, Mês)
    if "trevos" in dados_api and dados_api["trevos"]: 
        ficha_oficial["trevos"] = [int(x) for x in dados_api["trevos"]]
    if "time_do_coracao" in dados_api and dados_api["time_do_coracao"]: 
        ficha_oficial["time_do_coracao"] = dados_api["time_do_coracao"]
    if "mes_da_sorte" in dados_api and dados_api["mes_da_sorte"]: 
        ficha_oficial["mes_da_sorte"] = dados_api["mes_da_sorte"]

    # 2. ATUALIZA A VITRINE (Hoje e Histórico)
    print(f"   📁 Salvando na Gaveta 'SORTEIO_DE_HOJE' e 'HISTORICOS_DE_SORTEIOS'...")
    db_put(f"SORTEIO_DE_HOJE/{nome_jogo}", ficha_oficial)
    db_patch(f"HISTORICOS_DE_SORTEIOS/{nome_jogo}", {num_concurso: ficha_oficial})

    # 3. ATUALIZA A EXPECTATIVA (Próximo)
    print(f"   🔮 Atualizando a Gaveta 'PROXIMO_CONCURSO' (Expectativa Limpa)...")
    val_est = formatar_moeda(dados_api.get('valor_estimado_proximo_concurso', 0))
    ficha_proximo = {
        "numero_concurso": str(int(num_concurso) + 1),
        "data_proximo_sorteio": str(dados_api.get('data_proximo_concurso', 'A definir')),
        "estimativa_premio": moeda_br(val_est)
    }
    db_put(f"PROXIMO_CONCURSO/{nome_jogo}", ficha_proximo)

    # 4. A FAXINA E O CÉREBRO (Estatísticas)
    print(f"   🧹 Apagando palpites velhos...")
    db_delete(f"ESTATISTICAS/{nome_jogo}/jogos_prontos")
    
    # 5. RODA O MOTOR
    jogos_novos = calcular_estatisticas(nome_jogo, config_jogo)
    if jogos_novos:
        print(f"   ✅ Salvando 50 Jogos Prontos na Gaveta 'ESTATISTICAS'...")
        db_put(f"ESTATISTICAS/{nome_jogo}/jogos_prontos", jogos_novos)
    
    print(f"🎯 DOMINÓ FINALIZADO COM SUCESSO PARA {nome_jogo}!")

# =========================================================================
# AS FASES DO RELÓGIO
# =========================================================================
def fase_de_reconhecimento():
    """ 16:00 - O robô descobre quem joga hoje olhando a pasta PROXIMO_CONCURSO """
    global alvos_do_dia
    print("\n🔍 [16:00] FASE DE RECONHECIMENTO INICIADA...")
    alvos_do_dia = []
    
    hoje_str = datetime.now().strftime("%d/%m/%Y")
    
    # Pega todos os próximos concursos de uma vez
    proximos = db_get("PROXIMO_CONCURSO") or {}
    
    for api_nome, config in JOGOS.items():
        nome_jogo = config["nome"]
        dados_prox = proximos.get(nome_jogo, {})
        data_marcada = dados_prox.get("data_proximo_sorteio", "")
        
        # Se a data marcada for hoje (ou estiver atrasada no sistema), entra nos alvos
        if data_marcada == hoje_str or "definir" in data_marcada.lower():
            alvos_do_dia.append(api_nome)
            print(f"   🎯 ALVO CONFIRMADO: {nome_jogo} tem sorteio previsto.")
            
    if not alvos_do_dia:
        print("   😴 Nenhum sorteio previsto para hoje. O robô vai descansar.")
    else:
        print(f"   📋 Total de alvos para a noite: {len(alvos_do_dia)}")

def fase_da_cacada(nome_da_fase):
    """ 21:30, 22:00, 23:30, 09:00 - A busca pelos resultados """
    global alvos_do_dia
    if not alvos_do_dia:
        return # Nada para fazer
        
    print(f"\n🐺 [{nome_da_fase}] INICIANDO A CAÇADA AOS RESULTADOS...")
    
    alvos_restantes = []
    
    for api_nome in alvos_do_dia:
        config = JOGOS[api_nome]
        nome_jogo = config["nome"]
        print(f"   -> Verificando {nome_jogo} na API...")
        
        try:
            # Consulta a API Oficial
            res = requests.get(f"https://brasilapi.com.br/api/loterias/v1/{api_nome}", timeout=10)
            if res.status_code == 200:
                dados_api = res.json()
                concurso_api = str(dados_api.get('concurso'))
                
                # Consulta a vitrine (O Tira-Teima)
                vitrine_hoje = db_get(f"SORTEIO_DE_HOJE/{nome_jogo}")
                concurso_vitrine = vitrine_hoje.get("numero", "") if vitrine_hoje else ""
                
                if concurso_api != concurso_vitrine:
                    # ACHOU! Dispara o Efeito Dominó
                    executar_efeito_domino(api_nome, config, dados_api)
                else:
                    print(f"   ❌ {nome_jogo}: A Caixa ainda não liberou o resultado novo (Atual: {concurso_api}).")
                    alvos_restantes.append(api_nome) # Continua na lista para a próxima busca
            else:
                print(f"   ⚠️ {nome_jogo}: Erro na Brasil API. Tentarei depois.")
                alvos_restantes.append(api_nome)
        except Exception as e:
            print(f"   🚨 Erro de conexão ao buscar {nome_jogo}: {e}")
            alvos_restantes.append(api_nome)

    # Atualiza a memória. Se esvaziou, o robô dorme feliz.
    alvos_do_dia = alvos_restantes
    
    if "09:00" in nome_da_fase and alvos_do_dia:
        print("\n🛑 PARADA SEGURA: Atingiu 09:00h do dia seguinte e a Caixa não liberou os jogos:")
        print(f"   Abandonando missão para: {alvos_do_dia}")
        alvos_do_dia = [] # Limpa a lista na marra

# =========================================================================
# O CORAÇÃO DO ROBÔ (LOOP INFINITO COM CALENDÁRIO)
# =========================================================================
def iniciar_robo_eterno():
    print("🟢 Sistema Online. O Robô Analista assumiu o controle.")
    print("   Ele operará em silêncio e agirá nos horários combinados.")
    
    # Faz uma caçada imediata ao ligar, só por segurança
    global alvos_do_dia
    alvos_do_dia = list(JOGOS.keys()) # Força verificar tudo na primeira ligada
    fase_da_cacada("INICIALIZAÇÃO")
    
    while True:
        agora = datetime.now()
        hora_atual = agora.strftime("%H:%M")
        
        if hora_atual == "16:00":
            fase_de_reconhecimento()
            time.sleep(60) # Espera 1 min pra não rodar duas vezes no mesmo minuto
            
        elif hora_atual == "21:30":
            fase_da_cacada("1º BUSCA - 21:30")
            time.sleep(60)
            
        elif hora_atual == "22:00":
            fase_da_cacada("2º BUSCA - 22:00")
            time.sleep(60)
            
        elif hora_atual == "23:30":
            fase_da_cacada("3º BUSCA - 23:30")
            time.sleep(60)
            
        elif hora_atual == "09:00":
            fase_da_cacada("REPESCAGEM E ABORTO - 09:00")
            time.sleep(60)
            
        # O robô pisca o olho a cada 30 segundos verificando a hora
        time.sleep(30)

if __name__ == "__main__":
    iniciar_robo_eterno()
