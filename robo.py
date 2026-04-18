import requests
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# O SEU LINK NOVO DEFINITIVO ESTÁ AQUI:
URL_PLANILHA = "https://script.google.com/macros/s/AKfycbwfVdks7GrnNYgiNPxdvEEB41CPqAJfiS7-UP0rQ34IxJXhYRQ53275_ND25fiEjC5b_Q/exec"

def pegar_ultimo_salvo():
    try:
        res = requests.get(URL_PLANILHA, timeout=10)
        return int(res.json().get('ultimo', 0))
    except:
        return -1

def buscar_oficial_caixa(concurso=""):
    url = f"https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil/{concurso}"
    try:
        res = requests.get(url, verify=False, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        if res.status_code == 200 and 'numero' in res.json():
            dados = res.json()
            
            # Pega as bolas e GARANTE que estão organizadas matematicamente 01, 02, 03...
            bolas_brutas = dados.get('listaDezenas', [])
            if not bolas_brutas: return None # Falha na Caixa
            
            bolas_inteiras = [int(b) for b in bolas_brutas if str(b).strip() != ""]
            bolas_inteiras.sort()
            bolas_formatadas = [str(b).zfill(2) for b in bolas_inteiras]

            ganhadores = 0
            if dados.get('listaRateioPremio'):
                ganhadores = dados['listaRateioPremio'][0].get('numeroDeGanhadores', 0)

            return {
                "concurso": int(dados['numero']),
                "data": dados.get('dataApuracao', ''),
                "bolas": bolas_formatadas,
                "ganhadores": ganhadores
            }
    except:
        pass
    return None

def executar():
    print("🚜 INICIANDO ROBO OFICIAL CAIXA (SISTEMA DE ORDEM ABSOLUTA)...")
    
    ultimo_planilha = pegar_ultimo_salvo()
    if ultimo_planilha == -1: 
        return print("❌ Erro ao ler planilha. O link pode estar errado ou sem permissão.")

    atual = buscar_oficial_caixa("")
    if not atual: 
        return print("⚠️ Site da Caixa fora do ar agora.")

    max_caixa = atual['concurso']
    print(f"📍 Caixa: {max_caixa} | Planilha: {ultimo_planilha}")

    if ultimo_planilha >= max_caixa: 
        return print("✅ Planilha já está em dia. Tudo certo!")

    lote = []
    for num in range(ultimo_planilha + 1, max_caixa + 1):
        print(f"Baixando concurso {num}...")
        dados_concurso = buscar_oficial_caixa(num) if num != max_caixa else atual
        
        if not dados_concurso:
            print(f"❌ Caixa travou no concurso {num}. Parando por segurança para não pular NENHUM.")
            break
            
        lote.append(dados_concurso)

        # Manda de 50 em 50
        if len(lote) == 50 or num == max_caixa:
            try:
                requests.post(URL_PLANILHA, json={"lote": lote}, timeout=20)
                print(f"✅ Lote enviado! Planilha organizando dados (Até o {num})")
            except:
                print("❌ Falha de rede ao enviar para a planilha.")
                break
            lote = []
            time.sleep(2)

    print("🏁 Trabalho finalizado.")

if __name__ == "__main__":
    executar()
