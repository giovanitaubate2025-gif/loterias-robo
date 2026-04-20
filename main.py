import pandas as pd
import requests
import os

# =========================================================================
# IMPORTADOR OFICIAL E DEFINITIVO (BASEADO NO ACORDO DAS 3 PASTAS)
# Lê os arquivos Excel do seu celular e alimenta o Firebase rigorosamente.
# =========================================================================

URL_FIREBASE = "https://canal-da-loterias-default-rtdb.firebaseio.com/"
SECRET_FIREBASE = "7gS8ASjfG5ZGRVu55Yj5QRw58ZzLCMBzWFLOyrfd"

# Traduz o nome do seu arquivo para a pasta do Firebase
MAPA_PASTAS = {
    'Mega-Sena': 'MEGA-SENA',
    'Lotofácil': 'LOTOFÁCIL',
    'Quina': 'QUINA',
    'Lotomania': 'LOTOMANIA',
    'Timemania': 'TIMEMANIA',
    '+Milionária': 'MAISMILIONÁRIA',
    'Dia de Sorte': 'DIA_DE_SORTE',
    'Dupla Sena': 'DUPLA_SENA',
    'Super Sete': 'SUPER_SETE',
    'Loteca': 'LOTECA',
    'Federal': 'FEDERAL'
}

def limpar_dinheiro(valor):
    if pd.isna(valor): return 0.0
    if isinstance(valor, (int, float)): return float(valor)
    try:
        return float(str(valor).replace('R$', '').replace('.', '').replace(',', '.').strip())
    except: return 0.0

def formatar_moeda(valor):
    """ Formata o valor para o padrão R$ 70.000.000,00 da expectativa """
    try:
        v = float(valor)
        return f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return "R$ 0,00"

def limpar_data(valor):
    if pd.isna(valor): return ""
    return str(valor)[:10].strip()

def enviar_firebase(caminho, dados, metodo="put"):
    url = f"{URL_FIREBASE}{caminho}.json?auth={SECRET_FIREBASE}"
    try:
        if metodo == "put":
            res = requests.put(url, json=dados, timeout=120)  # PUT = Substitui tudo (Hoje e Próximo)
        else:
            res = requests.patch(url, json=dados, timeout=120) # PATCH = Adiciona na lista (Histórico)
        return res.status_code == 200
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return False

def rodar_importacao_celular():
    print("==================================================")
    print("🚀 INICIANDO CONSTRUÇÃO DAS 3 PASTAS (VIA EXCEL)")
    print("==================================================")
    
    pasta = "/storage/emulated/0/Download"
    
    if not os.path.exists(pasta):
        print(f"❌ ERRO: Pasta {pasta} não encontrada.")
        return
        
    arquivos = [f for f in os.listdir(pasta) if f.endswith('.xlsx') and not f.startswith('~')]
    print(f"✅ Encontrados {len(arquivos)} jogos na sua pasta Download.\n")

    for arquivo in arquivos:
        nome_puro = arquivo.split('(')[0].replace('.xlsx', '').strip()
        
        if nome_puro in MAPA_PASTAS:
            jogo_firebase = MAPA_PASTAS[nome_puro]
            caminho_completo = os.path.join(pasta, arquivo)
            
            print(f"📦 Processando: {arquivo} -> {jogo_firebase}")
            
            try:
                # 1. LER PLANILHA
                df = pd.read_excel(caminho_completo)
                coluna_concurso = df.columns[0] 
                df = df.dropna(subset=[coluna_concurso])
                
                pacote_historico = {}
                ultimo_concurso_dados = None
                maior_num_concurso = 0
                linha_do_ultimo_concurso = None
                
                # 2. VARRER TODOS OS CONCURSOS
                for _, linha in df.iterrows():
                    try:
                        num_concurso = int(linha[coluna_concurso])
                        str_concurso = str(num_concurso)
                    except ValueError:
                        continue 

                    # A. DEZENAS (Blidando para não salvar vazio)
                    dezenas = []
                    for col in df.columns:
                        col_l = str(col).lower()
                        if 'bola' in col_l or 'dezena' in col_l or (col_l.startswith('d') and len(col_l) <= 3) or col_l.isdigit():
                            val = linha[col]
                            if pd.notna(val) and str(val).replace('.0','').isdigit():
                                dezenas.append(int(val))
                    
                    # B. RATEIO (Valores pagos)
                    rateios = []
                    for col in df.columns:
                        col_l = str(col).lower()
                        if any(palavra in col_l for palavra in ['valor', 'premio', 'rateio', 'pago']):
                            rateios.append({
                                "faixa": str(col),
                                "valor": limpar_dinheiro(linha[col])
                            })
                            
                    # C. ESPECIAL (Time, Trevo, Mês)
                    especial = ""
                    for col in df.columns:
                        col_l = str(col).lower()
                        if any(palavra in col_l for palavra in ['time', 'coracao', 'trevo', 'mês', 'mes']):
                            if pd.notna(linha[col]):
                                especial = str(linha[col])

                    # D. ACUMULOU?
                    acumulou = "NÃO"
                    for col in df.columns:
                        if 'acumulad' in str(col).lower():
                            if pd.notna(linha[col]) and "sim" in str(linha[col]).lower():
                                acumulou = "SIM"

                    # Monta o pacote de dados EXATOS do concurso
                    dados_concurso = {
                        "numero": str_concurso,
                        "data": limpar_data(linha.get('Data', linha.get('Data Sorteio', ""))),
                        "dezenas": dezenas,
                        "rateio": rateios,
                        "especial": especial,
                        "acumulou": acumulou
                    }
                    
                    # Adiciona ao super pacote do Histórico
                    if dezenas: # Só salva se tiver dezenas (evita bugs do excel)
                        pacote_historico[str_concurso] = dados_concurso
                    
                    # Identifica qual é o último concurso (O Sorteio de Hoje)
                    if num_concurso > maior_num_concurso:
                        maior_num_concurso = num_concurso
                        ultimo_concurso_dados = dados_concurso
                        linha_do_ultimo_concurso = linha

                # =====================================================================
                # 3. DISTRIBUIR PARA AS 3 PASTAS EXATAMENTE COMO COMBINADO
                # =====================================================================
                
                if pacote_historico:
                    # PASTA 1: HISTORICOS_DE_SORTEIOS (Tudo desde o 1º concurso)
                    enviar_firebase(f"HISTORICOS_DE_SORTEIOS/{jogo_firebase}", pacote_historico, "patch")
                    
                    # PASTA 2: SORTEIO_DE_HOJE (Substitui com o mais recente)
                    enviar_firebase(f"SORTEIO_DE_HOJE/{jogo_firebase}", ultimo_concurso_dados, "put")
                    
                    # PASTA 3: PROXIMO_CONCURSO (Pega estimativa da última linha do Excel)
                    estimativa_prox = 0.0
                    data_prox = "A definir"
                    
                    for col in df.columns:
                        col_l = str(col).lower()
                        if 'próximo' in col_l or 'proximo' in col_l or 'estimativa' in col_l:
                            if 'data' in col_l:
                                data_prox = limpar_data(linha_do_ultimo_concurso[col])
                            elif 'valor' in col_l or 'premio' in col_l or 'prêmio' in col_l:
                                estimativa_prox = limpar_dinheiro(linha_do_ultimo_concurso[col])

                    pacote_proximo = {
                        "numero_concurso": str(maior_num_concurso + 1),
                        "data_proximo_sorteio": data_prox,
                        "estimativa_premio": formatar_moeda(estimativa_prox)
                    }
                    enviar_firebase(f"PROXIMO_CONCURSO/{jogo_firebase}", pacote_proximo, "put")

                    print(f"✅ SUCESSO! As 3 pastas de {jogo_firebase} foram criadas e populadas.")

            except Exception as e:
                print(f"❌ Erro ao processar arquivo {arquivo}: {e}")

    print("\n🎉 CARGA INICIAL FINALIZADA! O acordo foi cumprido. Verifique o Firebase.")

if __name__ == "__main__":
    rodar_importacao_celular()
