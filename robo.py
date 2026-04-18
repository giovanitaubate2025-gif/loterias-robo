import requests
import time
import urllib3

# Desativa avisos de segurança
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# SEU LINK NOVO JÁ ESTÁ AQUI:
URL_PLANILHA = "https://script.google.com/macros/s/AKfycbw8pc9Dh-aVqNJ2KmycFAy3xyMj_2bshtDovNOVV-99CO8t5v_sY0IUbshu23Ysbl15xQ/exec"

def perguntar_para_planilha():
    try:
        res = requests.get(URL_PLANILHA, timeout=10)
        if res.status_code == 200:
            return int(res.json().get('ultimo', 0))
    except Exception as e:
        print(f"❌ Erro ao ler a planilha: {e}")
    return -1

def buscar_dados(concurso=""):
    # 1. TENTA NA CAIXA OFICIAL
    url_caixa = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/{concurso}"
    try:
        res = requests.get(url_caixa, verify=False, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if res.status_code == 200 and 'numero' in res.json():
            dados = res.json()
            bolas = dados.get('listaDezenas') or dados.get('dezenas') or []
            ganhadores = 0
            if dados.get('listaRateioPremio') and len(dados['listaRateioPremio']) > 0:
                ganhadores = dados['listaRateioPremio'][0].get('numeroDeGanhadores', 0)
            return int(dados['numero']), dados.get('dataApuracao', ''), bolas, ganhadores
    except:
        pass
    
    # 2. SE A CAIXA TRAVAR, USA A API RESERVA
    if concurso != "":
        url_brasil = f"https://brasilapi.com.br/api/loterias/v1/lotofacil/{concurso}"
        try:
            res = requests.get(url_brasil, timeout=10)
            if res.status_code == 200 and 'concurso' in res.json():
                dados = res.json()
                return int(dados['concurso']), dados.get('data', ''), dados.get('dezenas', []), 0
        except:
            pass
            
    return None, None, None, None

def enviar_lote(lote):
    try:
        res = requests.post(URL_PLANILHA, json={"lote": lote}, timeout=15)
        if "Sucesso" in res.text:
            return True
    except:
        pass
    return False

def executar():
    print("🚜 INICIANDO O TRATOR CIRÚRGICO E ANTI-FALHAS...")
    
    ultimo_planilha = perguntar_para_planilha()
    if ultimo_planilha == -1: return

    concurso_atual, _, _, _ = buscar_dados("")
    if not concurso_atual:
        print("⚠️ Sistemas fora do ar. Tentaremos depois.")
        return
        
    print(f"📍 Sorteio Atual: {concurso_atual} | 📊 Na sua Planilha: {ultimo_planilha}")

    if ultimo_planilha >= concurso_atual:
        print("✅ A Planilha já está perfeitamente atualizada!")
        return

    print(f"⬇️ Faltam {concurso_atual - ultimo_planilha} concursos. Baixando de forma rigorosa...")
    
    lote = []
    
    for num in range(ultimo_planilha + 1, concurso_atual + 1):
        c_num, data, bolas, ganhadores = buscar_dados(num)
        
        # SISTEMA DE TRAVA: Se falhar, ele NÃO PULA o número. Ele para tudo!
        if not c_num or not bolas:
            print(f"❌ A Caixa bloqueou no concurso {num}. Parando por precaução para não pular números e não bagunçar a ordem.")
            break 

        # ORGANIZA AS BOLAS DO MENOR PRO MAIOR (01, 02, 03...)
        ints = [int(x) for x in bolas if str(x).strip() != ""]
        ints.sort()
        bolas_organizadas = [str(x).zfill(2) for x in ints]

        lote.append({
            "concurso": c_num,
            "data": data,
            "bolas": bolas_organizadas,
            "ganhadores": ganhadores
        })
        
        if len(lote) == 50:
            print(f"🚀 Enviando lote perfeito de {len(lote)} concursos...")
            if enviar_lote(lote):
                print(f"✅ Salvo na planilha até o concurso {num}!")
                lote = []
            else:
                print("❌ Erro ao enviar. Parando para segurança.")
                break
            time.sleep(1) 
            
        time.sleep(0.3)

    # Envia os que sobraram na memória caso ele tenha parado antes
    if len(lote) > 0:
        print(f"🚀 Enviando lote final de {len(lote)} concursos...")
        if enviar_lote(lote):
            print("✅ Lote final salvo na planilha com sucesso!")

    print("\n🏁 TRABALHO CONCLUÍDO! Olhe sua planilha agora.")

if __name__ == "__main__":
    executar()
