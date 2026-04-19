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

# Desativa avisos de segurança da API da Caixa
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================================================================
# 1. ARQUITETURA OFICIAL DAS MODALIDADES
# ==============================================================================
LOTERIAS = {
    'megasena': {'api': 'megasena', 'nome': 'Mega-Sena', 'bolas': 6, 'globo': 60, 'cor': '#209869'},
    'lotofacil': {'api': 'lotofacil', 'nome': 'Lotofacil', 'bolas': 15, 'globo': 25, 'cor': '#930089'},
    'quina': {'api': 'quina', 'nome': 'Quina', 'bolas': 5, 'globo': 80, 'cor': '#260085'},
    'lotomania': {'api': 'lotomania', 'nome': 'Lotomania', 'bolas': 20, 'globo': 100, 'cor': '#F78100', 'is_lotomania': True},
    'duplasena': {'api': 'duplasena', 'nome': 'Dupla-Sena', 'bolas': 6, 'globo': 50, 'cor': '#A61324'},
    'diadesorte': {'api': 'diadesorte', 'nome': 'Dia-de-Sorte', 'bolas': 7, 'globo': 31, 'cor': '#CB852A', 'especial': 'Mês de Sorte'},
    'timemania': {'api': 'timemania', 'nome': 'Timemania', 'bolas': 10, 'globo': 80, 'cor': '#049645', 'especial': 'Time do Coração'},
    'supersete': {'api': 'supersete', 'nome': 'Super-Sete', 'bolas': 7, 'globo': 9, 'cor': '#A9CC41', 'is_supersete': True},
    'maismilionaria': {'api': 'maismilionaria', 'nome': '+Milionaria', 'bolas': 6, 'globo': 50, 'cor': '#1E2C5A', 'tem_trevos': True},
    'loteca': {'api': 'loteca', 'nome': 'Loteca', 'bolas': 14, 'globo': 0, 'cor': '#E83E43', 'is_esportiva': True},
    'lotogol': {'api': 'lotogol', 'nome': 'Lotogol', 'bolas': 5, 'globo': 0, 'cor': '#E16C22', 'is_esportiva': True}
}

NOME_PLANILHA_MESTRE = "JOGOS BOLÕES ATIVO ✔️"

# ==============================================================================
# 2. CONEXÃO SEGURA COM NUVEM E PLANILHA
# ==============================================================================
def conectar_servicos():
    print("🔐 Autenticando Trator GG-456...")
    if not firebase_admin._apps:
        cred_json = json.loads(os.environ['FIREBASE_SERVICE_ACCOUNT'])
        cred = credentials.Certificate(cred_json)
        initialize_app(cred, {'databaseURL': "https://canal-da-loterias-default-rtdb.firebaseio.com"})
    
    gc = gspread.service_account_from_dict(json.loads(os.environ['GOOGLE_SHEETS_CREDENTIALS']))
    return gc, db

# ==============================================================================
# 3. A CAÇADORA (LIMPEZA FINANCEIRA E BUSCA API)
# ==============================================================================
def limpar_moeda(valor):
    if not valor: return 0.0
    try:
        if isinstance(valor, (int, float)): return float(valor)
        limpo = str(valor).replace('R$', '').replace('.', '').replace(',', '.').strip()
        return float(limpo)
    except: return 0.0

def formatar_moeda_visual(valor):
    return "R$ {:,.2f}".format(float(valor)).replace(',', 'X').replace('.', ',').replace('X', '.')

def buscar_caixa(api_path, concurso=None):
    sufixo = f"/{concurso}" if concurso else ""
    url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/{api_path}{sufixo}"
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, verify=False, timeout=15)
        if res.status_code == 200:
            dados = res.json()
            if 'numero' in dados:
                dados['valorEstimadoProximoConcurso_Limpo'] = limpar_moeda(dados.get('valorEstimadoProximoConcurso', 0))
                return dados
    except Exception as e:
        pass
    return None

# ==============================================================================
# 4. O CÉREBRO DA PLANILHA (PODA, DOMINÓ VERDE E ESTÉTICA)
# ==============================================================================
def setup_aba_se_nao_existe(sh, config):
    try:
        return sh.worksheet(config['nome'].upper())
    except gspread.exceptions.WorksheetNotFound:
        print(f"🏗️ Zero Setup: Construindo aba {config['nome'].upper()}...")
        ws = sh.add_worksheet(title=config['nome'].upper(), rows="50", cols="25")
        
        cabecalho = ["CONCURSO", "DATA"] + [f"BOLA {i+1}" for i in range(config['bolas'])]
        if config.get('tem_trevos'): cabecalho.extend(["TREVO 1", "TREVO 2"])
        elif config.get('especial'): cabecalho.append(config.get('especial').upper())
        cabecalho.extend(["ARRECADAÇÃO", "PRÊMIO ESTIMADO"])
        
        ws.insert_row(cabecalho, 1)
        set_frozen(ws, rows=1)
        
        format_cell_range(ws, '1:1', cellFormat(
            backgroundColor=color(0.15, 0.13, 0.38),
            textFormat=textFormat(foregroundColor=color(1, 1, 1), bold=True, fontSize=11),
            horizontalAlignment='CENTER', verticalAlignment='MIDDLE'
        ))
        return ws

def aplicar_poda_radical(ws):
    try:
        todas_linhas = ws.get_all_values()
        if not todas_linhas: return
        
        max_linhas_reais = len(todas_linhas)
        max_cols_reais = len(todas_linhas[0]) if max_linhas_reais > 0 else 20
        
        # Poda Radical
        ws.resize(rows=max_linhas_reais + 2, cols=max_cols_reais)
        
        # Alargamento
        set_column_width(ws, 'A:Z', 120)
        
        # Centralização Total e Bordas
        formato_base = cellFormat(
            horizontalAlignment='CENTER', verticalAlignment='MIDDLE',
            borders=borders(top=border('SOLID'), bottom=border('SOLID'), left=border('SOLID'), right=border('SOLID'))
        )
        format_cell_range(ws, f'A2:Z{max_linhas_reais}', formato_base)
    except Exception as e:
        print(f"⚠️ Aviso ao aplicar poda: {e}")

def montar_linha_planilha(config, dados):
    dezenas = dados.get('listaDezenas', [])
    if config.get('is_esportiva'): dezenas = dados.get('listaDezenas', []) or ["-"] * config['bolas']
    
    dezenas_fmt = [str(d).zfill(2) for d in dezenas]
    linha = [str(dados['numero']), dados.get('dataApuracao', '')] + dezenas_fmt
    
    if config.get('tem_trevos'):
        trevos = [str(t).zfill(2) for t in (dados.get('listaDezenasSegundoSorteio') or [])]
        linha.extend(trevos[:2] if trevos else ["", ""])
    elif config.get('especial'):
        linha.append(dados.get('nomeTimeCoracaoMesSorte') or "")
        
    linha.extend([
        formatar_moeda_visual(dados.get('valorArrecadacao', 0)),
        formatar_moeda_visual(dados.get('valorEstimadoProximoConcurso_Limpo', 0))
    ])
    return linha

def inserir_historico_topo(ws, linha):
    try:
        # Despinta a antiga Linha 2
        despintar = cellFormat(backgroundColor=color(1, 1, 1), textFormat=textFormat(bold=False))
        format_cell_range(ws, 'A2:Z2', despintar)
        
        ws.insert_row(linha, 2)
        
        # Pinta a nova Linha 2 de Verde
        pintar_verde = cellFormat(backgroundColor=color(0.85, 0.91, 0.82), textFormat=textFormat(bold=True, foregroundColor=color(0.11, 0.51, 0.28)))
        format_cell_range(ws, 'A2:Z2', pintar_verde)
    except Exception as e:
        print(f"Erro ao inserir no topo: {e}")

# ==============================================================================
# 5. GERENCIAMENTO DE ABAS GLOBAIS (VITRINE E COFRE)
# ==============================================================================
def salvar_vitrine_app(sh, config, dados):
    try:
        ws = sh.worksheet("VITRINE_APP")
    except:
        ws = sh.add_worksheet("VITRINE_APP", rows="20", cols="5")
        ws.insert_row(["JOGO", "PRÓXIMO PRÊMIO", "DATA PRÓXIMO", "HORA ATUALIZAÇÃO", "STATUS"], 1)
        set_frozen(ws, rows=1)
        format_cell_range(ws, 'A1:E1', cellFormat(backgroundColor=color(0.1, 0.1, 0.1), textFormat=textFormat(foregroundColor=color(1,1,1), bold=True)))
    
    status = "AGUARDANDO SORTEIO" if dados.get('acumulado') else "SORTEIO REALIZADO"
    linha_info = [
        config['nome'].upper(),
        formatar_moeda_visual(dados.get('valorEstimadoProximoConcurso_Limpo', 0)),
        dados.get('dataProximoConcurso', 'Aguardando'),
        datetime.now().strftime("%H:%M:%S"),
        status
    ]
    
    try:
        col_jogos = ws.col_values(1)
        if config['nome'].upper() in col_jogos:
            idx = col_jogos.index(config['nome'].upper()) + 1
            ws.update(f'A{idx}:E{idx}', [linha_info])
        else:
            ws.append_row(linha_info)
    except Exception as e:
        print(f"Aviso Vitrine: {e}")

def salvar_cofre_premiacoes(sh, config, dados):
    try:
        ws = sh.worksheet("PREMIAÇÕES GLOBAIS")
    except:
        ws = sh.add_worksheet("PREMIAÇÕES GLOBAIS", rows="100", cols="8")
        ws.insert_row(["JOGO", "CONCURSO", "DATA", "FAIXA", "GANHADORES", "VALOR PAGO", "ACUMULOU?", "PROX. ESTIMATIVA"], 1)
        set_frozen(ws, rows=1)
        format_cell_range(ws, '1:1', cellFormat(backgroundColor=color(0.1, 0.1, 0.1), textFormat=textFormat(foregroundColor=color(1,1,1), bold=True)))
    
    try:
        # Remove as antigas do mesmo jogo
        linhas = ws.get_all_values()
        for i in range(len(linhas), 1, -1):
            if linhas[i-1][0] == config['nome'].upper():
                ws.delete_rows(i)
                
        # Insere as novas
        acumulou_geral = "SIM" if dados.get('acumulado') else "NÃO"
        estimativa = formatar_moeda_visual(dados.get('valorEstimadoProximoConcurso_Limpo', 0))
        
        for faixa in reversed(dados.get('listaRateioPremio', [])):
            desc = faixa.get('descricaoFaixa', '')
            ganhadores = faixa.get('numeroDeGanhadores', 0)
            valor = formatar_moeda_visual(faixa.get('valorPremio', 0))
            
            # A Regra do Acumulou
            if ganhadores == 0: valor = "ACUMULOU"
                
            ws.insert_row([config['nome'].upper(), str(dados['numero']), dados.get('dataApuracao', ''), desc, ganhadores, valor, acumulou_geral, estimativa], 2)
    except Exception as e:
        print(f"Aviso Cofre: {e}")

# ==============================================================================
# 6. MOTOR ESTATÍSTICO (GERAÇÃO DOS 50 JOGOS)
# ==============================================================================
def processar_estatisticas(ws, config, concurso_base):
    if config.get('is_esportiva'): return []
    
    try:
        todas_linhas = ws.get_all_values()[1:]
        historico = [linha[2:2+config['bolas']] for linha in todas_linhas if len(linha) > 2]
        
        frequencia = {}
        for jogo in historico:
            for bola in jogo:
                bola = bola.strip()
                if bola: frequencia[bola] = frequencia.get(bola, 0) + 1
                
        quentes = [k for k, v in sorted(frequencia.items(), key=lambda item: item[1], reverse=True)]
        
        universo = []
        if config.get('is_supersete'): universo = [str(i) for i in range(10)]
        elif config.get('is_lotomania'): universo = [str(i).zfill(2) if i < 100 else '00' for i in range(100)]
        else: universo = [str(i).zfill(2) for i in range(1, config['globo'] + 1)]
        
        lotes_prontos = []
        for _ in range(50):
            jogo = set()
            while len(jogo) < config['bolas']:
                pool = quentes[:int(config['globo']*0.3)] if (random.random() < 0.7 and len(quentes) > 5) else universo
                if not pool: pool = universo
                bola = random.choice(pool)
                
                if config.get('is_supersete'):
                    lotes_prontos.append([random.choice(universo) for _ in range(7)])
                    break
                jogo.add(bola)
                
            if not config.get('is_supersete'):
                lotes_prontos.append(sorted(list(jogo)))
                
        return lotes_prontos
    except: return []

# ==============================================================================
# 7. ARQUITETURA DE NUVEM EM 5 PASTAS (FIREBASE)
# ==============================================================================
def atualizar_nuvem_firebase(config, dados, lotes, historico_completo=False):
    ref_jogo = db.reference(config['api'])
    concurso = str(dados['numero'])
    
    # 1. HISTÓRICO DE SORTEIOS
    pacote_historico = {
        'concurso': concurso, 'data_sorteio': dados.get('dataApuracao', ''),
        'dezenas': dados.get('listaDezenas', []), 'acumulado': dados.get('acumulado', False),
        'rateio': { f"pago_{f.get('faixa')}": f.get('valorPremio', 0) for f in dados.get('listaRateioPremio', []) }
    }
    ref_jogo.child(f'HISTORICO_DE_SORTEIOS/{concurso}').set(pacote_historico)
    
    if historico_completo: return 
    
    # 2. SORTEIO DE HOJE
    ref_jogo.child('SORTEIO_DE_HOJE').set({
        'concurso': concurso, 'data': dados.get('dataApuracao', ''),
        'dezenas': dados.get('listaDezenas', []), 'arrecadacao_total': formatar_moeda_visual(dados.get('valorArrecadacao', 0))
    })
    
    # 3. PRÓXIMO PRÊMIO
    ref_jogo.child('PROXIMO_PREMIO').set({
        'data_proximo': dados.get('dataProximoConcurso', 'Aguardando'),
        'proximo_premio': dados.get('valorEstimadoProximoConcurso_Limpo', 0),
        'status': "ACUMULOU" if dados.get('acumulado') else "SORTEIO REALIZADO"
    })
    
    # 4. TABELA DE PREMIAÇÕES
    tabela = {}
    for f in dados.get('listaRateioPremio', []):
        nome = f.get('descricaoFaixa', f"Faixa {f.get('faixa')}")
        if f.get('numeroDeGanhadores', 0) == 0:
            tabela[nome] = f"ACUMULOU - Estimativa {formatar_moeda_visual(dados.get('valorEstimadoProximoConcurso_Limpo', 0))}"
        else:
            tabela[nome] = formatar_moeda_visual(f.get('valorPremio', 0))
    ref_jogo.child('TABELA_DE_PREMIACOES').set(tabela)
    
    # 5. ESTATÍSTICAS
    if lotes:
        ref_jogo.child('ESTATISTICAS').set({
            'jogos_50': lotes,
            'selo_garantia': { 'data_geracao': datetime.now().strftime("%d/%m/%Y"), 'hora_geracao': datetime.now().strftime("%H:%M:%S"), 'concurso_base': concurso }
        })

# ==============================================================================
# 8. O TRATOR EXECUTIVO (ORQUESTRADOR GERAL)
# ==============================================================================
def executar_trator():
    print("🚀 Ligando Motores do Trator GG-456 (Versão Anti-Limite API)...")
    try:
        gc, _ = conectar_servicos()
        sh = gc.open(NOME_PLANILHA_MESTRE)
    except Exception as e:
        print(f"❌ Erro Crítico de Conexão. {e}")
        return

    for chave_api, config in LOTERIAS.items():
        print(f"\n🔎 Analisando Jogo: {config['nome']}")
        ws = setup_aba_se_nao_existe(sh, config)
        
        # Pausa inteligente para não sobrecarregar o Google Sheets na leitura inicial
        time.sleep(2)
        
        dados_oficiais = buscar_caixa(config['api'])
        if not dados_oficiais or 'numero' not in dados_oficiais:
            print(f"⚠️ Caixa falhou para {config['nome']}. Pulando...")
            continue
            
        concurso_atual_caixa = int(dados_oficiais['numero'])
        
        try:
            concursos_salvos = [c for c in ws.col_values(1) if c.isdigit()]
        except Exception as e:
            print(f"Aviso ao ler coluna: {e}")
            concursos_salvos = []
            
        topo_local = int(concursos_salvos[0]) if concursos_salvos else 0
        fundo_local = int(concursos_salvos[-1]) if concursos_salvos else concurso_atual_caixa + 1
        
        # ATUALIZAÇÃO DO DIA (VITRINE)
        if topo_local < concurso_atual_caixa:
            print(f"✅ Novo sorteio encontrado ({concurso_atual_caixa}). Atualizando Topo...")
            if concurso_atual_caixa - topo_local > 1:
                dados_oficiais = buscar_caixa(config['api'], topo_local + 1)
            
            if dados_oficiais:
                linha_topo = montar_linha_planilha(config, dados_oficiais)
                inserir_historico_topo(ws, linha_topo)
                lotes = processar_estatisticas(ws, config, str(dados_oficiais['numero']))
                atualizar_nuvem_firebase(config, dados_oficiais, lotes, historico_completo=False)
                salvar_vitrine_app(sh, config, dados_oficiais)
                salvar_cofre_premiacoes(sh, config, dados_oficiais)
        else:
            print(f"✔️ {config['nome']} já está atualizado no concurso {concurso_atual_caixa}.")

        # VARREDURA DE HISTÓRICO REVERSO (INSERÇÃO EM BLOCO - SOLUÇÃO DO ERRO 429)
        if fundo_local > 1:
            limite_batch = 10 
            inicio_busca = fundo_local - 1
            alvo_final = max(1, inicio_busca - limite_batch)
            
            print(f"🚜 Tratorando histórico... Buscando do {inicio_busca} até {alvo_final}")
            linhas_batch = []
            
            for conc_antigo in range(inicio_busca, alvo_final - 1, -1):
                dados_antigos = buscar_caixa(config['api'], conc_antigo)
                if dados_antigos:
                    linhas_batch.append(montar_linha_planilha(config, dados_antigos))
                    atualizar_nuvem_firebase(config, dados_antigos, None, historico_completo=True)
                time.sleep(0.5) 
                
            # Salva TODAS as 10 linhas de histórico numa ÚNICA chamada ao Google (Acaba com o erro Quota Exceeded)
            if linhas_batch:
                try:
                    ws.append_rows(linhas_batch)
                    print(f"📁 {len(linhas_batch)} concursos antigos inseridos em bloco na planilha.")
                except Exception as e:
                    print(f"⚠️ Erro ao inserir bloco no Google Sheets: {e}")

        # FAXINA FINAL (PODA E ALARGAMENTO)
        print(f"✂️ Aplicando Poda Radical em {config['nome']}...")
        aplicar_poda_radical(ws)
        
        # Pausa longa obrigatória no fim de cada lotaria para zerar os limites do Google
        time.sleep(5) 

    print("\n🏁 Plantão GG-456 Concluído com Sucesso Total!")

if __name__ == "__main__":
    executar_trator()
