# Configurações do Instagram Scraper
# IMPORTANTE: Configure suas credenciais antes de usar o script

# ===== INSTRUÇÕES =====
# 1. Substitua INSTAGRAM_USERNAME pela sua conta Instagram
# 2. Substitua INSTAGRAM_PASSWORD pela sua senha
# 3. Salve este arquivo
# 4. Execute: python instagram_scraper.py

# IMPORTANTE: 
# - Use uma conta que tenha acesso aos perfis que deseja fazer scraping
# - Mantenha este arquivo seguro e não compartilhe suas credenciais
# - Adicione config.py ao .gitignore se usar controle de versão 

# ===== CREDENCIAIS DO INSTAGRAM =====
# Substitua pelos dados da sua conta Instagram
INSTAGRAM_USERNAME = "username"
INSTAGRAM_PASSWORD = "password"

# ===== CONFIGURAÇÕES OPCIONAIS =====
# Diretório onde salvar as imagens (relativo ao script)
PRINTS_DIRECTORY = "prints"

# Arquivo para controle de duplicatas
DOWNLOADED_URLS_FILE = "downloaded_urls.txt"

# Delays em segundos (ajuste se necessário)
SCROLL_DELAY = 2.0          # Pausa entre scrolls
DOWNLOAD_DELAY = 0.2        # Pausa entre downloads
PAGE_LOAD_DELAY = 3.0       # Pausa para carregamento de páginas