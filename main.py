import os
import time
import sqlite3
import requests
import schedule          # pip install schedule  ← necessário para agendamento automático
from dotenv import load_dotenv
from datetime import datetime, timedelta


DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(DIRETORIO_ATUAL, '.env'))
CAMINHO_BANCO = os.path.join(DIRETORIO_ATUAL, 'vagas_gupy.db')

TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID_GRUPO")

TRADUCAO_MODELO = {
    "on-site": "Presencial",
    "hybrid":  "Híbrido",
    "remote":  "Remoto"
}

TRADUCAO_TIPO_VAGA = {
    "vacancy_type_effective":   "Efetivo",
    "vacancy_type_apprentice":  "Jovem Aprendiz",
    "vacancy_type_internship":  "Estágio",
    "vacancy_type_temporary":   "Temporário",
    "vacancy_type_freelancer":  "Freelancer"
}


PALAVRAS_CHAVE_TECH = [
    # Desenvolvimento
    "desenvolv", "developer", "software", "frontend", "back-end", "backend",
    "fullstack", "full stack", "programad", "engenharia de software",
    # Dados
    "dados", "data", "analytics", "bi ", "business intelligence",
    "machine learning", "inteligência artificial", "ia ", "ciência de dados",
    # Infraestrutura & Cloud
    "infraestrutura", "cloud", "devops", "sre", "aws", "azure", "gcp",
    "redes", "network", "servidor", "linux", "sysadmin",
    # Segurança
    "segurança", "security", "cibersegurança", "pentest", "soc ",
    # Suporte & Helpdesk
    "suporte", "helpdesk", "help desk", "ti ", "Ti ","t.i.", "técnico de ti",
    "service desk", "field service",
    # QA & UX
    "qualidade", "qa ", "testes", "ux", "ui ", "product",
    # Gerais de TI
    "tecnologia", "information technology", "computação", "sistemas",
    "banco de dados", "database", "erp", "sap", "scrum", "agile",
]

def eh_vaga_tech(titulo: str) -> bool:
    """Retorna True se o título da vaga contiver alguma palavra-chave de TI."""
    titulo_lower = titulo.lower()
    return any(palavra in titulo_lower for palavra in PALAVRAS_CHAVE_TECH)




def iniciar_banco():
    conn   = sqlite3.connect(CAMINHO_BANCO)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vagas_enviadas (
            link             TEXT PRIMARY KEY,
            data_publicacao  TEXT,
            titulo           TEXT
        )
    ''')
    conn.commit()
    return conn, cursor


def enviar_telegram(mensagem: str) -> bool:
    """Envia uma mensagem formatada para o grupo do Telegram."""
    url_tg     = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload_tg = {
        "chat_id":                 CHAT_ID,
        "text":                    mensagem,
        "parse_mode":              "HTML",
        "disable_web_page_preview": True
    }
    try:
        r = requests.post(url_tg, json=payload_tg, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Erro ao enviar para o Telegram: {e}")
        return False


def buscar_vagas_gupy():
    print("🚀 Iniciando varredura na API da Gupy...")
    conn, cursor = iniciar_banco()

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Accept': 'application/json, text/plain, */*',
        'Origin': 'https://portal.gupy.io'
    }

    url_api = "https://employability-portal.gupy.io/api/v1/jobs"

    # -------------------------------------------------------------------------
    # FILTROS DE BUSCA
    # 🔧 CORREÇÃO DO BUG:
    #   Antes: {'state': 'Ribeirão Preto'}  ← errado! 'state' = estado (SP, RJ…)
    #   Agora: {'city': 'Ribeirão Preto', 'state': 'SP'} ← correto!
    #
    # A API da Gupy usa:
    #   'city'           → nome da cidade
    #   'state'          → sigla do estado  (SP, RJ, MG…)
    #   'workplaceTypes' → presencial | remote | hybrid
    # -------------------------------------------------------------------------
    filtros_de_busca = [
        {
            "nome":   "Ribeirão Preto (Presencial/Híbrido)",
            "params": {'city': 'Ribeirão Preto', 'state': 'SP', 'limit': 10},
            "apenas_tech": False   # Mostra TODAS as vagas da cidade
        },
        {
            "nome":   "Estágio de TI — Remoto",
            "params": {
                'workplaceTypes': 'remote',
                'type':           'vacancy_type_internship',   # ← só estágios
                'limit':          10
            },
            "apenas_tech": True    # ← filtra pelo título usando PALAVRAS_CHAVE_TECH
        },
        {
            "nome":   "Estágio de TI — Ribeirão Preto",
            "params": {
                'city':  'Ribeirão Preto',
                'state': 'SP',
                'type':  'vacancy_type_internship',
                'limit': 10
            },
            "apenas_tech": True
        },
    ]

    LIMITE_VELHAS = 20
    PAGINA_MAXIMA = 35

    for filtro in filtros_de_busca:
        print(f"\n🔎 Varrendo: {filtro['nome']}...")
        vagas_velhas = 0

        for pagina in range(1, PAGINA_MAXIMA + 1):
            print(f"   ⏳ Página {pagina}/{PAGINA_MAXIMA}...")
            offset = (pagina - 1) * 10
            params_atuais          = filtro['params'].copy()
            params_atuais['offset'] = offset

            try:
                resposta = requests.get(url_api, headers=headers,
                                        params=params_atuais, timeout=15)

                if resposta.status_code != 200:
                    print(f"🛑 HTTP {resposta.status_code}. Abortando este filtro.")
                    break

                try:
                    dados_json = resposta.json()
                except Exception:
                    print("🛑 Resposta não é JSON válido (possível bloqueio).")
                    break

                lista_vagas = dados_json.get('data', [])
                if not lista_vagas:
                    print("   🔚 Sem mais vagas nesta busca.")
                    break

                for vaga in lista_vagas:
                    link_vaga = vaga.get('jobUrl', '')
                    if not link_vaga:
                        continue

                    titulo  = vaga.get('name', 'Título Indisponível')
                    empresa = vaga.get('careerPageName', 'Empresa não informada')

                    # --- Filtro de tecnologia (quando ativado no filtro) ---
                    if filtro['apenas_tech'] and not eh_vaga_tech(titulo):
                        continue   # pula vagas que não são de TI

                    # --- Localização ---
                    workplace = vaga.get('workplaceType', '')
                    if workplace == 'remote':
                        local = "Qualquer lugar (Remoto)"
                    else:
                        cidade = vaga.get('city', '')
                        estado = vaga.get('state', '')
                        local  = f"{cidade} - {estado}" if cidade else "Local não informado"

                    modelo = TRADUCAO_MODELO.get(workplace, "Não informado")
                    tipo   = TRADUCAO_TIPO_VAGA.get(vaga.get('type', ''), "Outros")
                    pcd    = "Sim" if vaga.get('disabilities') else "Não informado"

                    # --- Data de publicação ---
                    data_iso = vaga.get('publishedDate', '')
                    try:
                        data_limpa = data_iso.split('.')[0]
                        data_utc   = datetime.strptime(data_limpa, "%Y-%m-%dT%H:%M:%S")
                        data_brt   = data_utc - timedelta(hours=3)
                        data_f     = data_brt.strftime("%d/%m/%Y")
                        hora_f     = data_brt.strftime("%H:%M")
                    except Exception:
                        data_f, hora_f = "Sem data", "--:--"

                    # --- Verifica se já foi enviada ---
                    cursor.execute('SELECT 1 FROM vagas_enviadas WHERE link = ?',
                                   (link_vaga,))
                    if cursor.fetchone():
                        vagas_velhas += 1
                        if vagas_velhas >= LIMITE_VELHAS:
                            break
                        continue

                    # --- Nova vaga: salva e envia ---
                    vagas_velhas = 0
                    cursor.execute('INSERT INTO vagas_enviadas VALUES (?, ?, ?)',
                                   (link_vaga, data_f, titulo))
                    conn.commit()

                    emoji_tech = "💻" if filtro['apenas_tech'] else "🎯"
                    mensagem = (
                        f"{emoji_tech} <b>VAGA GUPY — {filtro['nome']}!</b>\n\n"
                        f"💼 <b>Vaga:</b> {titulo}\n"
                        f"🏢 <b>Empresa:</b> {empresa}\n"
                        f"📍 <b>Local:</b> {local}\n"
                        f"💻 <b>Modelo:</b> {modelo}\n"
                        f"📄 <b>Tipo:</b> {tipo}\n"
                        f"♿ <b>PCD:</b> {pcd}\n"
                        f"📅 <b>Data:</b> {data_f} às {hora_f}\n\n"
                        f"🔗 <a href='{link_vaga}'>Clique aqui para aplicar</a>"
                    )

                    sucesso = enviar_telegram(mensagem)
                    status  = "✅" if sucesso else "❌"
                    print(f"   {status} {titulo[:50]}...")
                    time.sleep(2)   # pausa para não sobrecarregar a API

                if vagas_velhas >= LIMITE_VELHAS:
                    print(f"   🛑 {LIMITE_VELHAS} vagas antigas seguidas. Próximo filtro.")
                    break

            except Exception as e:
                print(f"⚠️ Erro inesperado: {e}")
                break

    conn.close()
    print("\n✅ Varredura finalizada!\n")


def executar_varredura_completa():
    """Função principal chamada pelo agendador."""
    print(f"\n{'='*60}")
    print(f"⏰ Execução iniciada em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{'='*60}")
    buscar_vagas_gupy()
    # buscar_vagas_linkedin()   ← descomente quando ativar o LinkedIn


if __name__ == '__main__':
    if not TOKEN or not CHAT_ID:
        print("❌ ERRO: TELEGRAM_TOKEN ou CHAT_ID_GRUPO ausentes no .env!")
    else:
        # --- Executa imediatamente ao iniciar ---
        executar_varredura_completa()
        schedule.every().day.at("08:00").do(executar_varredura_completa)
        while True:
            schedule.run_pending()
            time.sleep(30)   # verifica a fila de tarefas a cada 30 segundos