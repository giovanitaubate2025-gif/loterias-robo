import os
import json
import time
import random
import requests
import urllib3
import gspread
import firebase_admin
from datetime import datetime
from firebase_admin import credentials, db, initialize_app
from gspread_formatting import *

# Desativa avisos de segurança ao acessar a Caixa
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================================================================
# 1. CONFIGURAÇÕES E REGRAS MATEMÁTICAS DAS 9 LOTERIAS PRINCIPAIS
# ==============================================================================
LOTERIAS = {
    'megasena': {'nome_pasta': 'Mega-Sena', 'bolas': 6, 'globo': 60},
    'lotofacil': {'nome_pasta': 'Lotofacil', 'bolas': 15, 'globo': 25},
    'quina': {'nome_pasta': 'Quina', 'bolas': 5, 'globo': 80},
    'lotomania': {'nome_pasta': 'Lotomania', 'bolas': 20, 'globo': 100, 'is_lotomania': True},
    'timemania': {'nome_pasta': 'Timemania', 'bolas': 10, 'globo': 80, 'especial': 'Time do Coracao'},
    'duplasena': {'nome_pasta': 'Dupla-Sena', 'bolas': 6, 'globo': 50},
    'maismilionaria': {'nome_pasta': '+Milionaria', 'bolas': 6, 'globo': 50, 'tem_trevos': True},
    'diadesorte': {'nome_pasta': 'Dia-de-Sorte', 'bolas': 7, 'globo': 31, 'especial': 'Mes de Sorte'},
    'supersete': {'nome_pasta': 'Super-Sete', 'bolas': 7, 'globo': 9, 'is_supersete': True}
}

# ==============================================================================
# 2. CONEXÃO SEGURA COM NUVEM E PLANILHA
# ==============================================================================
def conectar_servicos():
    print("🔐 Autenticando com Firebase e Google Sheets...")
    
    # Firebase
    if not firebase_admin._apps:
        # Pega a chave do segredo FIREBASE_SERVICE_ACCOUNT do GitHub
        cred_json = json.loads(os.environ['FIREBASE_SERVICE_ACCOUNT'])
        cred = credentials.Certificate(cred_json)
        initialize_app(cred, {'databaseURL': "https://canal-da-loterias-default-rtdb.firebaseio.com"})
    
    # Google Sheets
    # Pega a chave do segredo GOOGLE_SHEETS_CREDENTIALS do GitHub
    gc = gspread.service_account_from_dict(json.loads(os.environ['GOOGLE_SHEETS_CREDENTIALS']))
    return gc

# ==============================================================================
# 3. MÓDULO DE AUTO-CRIAÇÃO E PODA DA PLANILHA (O JARDINEIRO)
# ==============================================================================
def formatar_moeda(valor):
    if not valor:
        return "R$ 0,00"
    try:
        return "R$ {:,.2f}".format(float(valor)).replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return "R$ 0,00"

def setup_e_poda_planilha(gc, config, dados_novos):
    # ATENÇÃO: O nome abaixo deve ser IGUAL ao nome da sua planilha no Google Drive
    sh = gc.open("JOGOS BOLÕES ATIVO ✔️")
    nome_aba = config['nome_pasta'].upper()
    
    try:
        worksheet = sh.worksheet(nome_aba)
    except gspread.exceptions.WorksheetNotFound:
        print(f"🏗️ Criando aba {nome_aba} automaticamente (Zero Setup)...")
        worksheet = sh.add_worksheet(title=nome_aba, rows="100", cols="20")
        
        # Cria o Cabeçalho
        cabecalho = ["CONCURSO", "DATA"] + [f"BOLA {i+1}" for i in range(config['bolas'])]
        if config.get('tem_trevos'):
            cabecalho.extend(["TREVO 1", "TREVO 2"])
        elif config.get('especial'):
            cabecalho.append(config['especial'].upper())
        
        worksheet.insert_row(cabecalho, 1)
        
        # Estilização do cabeçalho
        set_frozen(worksheet, rows=1)
        format_cell_range(worksheet, '1:1', cellFormat(
            backgroundColor=color(0.15, 0.13, 0.38),
            textFormat=textFormat(foregroundColor=color(1, 1, 1), bold=True),
            horizontalAlignment='CENTER'
        ))

    # Verifica se o concurso já existe para não duplicar
    concursos_salvos = worksheet.col_values(1)
    if str(dados_novos['numero']) in concursos_salvos:
        print(f"✅ Concurso {dados_novos['numero']} já está na planilha.")
        return worksheet, False

    # Prepara a nova linha
    dezenas = [str(d).zfill(2) for d in dados_novos.get('listaDezenas', [])]
    nova_linha = [str(dados_novos['numero']), dados_novos['dataApuracao']] + dezenas
    
    if config.get('tem_trevos'):
        trevos = [str(t).zfill(2) for t in (dados_novos.get('listaDezenasSegundoSorteio') or dados_novos.get('trevosSorteados') or [])]
        nova_linha.extend(trevos[:2] if trevos else ["", ""])
    elif config.get('especial'):
        nova_linha.append(dados_novos.get('nomeTimeCoracaoMesSorte') or "")
    
    # Insere na segunda linha (abaixo do cabeçalho)
    worksheet.insert_row(nova_linha, 2)
    
    # Estética e Poda
    num_linhas = len(worksheet.col_values(1))
    pintar_verde = cellFormat(backgroundColor=color(0.85, 0.91, 0.82), textFormat=textFormat(bold=True))
    format_cell_range(worksheet, 'A2:Z2', pintar_verde)
    
    set_column_width(worksheet, 'A:Z', 110)
    return worksheet, True

# ==============================================================================
# 4. MOTOR ESTATÍSTICO
# ==============================================================================
def calcular_estatisticas(worksheet, config):
    todas_linhas = worksheet.get_all_values()[1:]
    historico = [linha[2:2+config['bolas']] for linha in todas_linhas if len(linha) > 2]
    
    frequencia = {}
    for jogo in historico:
        for bola in jogo:
            if bola.strip():
                frequencia[bola] = frequencia.get(bola, 0) + 1
    
    quentes = [k for k, v in sorted(frequencia.items(), key=lambda item: item[1], reverse=True)]
    
    if config.get('is_supersete'):
        universo = [str(i) for i in range(10)]
    elif config.get('is_lotomania'):
        universo = [str(i).zfill(2) if i < 100 else '00' for i in range(100)]
    else:
        universo = [str(i).zfill(2) for i in range(1, config['globo'] + 1)]

    lotes_prontos = []
    for _ in range(50):
        jogo = set()
        while len(jogo) < config['bolas']:
            pool = quentes[:20] if (random.random() < 0.7 and len(quentes) >= 20) else universo
            bola = random.choice(pool)
            if config.get('is_supersete'):
                lotes_prontos.append([random.choice(universo) for _ in range(7)])
                break
            jogo.add(bola)
        if not config.get('is_supersete'):
            lotes_prontos.append(sorted(list(jogo)))
            
    return lotes_prontos

# ==============================================================================
# 5. GERENCIADOR DE NUVEM (FIREBASE)
# ==============================================================================
def atualizar_nuvem(config, dados, lotes_prontos):
    ref_jogo = db.reference(config['nome_pasta'])
    
    # Sorteio de Hoje
    ref_jogo.child('SORTEIO_DE_HOJE').set({
        'concurso': str(dados['numero']),
        'data': dados['dataApuracao'],
        'dezenas': [str(d).zfill(2) for d in dados.get('listaDezenas', [])],
        'arrecadacao_total': formatar_moeda(dados.get('valorArrecadacao', 0))
    })
    
    # Próximo Prêmio
    valor_estimado = dados.get('valorEstimadoProximoConcurso', 0)
    data_prox = dados.get('dataProximoConcurso', 'Aguardando')
    ref_jogo.child('PROXIMO_PREMIO').set({
        'texto_informativo': f"Estimativa de prêmio do próximo concurso {data_prox}",
        'valor_estimado': formatar_moeda(valor_estimado)
    })
    
    # Estatísticas
    ref_jogo.child('ESTATISTICAS').set({
        'jogos_50': lotes_prontos,
        'selo_garantia': {
            'data_geracao': datetime.now().strftime("%d/%m/%Y"),
            'hora_geracao': datetime.now().strftime("%H:%M:%S"),
            'concurso_base': str(dados['numero'])
        }
    })
    print(f"☁️ Nuvem do jogo {config['nome_pasta']} atualizada!")

# ==============================================================================
# 6. FLUXO PRINCIPAL
# ==============================================================================
def processar_loterias():
    print("🚀 Iniciando Trator de Elite...")
    try:
        gc = conectar_servicos()
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return

    headers = {'User-Agent': 'Mozilla/5.0'}
    loterias_processadas = 0
    
    for api_id, config in LOTERIAS.items():
        print(f"\n🔎 Buscando: {config['nome_pasta']}")
        try:
            url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{api_id}"
            res = requests.get(url, headers=headers, verify=False, timeout=20)
            
            if res.status_code == 200:
                dados_caixa = res.json()
                worksheet, teve_novo = setup_e_poda_planilha(gc, config, dados_caixa)
                
                if teve_novo:
                    lotes = calcular_estatisticas(worksheet, config)
                    atualizar_nuvem(config, dados_caixa, lotes)
                    loterias_processadas += 1
            else:
                print(f"⚠️ Caixa não respondeu (Status {res.status_code})")
        except Exception as e:
            print(f"❌ Erro em {config['nome_pasta']}: {e}")
            
    print(f"\n🏁 Finalizado! Novos processados: {loterias_processadas}")

if __name__ == "__main__":
    processar_loterias()
