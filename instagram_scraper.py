import os
import time
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import re
import urllib.parse
import sys
import subprocess
import ctypes

# Importa configurações
try:
    from config import INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD, PRINTS_DIRECTORY, DOWNLOADED_URLS_FILE, SCROLL_DELAY, DOWNLOAD_DELAY, PAGE_LOAD_DELAY
except ImportError:
    print("❌ ERRO: Arquivo config.py não encontrado!")
    print("📝 Crie o arquivo config.py com suas credenciais do Instagram")
    print("📋 Veja o README.md para instruções detalhadas")
    sys.exit(1)

class InstagramScraper:
    def __init__(self):
        self.driver = None
        self.prints_dir = PRINTS_DIRECTORY
        self.downloaded_urls_file = DOWNLOADED_URLS_FILE
        self.downloaded_urls = set()
        self.setup_driver()
        self.create_prints_directory()
        self.load_downloaded_urls()
    
    def find_chrome_executable(self):
        """Encontra o executável do Chrome no Windows"""
        possible_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.getenv('USERNAME')),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def clear_webdriver_cache(self):
        """Limpa cache antigo do webdriver-manager"""
        try:
            import shutil
            wdm_cache = os.path.expanduser("~/.wdm")
            if os.path.exists(wdm_cache):
                print("Limpando cache antigo do webdriver-manager...")
                shutil.rmtree(wdm_cache)
        except:
            pass

    def download_chromedriver(self):
        """Baixa o ChromeDriver manualmente se necessário"""
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            print("Tentando baixar ChromeDriver com webdriver-manager...")
            
            # Limpa cache primeiro
            self.clear_webdriver_cache()
            
            # Obtém o diretório onde o webdriver-manager salva
            chrome_driver_path = ChromeDriverManager().install()
            print(f"Webdriver-manager retornou: {chrome_driver_path}")
            
            # Procura pelo chromedriver.exe no diretório
            if chrome_driver_path:
                driver_dir = os.path.dirname(chrome_driver_path)
                
                # Procura por chromedriver.exe no diretório e subdiretórios
                for root, dirs, files in os.walk(driver_dir):
                    for file in files:
                        if file == "chromedriver.exe":
                            correct_path = os.path.join(root, file)
                            print(f"ChromeDriver encontrado em: {correct_path}")
                            return correct_path
                
                # Se não encontrou, tenta o caminho direto
                direct_path = os.path.join(driver_dir, "chromedriver.exe")
                if os.path.exists(direct_path):
                    return direct_path
            
            raise Exception("ChromeDriver não encontrado nos caminhos esperados")
                
        except Exception as e:
            print(f"Erro com webdriver-manager: {e}")
            print("Tentando método alternativo...")
            
            # Método alternativo: baixar diretamente
            try:
                import zipfile
                import tempfile
                
                # URL do ChromeDriver mais recente (versão estável)
                driver_url = "https://storage.googleapis.com/chrome-for-testing-public/120.0.6099.109/win64/chromedriver-win64.zip"
                
                print("Baixando ChromeDriver diretamente...")
                response = requests.get(driver_url)
                response.raise_for_status()
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
                    tmp_file.write(response.content)
                    zip_path = tmp_file.name
                
                # Extrai o ChromeDriver
                extract_dir = os.path.join(os.getcwd(), "chromedriver")
                os.makedirs(extract_dir, exist_ok=True)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Procura pelo chromedriver.exe no diretório extraído
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        if file == "chromedriver.exe":
                            driver_path = os.path.join(root, file)
                            print(f"ChromeDriver extraído em: {driver_path}")
                            return driver_path
                
                # Cleanup do arquivo zip
                os.unlink(zip_path)
                
                raise Exception("ChromeDriver.exe não encontrado no arquivo baixado")
                    
            except Exception as e2:
                print(f"Erro no método alternativo: {e2}")
                return None
    
    def setup_driver(self):
        """Configura o driver do Chrome com melhor compatibilidade Windows"""
        print("Configurando ChromeDriver...")
        
        # Verifica se o Chrome está instalado
        chrome_path = self.find_chrome_executable()
        if not chrome_path:
            print("ERRO: Google Chrome não encontrado!")
            print("Por favor, instale o Google Chrome primeiro.")
            sys.exit(1)
        
        print(f"Chrome encontrado em: {chrome_path}")
        
        # Configura opções do Chrome
        chrome_options = Options()
        chrome_options.binary_location = chrome_path
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        
        # Suprime logs desnecessários para saída mais limpa
        chrome_options.add_argument("--log-level=3")  # Suprime INFO, WARNING, ERROR
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--disable-gpu-logging")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Tenta obter o ChromeDriver
        driver_path = self.download_chromedriver()
        
        if not driver_path:
            print("ERRO: Não foi possível obter o ChromeDriver!")
            print("Soluções:")
            print("1. Instale manualmente o ChromeDriver")
            print("2. Verifique sua conexão com a internet")
            print("3. Execute como administrador")
            sys.exit(1)
        
        print(f"ChromeDriver configurado: {driver_path}")
        
        try:
            service = Service(driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print("✓ ChromeDriver iniciado com sucesso!")
            
        except Exception as e:
            print(f"ERRO ao inicializar ChromeDriver: {e}")
            print("\nTentativas de solução:")
            print("1. Feche todas as janelas do Chrome")
            print("2. Execute o script como administrador")
            print("3. Verifique se o antivírus não está bloqueando")
            sys.exit(1)
    
    def create_prints_directory(self):
        """Cria o diretório prints se não existir"""
        if not os.path.exists(self.prints_dir):
            os.makedirs(self.prints_dir)
            print(f"Diretório '{self.prints_dir}' criado")
    
    def login_instagram(self, username, password):
        """Faz login no Instagram"""
        print("Fazendo login no Instagram...")
        
        try:
            # Navega para a página de login
            self.driver.get("https://www.instagram.com/accounts/login/")
            time.sleep(3)
            
            # Aguarda elementos de login carregarem
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            
            # Encontra campos de username e password
            username_field = self.driver.find_element(By.NAME, "username")
            password_field = self.driver.find_element(By.NAME, "password")
            
            # Digita credenciais
            print("Inserindo credenciais...")
            username_field.clear()
            username_field.send_keys(username)
            time.sleep(1)
            
            password_field.clear()
            password_field.send_keys(password)
            time.sleep(1)
            
            # Encontra e clica no botão de login
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()
            
            print("Aguardando login...")
            time.sleep(5)
            
            # Verifica se o login foi bem-sucedido usando múltiplos métodos
            success = False
            
            # Método 1: Verifica URL
            current_url = self.driver.current_url
            if "login" not in current_url.lower() and "instagram.com" in current_url:
                success = True
            
            # Método 2: Procura por elementos que indicam login bem-sucedido
            try:
                # Procura por elementos que só aparecem quando logado
                logged_indicators = [
                    "//a[@href='/direct/inbox/']",  # Link de mensagens
                    "//svg[@aria-label='Home']",     # Ícone Home
                    "//svg[@aria-label='New post']", # Ícone novo post
                    "//*[@data-testid='app-header']"  # Header da app
                ]
                
                for indicator in logged_indicators:
                    try:
                        element = WebDriverWait(self.driver, 3).until(
                            EC.presence_of_element_located((By.XPATH, indicator))
                        )
                        if element:
                            success = True
                            break
                    except:
                        continue
            except:
                pass
            
            # Método 3: Verifica se não há campos de login visíveis
            try:
                login_fields = self.driver.find_elements(By.NAME, "username")
                if not login_fields:
                    success = True
            except:
                pass
            
            if success:
                print("✓ Login realizado com sucesso!")
                # Tenta dispensar notificações/popups
                self.dismiss_popups()
                return True
            else:
                print("✗ Falha no login - verifique as credenciais")
                return False
                
        except Exception as e:
            print(f"Erro durante o login: {e}")
            return False
    
    def dismiss_popups(self):
        """Dispensa popups e notificações do Instagram"""
        print("Dispensando popups...")
        
        try:
            # Lista de possíveis textos de botões para dispensar
            dismiss_texts = [
                "Not Now", "Agora não", "Maybe Later", "Talvez depois",
                "Not now", "agora não", "Cancel", "Cancelar"
            ]
            
            for text in dismiss_texts:
                try:
                    button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, f"//button[contains(text(), '{text}')]"))
                    )
                    button.click()
                    print(f"✓ Popup dispensado: {text}")
                    time.sleep(PAGE_LOAD_DELAY)
                except:
                    continue
                    
        except Exception as e:
            print("Nenhum popup encontrado ou erro ao dispensar")
        
        time.sleep(PAGE_LOAD_DELAY)
    
    def load_downloaded_urls(self):
        """Carrega URLs já baixadas de arquivo para evitar duplicatas"""
        try:
            if os.path.exists(self.downloaded_urls_file):
                with open(self.downloaded_urls_file, 'r', encoding='utf-8') as f:
                    self.downloaded_urls = set(line.strip() for line in f if line.strip())
                
                print(f"🔄 Sistema de recuperação ativo!")
                print(f"📂 Carregadas {len(self.downloaded_urls)} URLs já baixadas anteriormente")
                
                if len(self.downloaded_urls) > 0:
                    print(f"✅ O script vai PULAR imagens já baixadas e continuar de onde parou")
                    
                    # Conta arquivos no diretório para comparar
                    try:
                        image_files = [f for f in os.listdir(self.prints_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                        print(f"📁 {len(image_files)} arquivos de imagem encontrados na pasta prints/")
                        
                        if len(image_files) != len(self.downloaded_urls):
                            print(f"⚠️  Discrepância detectada: {len(self.downloaded_urls)} URLs vs {len(image_files)} arquivos")
                            print(f"   Isso é normal se algumas imagens falharam no download anteriormente")
                    except:
                        pass
                else:
                    print("ℹ️  Histórico vazio - será o primeiro download")
            else:
                print("🆕 Nenhum histórico encontrado - iniciando do zero")
                self.downloaded_urls = set()
        except Exception as e:
            print(f"❌ Erro ao carregar histórico: {e}")
            print("⚠️  Continuando sem histórico - pode haver duplicatas")
            self.downloaded_urls = set()
    
    def save_downloaded_url(self, url):
        """Salva URL baixada no arquivo para controle de duplicatas"""
        try:
            self.downloaded_urls.add(url)
            with open(self.downloaded_urls_file, 'a', encoding='utf-8') as f:
                f.write(url + '\n')
        except Exception as e:
            print(f"Erro ao salvar URL: {e}")
    
    def count_elements_detailed(self):
        """Conta elementos usando múltiplos seletores e retorna detalhes"""
        selectors_data = {
            "articles": "article",
            "post_links": "a[href*='/p/']", 
            "images": "article img",
            "grid_items": "div._aagw",
            "media_containers": "div._aagu"
        }
        
        counts = {}
        total_max = 0
        
        for name, selector in selectors_data.items():
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                count = len(elements)
                counts[name] = count
                total_max = max(total_max, count)
            except:
                counts[name] = 0
        
        return total_max, counts

    def extract_and_download_new_images(self, scroll_count):
        """Extrai e baixa novas imagens encontradas no scroll atual"""
        print(f"   🖼️  Procurando novas imagens...")
        
        # Extrai imagens da área visível atual
        new_images = []
        images_found_this_round = set()
        
        # Seletores para imagens no feed
        image_selectors = [
            "article img",
            "div._aagw img", 
            "img[style*='object-fit']",
            "div._aagu img",
            "div._aagv img"
        ]
        
        reels_skipped_this_round = 0
        already_downloaded_this_round = 0
        
        for selector in image_selectors:
            try:
                img_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for img in img_elements:
                    try:
                        src = img.get_attribute('src')
                        alt = img.get_attribute('alt') or ""
                        
                        # Filtros básicos
                        if not (src and 'instagram' in src):
                            continue
                            
                        # Exclui imagens de perfil, stories, etc.
                        basic_excludes = ['profile', 'story', 'avatar', 'highlight']
                        if any(exclude in src.lower() for exclude in basic_excludes):
                            continue
                        if any(exclude in alt.lower() for exclude in basic_excludes):
                            continue
                            
                        # Filtro específico para URLs de reels/vídeos
                        reel_url_patterns = ['/reel/', '/clips/', '/tv/', 'video', 'reel']
                        if any(pattern in src.lower() for pattern in reel_url_patterns):
                            reels_skipped_this_round += 1
                            continue
                            
                        # Verifica se já foi processada nesta sessão
                        if src in images_found_this_round:
                            continue
                        
                        # IMPORTANTE: Verifica se já foi baixada anteriormente
                        if src in self.downloaded_urls:
                            already_downloaded_this_round += 1
                            continue
                        
                        # Verifica se é reel ou vídeo
                        if self.is_reel_or_video(img):
                            reels_skipped_this_round += 1
                            continue
                        
                        # Verifica se o link da postagem é de reel
                        if self.has_reel_link_nearby(img):
                            reels_skipped_this_round += 1
                            continue
                        
                        # Pega a URL da imagem em alta resolução se possível
                        high_res_src = src.replace('150x150/', '').replace('240x240/', '').replace('320x320/', '')
                        
                        images_found_this_round.add(src)
                        new_images.append(high_res_src)
                            
                    except Exception as e:
                        continue
                        
            except Exception as e:
                continue
        
        # Relatório do que foi encontrado neste scroll
        total_images_seen = len(new_images) + already_downloaded_this_round + reels_skipped_this_round
        
        if total_images_seen > 0:
            print(f"   📊 Estatísticas deste scroll:")
            print(f"      🖼️  Total de imagens vistas: {total_images_seen}")
            if already_downloaded_this_round > 0:
                print(f"      🔄 Já baixadas (puladas): {already_downloaded_this_round}")
            if reels_skipped_this_round > 0:
                print(f"      ⏭️  Reels/vídeos ignorados: {reels_skipped_this_round}")
            print(f"      📥 Novas para baixar: {len(new_images)}")
        
        # Baixa as novas imagens encontradas
        if new_images:
            successful_downloads = 0
            for i, img_url in enumerate(new_images):
                # Cria nome do arquivo com timestamp e número do scroll
                current_date = datetime.now()
                date_str = current_date.strftime("%Y%m%d_%H%M%S")
                filename = f"{date_str}_scroll{scroll_count:02d}_img{i+1:03d}.jpg"
                
                print(f"      💾 Baixando {i+1}/{len(new_images)}: {filename}")
                
                if self.download_image(img_url, filename):
                    successful_downloads += 1
                
                # Pequena pausa entre downloads
                time.sleep(DOWNLOAD_DELAY)
            
            print(f"   ✅ {successful_downloads}/{len(new_images)} imagens baixadas com sucesso")
            return successful_downloads
        else:
            if total_images_seen > 0:
                print(f"   ℹ️  Nenhuma imagem nova para baixar neste scroll (todas já existem)")
            else:
                print(f"   ℹ️  Nenhuma imagem encontrada neste scroll")
            return 0

    def scroll_and_download_incremental(self):
        """Rola a página e baixa imagens incrementalmente"""
        print("🚀 Iniciando scroll e download incremental...")
        
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        posts_loaded = 0
        no_change_count = 0
        max_no_change = 5  # Máximo de tentativas sem mudança
        scroll_count = 0
        total_downloads = 0
        
        while True:
            scroll_count += 1
            print(f"\n🔄 Scroll #{scroll_count}")
            
            # Rola até o final da página
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Aguarda o carregamento
            print("   ⏳ Aguardando carregamento...")
            time.sleep(4)
            
            # Verifica se há mais conteúdo para carregar
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            print(f"   📏 Altura da página: {new_height}px (anterior: {last_height}px)")
            
            # Conta elementos com detalhes
            current_posts, details = self.count_elements_detailed()
            
            print(f"   📊 Elementos encontrados:")
            for name, count in details.items():
                print(f"      - {name}: {count}")
            print(f"   🎯 Maior contagem: {current_posts}")
            
            # NOVO: Extrai e baixa imagens imediatamente
            try:
                downloads_this_round = self.extract_and_download_new_images(scroll_count)
                total_downloads += downloads_this_round
                print(f"   📊 Total baixado até agora: {total_downloads} imagens")
            except Exception as e:
                print(f"   ❌ Erro ao baixar imagens neste scroll: {e}")
            
            if current_posts > posts_loaded:
                increment = current_posts - posts_loaded
                print(f"   ✅ +{increment} novos elementos! Total: {current_posts}")
                posts_loaded = current_posts
                no_change_count = 0  # Reset contador
            else:
                print(f"   ⚠️  Nenhum elemento novo detectado")
            
            if new_height == last_height:
                no_change_count += 1
                print(f"   ❌ Altura não mudou ({no_change_count}/{max_no_change})")
                
                if no_change_count >= max_no_change:
                    print("✓ Chegou ao final do feed!")
                    break
                    
                # Tenta rolar mais algumas vezes para garantir
                print("   🔄 Tentando scroll adicional...")
                for i in range(3):
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)
                    newer_height = self.driver.execute_script("return document.body.scrollHeight")
                    if newer_height > new_height:
                        new_height = newer_height
                        print(f"   ✅ Nova altura detectada: {newer_height}px")
                        break
                    print(f"      - Tentativa {i+1}/3: sem mudança")
                else:
                    # Se nenhuma tentativa funcionou, força scroll adicional
                    print("   🚀 Forçando scroll adicional...")
                    self.driver.execute_script("window.scrollBy(0, 1000);")
                    time.sleep(SCROLL_DELAY)
            else:
                height_diff = new_height - last_height
                print(f"   ✅ Página cresceu +{height_diff}px")
                no_change_count = 0  # Reset contador se houve mudança
            
            last_height = new_height
            
            # Verifica se atingiu o limite de "end of posts"
            try:
                end_messages = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'You've seen all') or contains(text(), 'Você viu todas')]")
                if end_messages:
                    print("✅ Mensagem de 'final dos posts' detectada!")
                    break
            except:
                pass
        
        print(f"\n🏁 Scroll e download completos!")
        print(f"📊 Estatísticas finais:")
        final_count, final_details = self.count_elements_detailed()
        for name, count in final_details.items():
            print(f"   - {name}: {count}")
        print(f"🎯 Total de scrolls realizados: {scroll_count}")
        print(f"🎯 Maior contagem de elementos: {final_count}")
        print(f"💾 Total de imagens baixadas: {total_downloads}")
        
        return final_count, total_downloads
    
    def is_reel_or_video(self, img_element):
        """Verifica se a imagem é thumbnail de reel ou vídeo"""
        try:
            # Verifica o elemento pai e elementos próximos para identificar reels
            parent = img_element.find_element(By.XPATH, "./..")
            grandparent = parent.find_element(By.XPATH, "./..")
            
            # Procura por indicadores de vídeo/reel no HTML próximo
            parent_html = parent.get_attribute('outerHTML').lower()
            grandparent_html = grandparent.get_attribute('outerHTML').lower()
            
            # Indicadores de que é um reel/vídeo
            video_indicators = [
                'reel', 'video', 'play', 'duration', 'clip',
                'svg', 'play-button', 'video-player', 'media-video'
            ]
            
            # Verifica se há indicadores de vídeo no HTML dos elementos pais
            for indicator in video_indicators:
                if indicator in parent_html or indicator in grandparent_html:
                    return True
            
            # Verifica se há elementos SVG (ícone de play) próximos
            try:
                svg_elements = grandparent.find_elements(By.TAG_NAME, "svg")
                if svg_elements:
                    return True
            except:
                pass
            
            # Verifica se há span com texto indicando duração
            try:
                spans = grandparent.find_elements(By.TAG_NAME, "span")
                for span in spans:
                    text = span.text.strip()
                    # Procura por padrão de duração (ex: "0:15", "1:23")
                    if re.match(r'\d+:\d+', text):
                        return True
            except:
                pass
                
            return False
            
        except Exception as e:
            return False
    
    def has_reel_link_nearby(self, img_element):
        """Verifica se há links de reel próximos à imagem"""
        try:
            # Procura por elementos <a> próximos que podem conter links de reel
            parent = img_element.find_element(By.XPATH, "./..")
            grandparent = parent.find_element(By.XPATH, "./..")
            
            # Procura por links em elementos pais
            for ancestor in [parent, grandparent]:
                try:
                    links = ancestor.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        href = link.get_attribute('href') or ""
                        if any(pattern in href.lower() for pattern in ['/reel/', '/reels/', '/tv/', 'reel']):
                            return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            return False
    
    def extract_images_from_feed(self):
        """Extrai todas as imagens diretamente do feed, excluindo reels e vídeos"""
        print("Extraindo imagens do feed (excluindo reels/vídeos)...")
        
        # Seletores para imagens no feed
        image_selectors = [
            "article img",
            "div._aagw img", 
            "img[style*='object-fit']",
            "div._aagu img",
            "div._aagv img"
        ]
        
        all_images = []
        images_found = set()  # Para evitar duplicatas
        reels_skipped = 0
        
        for selector in image_selectors:
            try:
                img_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"Encontrados {len(img_elements)} elementos com seletor: {selector}")
                
                for img in img_elements:
                    try:
                        src = img.get_attribute('src')
                        alt = img.get_attribute('alt') or ""
                        
                        # Filtros básicos
                        if not (src and 'instagram' in src):
                            continue
                            
                        # Exclui imagens de perfil, stories, etc.
                        basic_excludes = ['profile', 'story', 'avatar', 'highlight']
                        if any(exclude in src.lower() for exclude in basic_excludes):
                            continue
                        if any(exclude in alt.lower() for exclude in basic_excludes):
                            continue
                            
                        # NOVO: Filtro específico para URLs de reels/vídeos
                        reel_url_patterns = [
                            '/reel/', '/clips/', '/tv/', 'video', 'reel'
                        ]
                        if any(pattern in src.lower() for pattern in reel_url_patterns):
                            reels_skipped += 1
                            print(f"⏭️  Reel ignorado (URL pattern)")
                            continue
                            
                        # Verifica se já foi processada nesta sessão
                        if src in images_found:
                            continue
                        
                        # NOVO: Verifica se já foi baixada anteriormente
                        if src in self.downloaded_urls:
                            print(f"🔄 Imagem já baixada anteriormente, pulando...")
                            continue
                        
                        # NOVO: Verifica se é reel ou vídeo
                        if self.is_reel_or_video(img):
                            reels_skipped += 1
                            print(f"⏭️  Reel/vídeo ignorado (thumbnail)")
                            continue
                        
                        # NOVO: Verifica se o link da postagem é de reel
                        if self.has_reel_link_nearby(img):
                            reels_skipped += 1
                            print(f"⏭️  Reel ignorado (link detectado)")
                            continue
                        
                        # Pega a URL da imagem em alta resolução se possível
                        high_res_src = src.replace('150x150/', '').replace('240x240/', '').replace('320x320/', '')
                        
                        images_found.add(src)
                        all_images.append(high_res_src)
                        print(f"✓ Imagem válida adicionada")
                            
                    except Exception as e:
                        continue
                        
            except Exception as e:
                print(f"Erro com seletor {selector}: {e}")
                continue
        
        print(f"Extraídas {len(all_images)} imagens únicas do feed")
        print(f"Ignorados {reels_skipped} reels/vídeos")
        return all_images
    
    def get_post_date_from_html(self, post_html):
        """Extrai a data da postagem do HTML"""
        try:
            # Procura por timestamp no HTML
            time_elements = self.driver.find_elements(By.CSS_SELECTOR, "time")
            for time_elem in time_elements:
                datetime_attr = time_elem.get_attribute('datetime')
                if datetime_attr:
                    return datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
            
            # Fallback: procura por data em formato de texto
            date_patterns = [
                r'(\d{1,2})\s+(de\s+)?(\w+)\s+(de\s+)?(\d{4})',
                r'(\d{4})-(\d{2})-(\d{2})'
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, post_html)
                if matches:
                    # Tenta parsear a data encontrada
                    return datetime.now()  # Fallback para data atual
            
        except Exception as e:
            print(f"Erro ao extrair data: {e}")
        
        return datetime.now()
    
    def get_current_date(self):
        """Retorna a data atual para naming das imagens"""
        return datetime.now()
    
    def download_image(self, img_url, filename):
        """Baixa uma imagem específica"""
        try:
            # Verifica novamente se não foi baixada (double check)
            if img_url in self.downloaded_urls:
                print(f"🔄 {filename} - já baixada anteriormente")
                return True
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = requests.get(img_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            filepath = os.path.join(self.prints_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            # Salva URL no controle de duplicatas
            self.save_downloaded_url(img_url)
            
            print(f"✓ Imagem salva: {filename}")
            return True
            
        except Exception as e:
            print(f"✗ Erro ao baixar {filename}: {e}")
            return False
    
    def scrape_profile(self, profile_url):
        """Função principal para fazer scraping do perfil"""
        print("Iniciando scraping...")
        print(f"URL do perfil: {profile_url}")
        
        try:
            # Faz login primeiro
            login_success = self.login_instagram(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            if not login_success:
                print("Falha no login detectada pelo script. Verificando manualmente...")
                
                # Verifica novamente se realmente não está logado
                try:
                    self.driver.get("https://www.instagram.com/")
                    time.sleep(3)
                    
                    # Procura por indicadores de login
                    login_indicators = self.driver.find_elements(By.NAME, "username")
                    if not login_indicators:
                        print("✓ Na verdade o login funcionou! Continuando...")
                        login_success = True
                    else:
                        print("⚠️ Confirmado: não está logado. Tentando continuar sem login...")
                except:
                    print("⚠️ Não foi possível verificar status de login. Tentando continuar...")
                
                time.sleep(3)
            
            # Navega para o perfil
            print(f"Navegando para: {profile_url}")
            navigation_success = False
            
            for attempt in range(3):
                try:
                    print(f"Tentativa de navegação {attempt + 1}/3...")
                    self.driver.get(profile_url)
                    time.sleep(5)
                    
                    # Verifica se a navegação foi bem-sucedida
                    current_url = self.driver.current_url
                    if "instagram.com" in current_url:
                        navigation_success = True
                        print("✓ Navegação bem-sucedida!")
                        break
                    else:
                        print(f"URL inesperada: {current_url}")
                        
                except Exception as e:
                    print(f"Erro na navegação (tentativa {attempt + 1}): {e}")
                    if attempt < 2:
                        time.sleep(3)
            
            if not navigation_success:
                print("❌ Falha na navegação após múltiplas tentativas")
                return
            
            # Aguarda o carregamento da página com múltiplas tentativas
            page_loaded = False
            for attempt in range(3):
                try:
                    print(f"Aguardando carregamento da página (tentativa {attempt + 1}/3)...")
                    WebDriverWait(self.driver, 10).until(
                        EC.any_of(
                            EC.presence_of_element_located((By.TAG_NAME, "article")),
                            EC.presence_of_element_located((By.CSS_SELECTOR, "main")),
                            EC.presence_of_element_located((By.CSS_SELECTOR, "[role='main']"))
                        )
                    )
                    page_loaded = True
                    print("✓ Página carregada com sucesso!")
                    break
                except Exception as e:
                    print(f"Tentativa {attempt + 1} falhou: {e}")
                    if attempt < 2:
                        time.sleep(3)
                        self.driver.refresh()
                        time.sleep(5)
            
            if not page_loaded:
                print("⚠️ Não foi possível carregar a página completamente, tentando continuar...")
                time.sleep(5)
            
            # NOVO: Scroll e download incremental
            total_posts, total_downloads = self.scroll_and_download_incremental()
            
            # Relatório final detalhado
            print(f"\n" + "="*60)
            print(f"📊 RELATÓRIO FINAL DE SCRAPING INCREMENTAL")
            print(f"="*60)
            print(f"🎯 Perfil processado: {profile_url}")
            print(f"📱 Total de elementos no feed: {total_posts}")
            print(f"✅ Imagens baixadas durante scroll: {total_downloads}")
            print(f"💾 Total no histórico: {len(self.downloaded_urls)}")
            print(f"📁 Pasta de destino: {os.path.abspath(self.prints_dir)}")
            print(f"="*60)
            
            if total_downloads > 0:
                print(f"✓ Scraping incremental concluído com sucesso!")
            else:
                print(f"⚠️  Nenhuma imagem nova foi baixada durante o scroll")
                
            # Verificação final opcional - extrai qualquer imagem que possa ter ficado
            print(f"\n🔍 Fazendo verificação final...")
            try:
                final_images = self.extract_images_from_feed()
                if final_images:
                    new_images_found = []
                    for img_url in final_images:
                        if img_url not in self.downloaded_urls:
                            new_images_found.append(img_url)
                    
                    if new_images_found:
                        print(f"🎯 Encontradas {len(new_images_found)} imagens adicionais na verificação final")
                        additional_downloads = 0
                        current_date = datetime.now()
                        
                        for i, img_url in enumerate(new_images_found):
                            date_str = current_date.strftime("%Y%m%d_%H%M%S")
                            filename = f"{date_str}_final_{i+1:03d}.jpg"
                            
                            print(f"   📥 Baixando adicional {i+1}/{len(new_images_found)}: {filename}")
                            if self.download_image(img_url, filename):
                                additional_downloads += 1
                        
                        print(f"✅ {additional_downloads}/{len(new_images_found)} imagens adicionais baixadas")
                        total_downloads += additional_downloads
                        
                        print(f"\n📊 TOTAL FINAL: {total_downloads} imagens baixadas")
                    else:
                        print(f"✅ Nenhuma imagem adicional encontrada - scroll incremental foi completo!")
                else:
                    print(f"ℹ️  Nenhuma imagem encontrada na verificação final")
            except Exception as e:
                print(f"❌ Erro na verificação final: {e}")
                
        except Exception as e:
            print(f"Erro durante o scraping: {e}")
            print("Tentando continuar com fallback...")
            
            # Tenta capturar informações úteis mesmo com erro
            try:
                current_url = self.driver.current_url
                print(f"URL atual quando erro ocorreu: {current_url}")
                
                # Tenta pelo menos fazer scroll básico se possível
                if "instagram.com" in current_url:
                    print("Tentando scroll básico...")
                    for i in range(3):
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(SCROLL_DELAY)
                    
                    # Tenta extrair pelo menos algumas imagens
                    try:
                        all_images_urls = self.extract_images_from_feed()
                        if all_images_urls:
                            print(f"Conseguiu extrair {len(all_images_urls)} imagens mesmo com erro!")
                    except:
                        print("Não foi possível extrair imagens com fallback")
                        
            except Exception as fallback_error:
                print(f"Erro no fallback: {fallback_error}")
        
        finally:
            try:
                if self.driver:
                    self.driver.quit()
                    print("✓ Navegador fechado")
            except:
                print("⚠️ Erro ao fechar navegador")

def is_admin():
    """Verifica se o script está sendo executado como administrador"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def request_admin_privileges():
    """Solicita privilégios de administrador"""
    if not is_admin():
        print("Este script precisa de privilégios de administrador para funcionar corretamente.")
        print("Solicitando elevação de privilégios...")
        try:
            # Executa novamente como admin
            ctypes.windll.shell32.ShellExecuteW(
                None, 
                "runas", 
                sys.executable, 
                " ".join([f'"{arg}"' for arg in sys.argv]), 
                None, 
                1
            )
            sys.exit(0)
        except Exception as e:
            print(f"Erro ao elevar privilégios: {e}")
            print("Tente executar o prompt de comando como administrador e rode o script novamente.")
            input("Pressione Enter para continuar mesmo assim...")

def main():
    # Verifica privilégios de administrador
    request_admin_privileges()
    
    if is_admin():
        print("✓ Executando com privilégios de administrador")
    else:
        print("⚠️ Executando sem privilégios de administrador (pode causar problemas)")
    
    # URL do perfil Instagram
    profile_url = input("Digite a URL do perfil Instagram: ").strip()
    
    if not profile_url:
        print("URL não fornecida!")
        return
    
    if 'instagram.com' not in profile_url:
        print("URL inválida! Deve ser uma URL do Instagram.")
        return
    
    scraper = InstagramScraper()
    scraper.scrape_profile(profile_url)

if __name__ == "__main__":
    main() 