
import os
import time
import sqlite3
import requests
import schedule          # pip install schedule  ← necessário para agendamento automático
from dotenv import load_dotenv
import urllib.parse
from datetime import datetime, timedelta

# 6. LINKEDIN API — FUNÇÃO RESERVADA (TOTALMENTE COMENTADA)
#    Para ativar no futuro:
#      1. Crie um app em https://www.linkedin.com/developers/
#      2. Solicite acesso ao produto "Job Postings" ou use a Jobs Search API
#      3. Adicione LINKEDIN_CLIENT_ID e LINKEDIN_ACCESS_TOKEN ao .env
#      4. Descomente o bloco abaixo e chame buscar_vagas_linkedin() dentro de
#         executar_varredura_completa()
# =============================================================================

#
#
# LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
# LINKEDIN_KEYWORDS     = os.getenv("LINKEDIN_KEYWORDS", "tecnologia estágio")
# LINKEDIN_LOCATION     = os.getenv("LINKEDIN_LOCATION", "Ribeirão Preto")
#
# def buscar_vagas_linkedin():
#     """
#     Busca vagas no LinkedIn usando a Jobs Search API (v2).
#     Requer: access_token com escopo r_liteprofile + w_member_social ou
#             parceria com LinkedIn Talent Solutions para a API completa.
#
#     ATENÇÃO: a API pública de vagas do LinkedIn é restrita.
#     Uma alternativa legítima é usar o endpoint não-oficial:
#       GET https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search
#     que não requer autenticação, mas pode ser bloqueado.
#     """
#     print("🔵 Iniciando varredura no LinkedIn...")
#     conn, cursor = iniciar_banco()
#
#     # --- Endpoint não-oficial (sem autenticação) ---
#     url_linkedin = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
#
#     headers_linkedin = {
#         'User-Agent': (
#             'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
#             'AppleWebKit/537.36 (KHTML, like Gecko) '
#             'Chrome/124.0.0.0 Safari/537.36'
#         ),
#         'Accept-Language': 'pt-BR,pt;q=0.9',
#     }
#
#     palavras = urllib.parse.quote(LINKEDIN_KEYWORDS)
#     local    = urllib.parse.quote(LINKEDIN_LOCATION)
#
#     PAGINAS_LI    = 10      # cada página retorna ~10 vagas
#     INICIO_OFFSET = 0
#
#     for pagina in range(PAGINAS_LI):
#         offset = INICIO_OFFSET + (pagina * 10)
#         url    = (
#             f"{url_linkedin}"
#             f"?keywords={palavras}"
#             f"&location={local}"
#             f"&start={offset}"
#             f"&f_JT=I"         # I = Internship (estágio)
#             # f"&f_WT=2"       # 2 = Remote (descomente se quiser só remoto)
#         )
#
#         try:
#             from bs4 import BeautifulSoup   # pip install beautifulsoup4
#
#             resposta = requests.get(url, headers=headers_linkedin, timeout=15)
#             if resposta.status_code != 200:
#                 print(f"🛑 LinkedIn HTTP {resposta.status_code}")
#                 break
#
#             soup      = BeautifulSoup(resposta.text, 'html.parser')
#             cards     = soup.find_all('div', class_='base-card')
#
#             if not cards:
#                 print("   🔚 Sem mais vagas no LinkedIn.")
#                 break
#
#             for card in cards:
#                 # Extrai dados do card HTML
#                 titulo_tag  = card.find('h3', class_='base-search-card__title')
#                 empresa_tag = card.find('h4', class_='base-search-card__subtitle')
#                 local_tag   = card.find('span', class_='job-search-card__location')
#                 link_tag    = card.find('a', class_='base-card__full-link')
#
#                 if not link_tag:
#                     continue
#
#                 titulo  = titulo_tag.get_text(strip=True)  if titulo_tag  else "Título não informado"
#                 empresa = empresa_tag.get_text(strip=True) if empresa_tag else "Empresa não informada"
#                 local   = local_tag.get_text(strip=True)   if local_tag   else "Local não informado"
#                 link    = link_tag.get('href', '').split('?')[0]  # limpa parâmetros
#
#                 if not link:
#                     continue
#
#                 # Filtro de tecnologia (reutiliza a mesma função)
#                 if not eh_vaga_tech(titulo):
#                     continue
#
#                 # Verifica duplicata
#                 cursor.execute('SELECT 1 FROM vagas_enviadas WHERE link = ?', (link,))
#                 if cursor.fetchone():
#                     continue
#
#                 cursor.execute('INSERT INTO vagas_enviadas VALUES (?, ?, ?)',
#                                (link, datetime.now().strftime("%d/%m/%Y"), titulo))
#                 conn.commit()
#
#                 mensagem = (
#                     f"🔵 <b>VAGA LINKEDIN — TI!</b>\n\n"
#                     f"💼 <b>Vaga:</b> {titulo}\n"
#                     f"🏢 <b>Empresa:</b> {empresa}\n"
#                     f"📍 <b>Local:</b> {local}\n"
#                     f"📄 <b>Tipo:</b> Estágio\n\n"
#                     f"🔗 <a href='{link}'>Ver vaga no LinkedIn</a>"
#                 )
#
#                 sucesso = enviar_telegram(mensagem)
#                 print(f"   {'✅' if sucesso else '❌'} LinkedIn: {titulo[:50]}...")
#                 time.sleep(2)
#
#         except Exception as e:
#             print(f"⚠️ Erro LinkedIn: {e}")
#             break
#
#     conn.close()
#     print("✅ Varredura LinkedIn finalizada!")


# =============================================================================
# 7. AGENDAMENTO AUTOMÁTICO
#    O script fica rodando em loop e executa a varredura no intervalo definido.
#    Para manter rodando em servidor/VPS:
#      → Linux: use 'nohup python vagas_gupy.py &' ou crie um serviço systemd
#      → Windows: use o Agendador de Tarefas (Task Scheduler)
#      → Nuvem gratuita: Railway, Render, PythonAnywhere (plano free)
