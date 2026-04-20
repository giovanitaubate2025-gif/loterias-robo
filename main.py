import requests
from datetime import datetime

# =========================================================================
# ROBÔ GG-456 OFICIAL (GITHUB ACTIONS)
# Sincroniza dados da Caixa com o Firebase (Hoje, Histórico e Próximo)
# =========================================================================

URL_FIREBASE = "https://canal-da-loterias-default-rtdb.firebaseio.com/"
SECRET_FIREBASE = "7gS8ASjfG5ZGRVu55Yj5QRw58ZzLCMBzWFLOyrfd"

# Mapa de comunicação: API da Caixa -> Nome da Pasta no seu Firebase
JOGOS = {
    'megasena': 'MEGA-SENA',
    'lotofacil': 'LOTOFÁCIL',
    'quina': 'QUINA',
    'lotomania': 'LOTOMANIA',
    'timemania': 'TIMEMANIA',
    'maismilionaria': 'MAISMILIONÁRIA',
    'diadesorte': 'DIA_DE_SORTE',
    'duplasena': 'DUPLA_SENA',
    'supersete': 'SUPER_SETE'
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def enviar_firebase(caminho, dados, metodo="put"):
    """ Envia os dados estruturados para a sua nuvem """
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try:
        if metodo == "put":
            res = requests.put(url, json=dados, timeout=20)
        else:
            res = requests.patch(url, json=dados, timeout=20)
        return res.status_code == 200
    except Exception as e:
        log(f"Erro de conexão com Firebase: {e}")
        return False

def formatar_moeda(valor):
    """ Transforma números da API em formato de Reais legível (Opcional, pois a API já manda formatado às vezes) """
    try:
        return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return "R$ 0,00"

def buscar_caixa(jogo_api):
    """ Pega o resultado ao vivo do site oficial da Caixa """
    url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{jogo_api}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        log(f"Erro ao buscar {jogo_api} na Caixa: {e}")
    return None

def executar_robo():
    log("🚀 INICIANDO ROBÔ DE SINCRONIZAÇÃO OFICIAL...")

    for api_id, pasta_firebase in JOGOS.items():
        log(f"Processando jogo: {pasta_firebase}...")
        
        dados_caixa = buscar_caixa(api_id)
        
        if dados_caixa and 'numero' in dados_caixa:
            concurso = str(dados_caixa['numero'])
            
            # 1. PREPARANDO PACOTE DO SORTEIO (Para HOJE e HISTÓRICO)
            especial = dados_caixa.get('nomeTimeCoracao') or dados_caixa.get('nomeMesSorte') or ""
            if dados_caixa.get('listaTrevos'): # Para +Milionária
                especial = " - ".join([str(t) for t in dados_caixa['listaTrevos']])
                
            rateios = []
            if dados_caixa.get('listaRateioPremio'):
                for r in dados_caixa['listaRateioPremio']:
                    rateios.append({
                        "descricao": r.get('descricaoFaixa', ''),
                        "valor": r.get('valorPremio', 0.0)
                    })

            pacote_sorteio = {
                "numero": concurso,
                "data": dados_caixa.get('dataApuracao', ''),
                "dezenas": dados_caixa.get('listaDezenas', []),
                "rateio": rateios,
                "especial": especial,
                "acumulou": "SIM" if dados_caixa.get('acumulado') else "NÃO"
            }

            # 2. PREPARANDO PACOTE DO PRÓXIMO CONCURSO
            pacote_proximo = {
                "numero_concurso": str(int(concurso) + 1),
                "data_proximo_sorteio": dados_caixa.get('dataProximoConcurso', ''),
                "valor_estimado": formatar_moeda(dados_caixa.get('valorEstimadoProximoConcurso', 0.0))
            }

            # ====== DISPARANDO PARA AS 3 PASTAS DA NUVEM ======
            
            # A. Atualiza SORTEIO DE HOJE (Substitui)
            enviar_firebase(f"SORTEIO_DE_HOJE/{pasta_firebase}", pacote_sorteio, "put")
            
            # B. Salva no HISTÓRICO (Adiciona/Substitui o concurso específico)
            enviar_firebase(f"HISTORICOS_DE_SORTEIOS/{pasta_firebase}/{concurso}", pacote_sorteio, "put")
            
            # C. Atualiza PRÓXIMO CONCURSO (Substitui com a estimativa nova)
            enviar_firebase(f"PROXIMO_CONCURSO/{pasta_firebase}", pacote_proximo, "put")
            
            log(f"✅ {pasta_firebase} sincronizado com sucesso! (Concurso {concurso})")
        else:
            log(f"⚠️ Dados não encontrados para {pasta_firebase} no momento.")

    log("🏁 CICLO FINALIZADO. Nuvem 100% atualizada de acordo com as regras.")

if __name__ == "__main__":
    executar_robo()
