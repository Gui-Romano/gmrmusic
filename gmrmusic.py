import csv
import subprocess
import json
import os
import sys
import time
import argparse
import requests
import platform
import pandas as pd
import shutil
from pathlib import Path
from tqdm import tqdm
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC
from mutagen.mp4 import MP4, MP4Cover
from mutagen import File


# Set the biblioteca path to be relative to the script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BIBLIOTECA_PATH = os.path.join(SCRIPT_DIR, 'biblioteca')
BIBLIOTECA_CSV = os.path.join(BIBLIOTECA_PATH, 'biblioteca.csv')
SECONDBRAIN_PATH = "/mnt/shared_folder/SecondBrain/"
MARKDOWN_FILE = os.path.join(SECONDBRAIN_PATH, "musicas.md")
EXCEL_FILE = os.path.join(SECONDBRAIN_PATH, "musicas.xlsx")

def obter_metadados(arquivo):
    """Extrai metadados de um arquivo de áudio m4a."""
    metadados = {"meta_artista": "", "URL": ""}
    
    try:
        audio = MP4(arquivo)
        # Extrair artista - geralmente '©ART' no formato m4a
        if '©ART' in audio:
            metadados["meta_artista"] = audio['©ART'][0]
        elif 'aART' in audio:
            metadados["meta_artista"] = audio['aART'][0]
        
        # Se houver algum campo personalizado ou URL nas tags
        # Isso é apenas um exemplo, pois URLs não são campos padronizados em m4a
        for tag in audio:
            if 'url' in tag.lower() and audio[tag]:
                metadados["URL"] = audio[tag][0]
                break
    
    except Exception as e:
        print(f"Erro ao ler metadados de {arquivo}: {e}")
    
    return metadados

def escanear_biblioteca():
    """Escaneia a biblioteca de músicas e retorna uma lista de dados."""
    dados = []
    
    print(f"Escaneando diretório: {BIBLIOTECA_PATH}")
    
    # Contar o número total de arquivos m4a para a barra de progresso
    total_arquivos = 0
    for raiz, _, arquivos in os.walk(BIBLIOTECA_PATH):
        for arquivo in arquivos:
            if arquivo.lower().endswith('.m4a'):
                total_arquivos += 1
    
    print(f"Total de arquivos m4a encontrados: {total_arquivos}")
    
    # Usar tqdm para barra de progresso
    progresso = tqdm(total=total_arquivos, desc="Processando arquivos")
    
    # Percorre todos os diretórios e arquivos
    for raiz, _, arquivos in os.walk(BIBLIOTECA_PATH):
        for arquivo in arquivos:
            if arquivo.lower().endswith('.m4a'):
                caminho_completo = os.path.join(raiz, arquivo)
                diretorio_relativo = os.path.relpath(raiz, BIBLIOTECA_PATH)
                
                # Obter metadados
                metadados = obter_metadados(caminho_completo)
                
                # Adicionar à lista de dados com coluna para novo nome
                dados.append({
                    "Diretório": diretorio_relativo,
                    "Nome_arquivo": arquivo,
                    "Novo_Nome": "",  # Coluna vazia para possível renomeação
                    "meta_artista": metadados["meta_artista"],
                    "URL": metadados["URL"],
                    "Tags": ""  # Campo vazio para tags que podem ser adicionadas manualmente
                })
                
                progresso.update(1)
    
    progresso.close()
    print(f"Processamento concluído. Total de arquivos catalogados: {len(dados)}")
    return dados

def criar_markdown(dados):
    """Cria ou atualiza o arquivo markdown com os dados."""
    # Verifica se o diretório existe
    os.makedirs(os.path.dirname(MARKDOWN_FILE), exist_ok=True)
    
    # Criar conteúdo do markdown
    conteudo = "# Biblioteca de Músicas\n\n"
    conteudo += "| Diretório | Nome_arquivo | Novo_Nome | meta_artista | URL | Tags |\n"
    conteudo += "| --------- | ------------ | --------- | ------------ | --- | ---- |\n"
    
    for item in dados:
        novo_nome = item.get('Novo_Nome', '')
        conteudo += f"| {item['Diretório']} | {item['Nome_arquivo']} | {novo_nome} | {item['meta_artista']} | {item['URL']} | {item.get('Tags', '')} |\n"
    
    # Escrever no arquivo
    with open(MARKDOWN_FILE, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    
    print(f"Arquivo markdown criado/atualizado: {MARKDOWN_FILE}")

def criar_excel(dados):
    """Cria ou atualiza o arquivo Excel com os dados."""
    # Verifica se o diretório existe
    os.makedirs(os.path.dirname(EXCEL_FILE), exist_ok=True)
    
    # Criar DataFrame e salvar como Excel
    df = pd.DataFrame(dados)
    df.to_excel(EXCEL_FILE, index=False)
    
    print(f"Arquivo Excel criado/atualizado: {EXCEL_FILE}")

def ler_excel():
    """Lê o arquivo Excel e retorna os dados."""
    if not os.path.exists(EXCEL_FILE):
        print(f"Arquivo Excel não encontrado: {EXCEL_FILE}")
        return []
    
    try:
        # Verificar se o arquivo Excel existe
        print(f"Lendo arquivo Excel: {EXCEL_FILE}")
        
        # Exibir cabeçalhos do arquivo para diagnóstico
        df = pd.read_excel(EXCEL_FILE)
        print(f"Colunas encontradas no Excel: {list(df.columns)}")
        
        # Normalizar nomes das colunas para evitar problemas de case sensitivity
        df.columns = [col.strip() for col in df.columns]
        
        # Verificar se as colunas necessárias existem
        colunas_requeridas = ['Diretório', 'Nome_arquivo']
        for col in colunas_requeridas:
            if col not in df.columns and col.lower() not in [c.lower() for c in df.columns]:
                print(f"AVISO: Coluna '{col}' não encontrada no arquivo Excel")
        
        return df.to_dict('records')
    except Exception as e:
        print(f"Erro ao ler o arquivo Excel: {e}")
        return []

def atualizar_metadados(dados_atualizados):
    """Atualiza os metadados dos arquivos baseado nos dados do Excel."""
    atualizados = 0
    renomeados = 0
    
    # Iniciar barra de progresso
    barra = tqdm(total=len(dados_atualizados), desc="Atualizando arquivos")
    
    for item in dados_atualizados:
        # Verificar as chaves disponíveis
        diretorio = item.get('Diretório', '')
        nome_arquivo = item.get('Nome_arquivo', '')
        novo_nome = item.get('Novo_Nome', '')
        
        # Tentar diferentes possíveis nomes para a chave de artista
        meta_artista = None
        for possivel_chave in ['meta_artista', 'Meta_artista', 'meta artista', 'Meta artista']:
            if possivel_chave in item:
                meta_artista = item[possivel_chave]
                break
        
        if not diretorio or not nome_arquivo:
            barra.update(1)
            continue
            
        # Caminho completo para o arquivo
        caminho_arquivo = os.path.join(BIBLIOTECA_PATH, diretorio, nome_arquivo)
        
        # Verificar se o arquivo existe
        if not os.path.exists(caminho_arquivo):
            barra.update(1)
            continue
        
        try:
            # Atualizar metadados apenas se o arquivo existe
            alterado = False
            
            if meta_artista:
                audio = MP4(caminho_arquivo)
                audio['©ART'] = [meta_artista]
                audio.save()
                alterado = True
                atualizados += 1
            
            # Processar renomeação se o novo nome foi fornecido
            if novo_nome and novo_nome != nome_arquivo and novo_nome.strip():
                novo_caminho = os.path.join(BIBLIOTECA_PATH, diretorio, novo_nome)
                
                # Verificar se o novo nome já tem a extensão correta
                if not novo_nome.lower().endswith('.m4a'):
                    novo_caminho += '.m4a'
                
                # Verificar se o destino não existe para evitar sobrescrever
                if not os.path.exists(novo_caminho):
                    shutil.move(caminho_arquivo, novo_caminho)
                    renomeados += 1
                    alterado = True
            
            if alterado:
                barra.set_description(f"Atualizados: {atualizados}, Renomeados: {renomeados}")
        
        except Exception as e:
            print(f"\nErro ao processar {caminho_arquivo}: {e}")
        
        # Atualizar a barra de progresso
        barra.update(1)
    
    # Fechar a barra de progresso
    barra.close()
    print(f"\nProcessamento concluído!")
    print(f"Total de arquivos com metadados atualizados: {atualizados}")
    print(f"Total de arquivos renomeados: {renomeados}")


def verificar_ffmpeg():
    """Verifica se o ffmpeg está instalado e disponível no PATH."""
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False

def verificar_ytdlp():
    """Verifica se o yt-dlp está instalado e disponível no PATH."""
    try:
        subprocess.run(['yt-dlp', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False

def verifica_biblioteca(video_url):
    """Verifica se a música já foi baixada anteriormente."""
    if not os.path.exists(BIBLIOTECA_CSV):
        # Se o arquivo não existir, cria-o com o cabeçalho
        with open(BIBLIOTECA_CSV, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Video URL', 'Canal'])
        return False
    
    # Verifica se o URL já está no arquivo
    with open(BIBLIOTECA_CSV, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Pula o cabeçalho
        for row in reader:
            if row and row[0] == video_url:
                return True
    
    return False

def listar_biblioteca():
    """Lista todas as músicas registradas na biblioteca."""
    if not os.path.exists(BIBLIOTECA_CSV):
        print("❌ Biblioteca ainda não foi criada.")
        return
    
    print("\n📚 Conteúdo da biblioteca:")
    print("-" * 80)
    
    with open(BIBLIOTECA_CSV, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Pula o cabeçalho
        
        count = 0
        for row in reader:
            if row:
                count += 1
                print(f"{count}. URL: {row[0]}")
                print(f"   Canal: {row[1]}")
                print("-" * 80)
        
        if count == 0:
            print("Biblioteca vazia. Nenhuma música registrada.")
        else:
            print(f"Total de músicas: {count}")
            

def normalizar_nome_artista(nome_artista):
    """Usa o modelo para normalizar o nome do artista."""
    prompt = f"""
Sua tarefa é normalizar o nome do artista musical a seguir, corrigindo a formatação e removendo caracteres especiais desnecessários.
Mantenha apenas letras, números, espaços e hífens. Não use underscores.
Retorne APENAS o nome normalizado, sem explicações ou texto adicional.
Nome original: {nome_artista}
"""
    resultado = consultar_ollama(prompt)
    if not resultado:
        return nome_artista
    
    # Limpa ainda mais o resultado para garantir que seja um nome de pasta válido
    resultado = resultado.replace('/', '-').replace('\\', '-').replace(':', '-')
    resultado = resultado.strip()
    
    # Se o resultado for vazio ou muito diferente, mantenha o original
    if not resultado or len(resultado) < 2:
        return nome_artista
        
    return resultado

def normalizar_nome_arquivo(nome_arquivo, extensao):
    """Usa o modelo para normalizar o nome do arquivo."""
    # Remove a extensão para processamento
    nome_base = nome_arquivo.replace('.' + extensao, '')
    
    prompt = f"""
Sua tarefa é normalizar o nome deste arquivo de música, mantendo informações importantes como título e artista, 
mas removendo caracteres especiais desnecessários e melhorando a formatação.
Mantenha apenas letras, números, espaços e hífens.
Retorne APENAS o nome normalizado, sem explicações ou texto adicional.
Nome original: {nome_base}
"""
    resultado = consultar_ollama(prompt)
    if not resultado:
        return nome_arquivo
    
    # Limpa ainda mais o resultado para garantir que seja um nome de arquivo válido
    resultado = resultado.replace('/', '-').replace('\\', '-').replace(':', '-')
    resultado = resultado.strip()
    
    # Se o resultado for vazio ou muito diferente, mantenha o original
    if not resultado or len(resultado) < 2:
        return nome_arquivo
        
    return f"{resultado}.{extensao}"

def organizar_biblioteca():
    """Organiza a biblioteca usando IA para melhorar nomes de pastas e arquivos."""
    if not os.path.exists(BIBLIOTECA_PATH):
        print("❌ Biblioteca não encontrada.")
        return False
    
    print("\n🧠 Conectando à API do Ollama...")
    # Teste de conexão com o Ollama
    teste = consultar_ollama("Responda apenas com 'OK' se você estiver funcionando corretamente.")
    if not teste or "OK" not in teste.upper():
        print("❌ Não foi possível conectar ao servidor Ollama ou modelo não disponível.")
        return False
    
    print("✅ Conexão com Ollama estabelecida.")
    print("\n🔍 Iniciando organização da biblioteca...")
    
    # Lista para rastrear mudanças
    mudancas_artistas = {}
    mudancas_arquivos = []
    contagem_total = 0
    contagem_processados = 0
    
    # Primeiro, conte o número total de arquivos para a barra de progresso
    for pasta_artista in os.listdir(BIBLIOTECA_PATH):
        caminho_pasta = os.path.join(BIBLIOTECA_PATH, pasta_artista)
        if os.path.isdir(caminho_pasta) and pasta_artista != "downloads_puros":
            contagem_total += len([f for f in os.listdir(caminho_pasta) if os.path.isfile(os.path.join(caminho_pasta, f))])
    
    pbar = tqdm(total=contagem_total, desc="Organizando biblioteca", unit="arquivo")
    
    # Organiza os arquivos por artista
    for pasta_artista in os.listdir(BIBLIOTECA_PATH):
        caminho_pasta = os.path.join(BIBLIOTECA_PATH, pasta_artista)
        
        # Ignora a pasta de downloads e arquivos (como o CSV)
        if not os.path.isdir(caminho_pasta) or pasta_artista == "downloads_puros":
            continue
        
        # Normaliza o nome do artista
        novo_nome_artista = normalizar_nome_artista(pasta_artista)
        if novo_nome_artista != pasta_artista:
            mudancas_artistas[pasta_artista] = novo_nome_artista
            novo_caminho_pasta = os.path.join(BIBLIOTECA_PATH, novo_nome_artista)
            
            # Se já existir uma pasta com o novo nome, unifica os conteúdos
            if os.path.exists(novo_caminho_pasta):
                print(f"📁 Unificando pasta: {pasta_artista} → {novo_nome_artista}")
                # Movemos os arquivos um por um
                for arquivo in os.listdir(caminho_pasta):
                    caminho_arquivo = os.path.join(caminho_pasta, arquivo)
                    if os.path.isfile(caminho_arquivo):
                        novo_caminho_arquivo = os.path.join(novo_caminho_pasta, arquivo)
                        # Se o arquivo já existir, adiciona um sufixo
                        if os.path.exists(novo_caminho_arquivo):
                            nome_base, ext = os.path.splitext(arquivo)
                            arquivo = f"{nome_base}_alt{ext}"
                            novo_caminho_arquivo = os.path.join(novo_caminho_pasta, arquivo)
                        os.rename(caminho_arquivo, novo_caminho_arquivo)
                # Remove a pasta antiga vazia
                os.rmdir(caminho_pasta)
                # Atualiza o caminho para continuar o processamento
                caminho_pasta = novo_caminho_pasta
            else:
                # Renomeia a pasta
                print(f"📁 Renomeando pasta: {pasta_artista} → {novo_nome_artista}")
                os.rename(caminho_pasta, novo_caminho_pasta)
                # Atualiza o caminho para continuar o processamento
                caminho_pasta = novo_caminho_pasta
        
        # Processa os arquivos dentro da pasta
        for arquivo in os.listdir(caminho_pasta):
            caminho_arquivo = os.path.join(caminho_pasta, arquivo)
            if os.path.isfile(caminho_arquivo):
                # Extrai a extensão
                _, ext = os.path.splitext(arquivo)
                ext = ext.lstrip('.').lower()
                
                # Normaliza o nome do arquivo
                novo_nome_arquivo = normalizar_nome_arquivo(arquivo, ext)
                if novo_nome_arquivo != arquivo:
                    novo_caminho_arquivo = os.path.join(caminho_pasta, novo_nome_arquivo)
                    # Se já existir um arquivo com o novo nome, adiciona um sufixo
                    if os.path.exists(novo_caminho_arquivo):
                        nome_base, ext_com_ponto = os.path.splitext(novo_nome_arquivo)
                        novo_nome_arquivo = f"{nome_base}_alt{ext_com_ponto}"
                        novo_caminho_arquivo = os.path.join(caminho_pasta, novo_nome_arquivo)
                    
                    os.rename(caminho_arquivo, novo_caminho_arquivo)
                    mudancas_arquivos.append((arquivo, novo_nome_arquivo))
                
                contagem_processados += 1
                pbar.update(1)
    
    pbar.close()
    
    print(f"\n✅ Organização concluída! Processados {contagem_processados} arquivos.")
    print(f"📊 Resumo: {len(mudancas_artistas)} pastas renomeadas, {len(mudancas_arquivos)} arquivos renomeados.")
    
    # Exibe as mudanças de nomes de artistas
    if mudancas_artistas:
        print("\n🎨 Mudanças de nomes de artistas:")
        for original, novo in mudancas_artistas.items():
            print(f"  • {original} → {novo}")
    
    # Exibe alguns exemplos de mudanças de nomes de arquivos (no máximo 10)
    if mudancas_arquivos:
        print("\n📄 Exemplos de mudanças de nomes de arquivos:")
        for original, novo in mudancas_arquivos[:10]:
            print(f"  • {original} → {novo}")
        
        if len(mudancas_arquivos) > 10:
            print(f"  ... e mais {len(mudancas_arquivos) - 10} mudanças.")
    
    return True

def definir_metadados(arquivo_path, artista, titulo, album, thumbnail_url=None):
    """Define os metadados do arquivo de áudio."""
    print(f"📝 Configurando metadados para: {os.path.basename(arquivo_path)}")
    extensao = os.path.splitext(arquivo_path)[1].lower()
    
    try:
        if extensao == '.m4a':
            # Para arquivos M4A (MP4)
            audio = MP4(arquivo_path)
            audio['\xa9nam'] = [titulo]  # Nome/título
            audio['\xa9ART'] = [artista]  # Artista
            audio['\xa9alb'] = [album]    # Álbum
            
            # Baixar e adicionar thumbnail como capa se disponível
            if thumbnail_url:
                try:
                    print("🖼️ Baixando thumbnail para capa...")
                    response = requests.get(thumbnail_url, timeout=30)
                    if response.status_code == 200:
                        cover_data = response.content
                        # Determinar o formato da imagem
                        if thumbnail_url.lower().endswith('.jpg') or thumbnail_url.lower().endswith('.jpeg'):
                            cover_format = MP4Cover.FORMAT_JPEG
                        else:
                            cover_format = MP4Cover.FORMAT_PNG
                        audio['covr'] = [MP4Cover(cover_data, cover_format)]
                        print("✅ Capa adicionada com sucesso!")
                    else:
                        print(f"⚠️ Não foi possível baixar a thumbnail: {response.status_code}")
                except Exception as e:
                    print(f"⚠️ Erro ao adicionar capa: {str(e)}")
            
            audio.save()
            
        elif extensao == '.mp3':
            # Para arquivos MP3
            try:
                audio = EasyID3(arquivo_path)
            except:
                # Se não existir tags, inicializa
                audio = File(arquivo_path, easy=True)
                audio.add_tags()
                
            audio['title'] = titulo
            audio['artist'] = artista
            audio['album'] = album
            audio.save()
            
            # Adicionar capa (requer ID3 completo)
            if thumbnail_url:
                try:
                    print("🖼️ Baixando thumbnail para capa...")
                    response = requests.get(thumbnail_url, timeout=30)
                    if response.status_code == 200:
                        cover_data = response.content
                        audio = ID3(arquivo_path)
                        # Determinar o tipo de imagem
                        mime = 'image/jpeg' if thumbnail_url.lower().endswith('.jpg') or thumbnail_url.lower().endswith('.jpeg') else 'image/png'
                        audio.add(APIC(
                            encoding=3,  # UTF-8
                            mime=mime,
                            type=3,  # 3 é para capa frontal
                            desc='Cover',
                            data=cover_data
                        ))
                        audio.save()
                        print("✅ Capa adicionada com sucesso!")
                    else:
                        print(f"⚠️ Não foi possível baixar a thumbnail: {response.status_code}")
                except Exception as e:
                    print(f"⚠️ Erro ao adicionar capa: {str(e)}")
        
        else:
            print(f"⚠️ Formato não suportado para metadados: {extensao}")
            return False
        
        print("✅ Metadados configurados com sucesso!")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao definir metadados: {str(e)}")
        return False

def obter_info_video(yt_dlp_cmd, video_url):
    """Obtém informações do vídeo usando yt-dlp."""
    try:
        command_video = [yt_dlp_cmd, '-J', video_url]
        result_video = subprocess.run(command_video, capture_output=True, text=True, check=True)
        video_info = json.loads(result_video.stdout)
        return video_info
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"⚠️  Erro ao obter info do vídeo {video_url}. ({str(e)})")
        return None

def baixar_video(yt_dlp_cmd, video_url, video_info, download_dir, apenas_audio, quality, force=False, idx=None, total_videos=None):
    """Baixa um vídeo individual."""
    artist = video_info.get('uploader', 'Desconhecido').strip()
    title = video_info.get('title', 'Sem título').strip()
    album = video_info.get('album') or "YouTube"
    ext = "m4a" if apenas_audio else "webm"
    filename = f"{artist}_{title}_{album}.{ext}".replace('/', '-').replace('\\', '-')
    artista_folder = os.path.join(BIBLIOTECA_PATH, artist)
    destino_final = os.path.join(artista_folder, filename)
    
    if os.path.exists(destino_final) and not force:
        print(f"⏩ Música já existe: {destino_final}. Pulando...")
        return False
    
    command = [yt_dlp_cmd]
    if not apenas_audio:
        if quality:
            command += ['-f', f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]']
        else:
            command += ['-f', 'best']
    else:
        command += ['-x', '--audio-format', 'm4a', '--audio-quality', '0']
    
    command += ['-o', os.path.join(download_dir, '%(title)s.%(ext)s')]
    command.append(video_url)
    
    if idx is not None and total_videos is not None:
        print(f"\n▶️  Baixando vídeo {idx}/{total_videos}: {title}")
    else:
        print(f"\n▶️  Baixando: {title}")
    
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    pbar_desc = f"[{idx}/{total_videos}] {title[:30]}..." if idx is not None else f"{title[:30]}..."
    pbar = tqdm(total=100, desc=pbar_desc, unit='%')
    
    for line in process.stdout:
        if "%" in line:
            try:
                percent = float(line.split('%')[0].split()[-1])
                pbar.n = percent
                pbar.refresh()
            except Exception:
                pass
    
    process.wait()
    pbar.close()
    
    try:
        arquivos_baixados = os.listdir(download_dir)
        if not arquivos_baixados:
            print(f"⚠️  Nenhum arquivo encontrado para {title}.")
            return False
        
        arquivo_downloadado = arquivos_baixados[0]
        caminho_origem = os.path.join(download_dir, arquivo_downloadado)
        os.makedirs(artista_folder, exist_ok=True)
        os.rename(caminho_origem, destino_final)
        print(f"📦 Movido para biblioteca: {destino_final}")
        
        # Adiciona metadados ao arquivo
        thumbnail_url = None
        thumbnails = video_info.get('thumbnails', [])
        if thumbnails:
            # Pega a maior thumbnail disponível
            thumbnails.sort(key=lambda x: x.get('height', 0) * x.get('width', 0), reverse=True)
            thumbnail_url = thumbnails[0].get('url')
            
        definir_metadados(destino_final, artist, title, album, thumbnail_url)
        
        # Registra o download no CSV
        with open(BIBLIOTECA_CSV, 'a', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([video_url, artist])
        
        for f in os.listdir(download_dir):
            os.remove(os.path.join(download_dir, f))
            
        return True
    except Exception as e:
        print(f"❌ Erro ao mover/renomear {title}: {str(e)}")
        return False

def baixar_video_individual(video_url, apenas_audio=True, quality=None, force=False, artist_name=None):
    """Baixa um vídeo individual do YouTube."""
    if not verificar_ffmpeg():
        print("⚠️  ffmpeg não encontrado. Instale e adicione ao PATH antes de continuar.")
        return False
    
    if not verificar_ytdlp():
        print("⚠️  yt-dlp não encontrado. Instale e adicione ao PATH antes de continuar.")
        print("   Execute: pip install yt-dlp")
        return False
    
    # Verifica se o vídeo já foi baixado
    if verifica_biblioteca(video_url) and not force:
        print(f"⏩ Vídeo já registrado na biblioteca: {video_url}. Pulando...")
        return False
    
    # Garante que a pasta biblioteca existe
    os.makedirs(BIBLIOTECA_PATH, exist_ok=True)
    
    download_dir = os.path.join(BIBLIOTECA_PATH, "downloads_puros")
    os.makedirs(download_dir, exist_ok=True)
    
    # Use 'yt-dlp' command directly
    yt_dlp_cmd = 'yt-dlp'
    
    print("\n🔍 Obtendo informações do vídeo...")
    video_info = obter_info_video(yt_dlp_cmd, video_url)
    
    if not video_info:
        print("❌ Não foi possível obter informações do vídeo.")
        return False
    
    # Se um nome de artista foi especificado, sobrescreve o valor de uploader
    if artist_name:
        video_info['uploader'] = artist_name
    
    start_time = time.time()
    result = baixar_video(yt_dlp_cmd, video_url, video_info, download_dir, apenas_audio, quality, force)
    
    elapsed_time = time.time() - start_time
    minutes, seconds = divmod(int(elapsed_time), 60)
    
    if result:
        print(f"\n✅ Download concluído em {minutes}min {seconds}s!")
        return True
    return False

def baixar_playlist(playlist_url, apenas_audio=True, quality=None, force=False, artist_name=None):
    """Baixa todos os vídeos de uma playlist do YouTube."""
    if not verificar_ffmpeg():
        print("⚠️  ffmpeg não encontrado. Instale e adicione ao PATH antes de continuar.")
        return False
    
    if not verificar_ytdlp():
        print("⚠️  yt-dlp não encontrado. Instale e adicione ao PATH antes de continuar.")
        print("   Execute: pip install yt-dlp")
        return False
    
    # Garante que a pasta biblioteca existe
    os.makedirs(BIBLIOTECA_PATH, exist_ok=True)
    
    download_dir = os.path.join(BIBLIOTECA_PATH, "downloads_puros")
    os.makedirs(download_dir, exist_ok=True)
    
    # Use 'yt-dlp' command directly
    yt_dlp_cmd = 'yt-dlp'
    
    print("\n🔍 Obtendo informações da playlist...")
    try:
        result = subprocess.run([yt_dlp_cmd, '--flat-playlist', '-J', playlist_url], 
                                capture_output=True, text=True, check=True)
        playlist_data = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao obter informações da playlist: {e}")
        return False
    except json.JSONDecodeError:
        print("❌ Erro ao processar informações da playlist. Verifique se a URL é válida.")
        return False
    
    if 'entries' not in playlist_data:
        print("❌ Não foi possível encontrar vídeos na playlist.")
        return False
    
    entries = playlist_data['entries']
    total_videos = len(entries)
    videos_baixados = 0
    videos_pulados = 0
    
    start_time = time.time()
    
    for idx, entry in enumerate(entries, start=1):
        if not entry:
            continue
        
        video_id = entry.get('id')
        if not video_id:
            continue
        
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Verifica se o vídeo já foi baixado
        if verifica_biblioteca(video_url) and not force:
            print(f"⏩ Vídeo já registrado na biblioteca: {video_url}. Pulando...")
            videos_pulados += 1
            continue
        
        video_info = obter_info_video(yt_dlp_cmd, video_url)
        if not video_info:
            continue
        
        # Se um nome de artista foi especificado, sobrescreve o valor de uploader
        if artist_name:
            video_info['uploader'] = artist_name
        
        if baixar_video(yt_dlp_cmd, video_url, video_info, download_dir, apenas_audio, quality, force, idx, total_videos):
            videos_baixados += 1
    
    elapsed_time = time.time() - start_time
    minutes, seconds = divmod(int(elapsed_time), 60)
    
    print(f"\n✅ Download concluído em {minutes}min {seconds}s!")
    print(f"📊 Resumo: {videos_baixados} vídeos baixados, {videos_pulados} pulados.")
    
    return True

def atualizar_metadados_existentes():
    """Atualiza os metadados de todos os arquivos existentes na biblioteca."""
    print("\n🔍 Procurando arquivos na biblioteca para atualizar metadados...")
    total_arquivos = 0
    atualizados = 0
    falhas = 0
    
    for pasta_artista in os.listdir(BIBLIOTECA_PATH):
        caminho_pasta = os.path.join(BIBLIOTECA_PATH, pasta_artista)
        
        # Ignora a pasta de downloads e arquivos (como o CSV)
        if not os.path.isdir(caminho_pasta) or pasta_artista == "downloads_puros":
            continue
        
        for arquivo in os.listdir(caminho_pasta):
            caminho_arquivo = os.path.join(caminho_pasta, arquivo)
            if not os.path.isfile(caminho_arquivo):
                continue
                
            ext = os.path.splitext(arquivo)[1].lower()
            if ext not in ['.mp3', '.m4a']:
                continue
                
            total_arquivos += 1
            print(f"\n📄 Processando arquivo: {arquivo}")
            
            # Extrair informações do nome do arquivo
            nome_sem_ext = os.path.splitext(arquivo)[0]
            partes = nome_sem_ext.split('_')
            
            # O padrão é: artista_titulo_album
            artista = pasta_artista  # Usa o nome da pasta como artista
            titulo = nome_sem_ext  # Por padrão, usa o nome inteiro como título
            album = "YouTube"  # Valor padrão
            
            # Tenta extrair mais informações do nome, se possível
            if len(partes) >= 2:
                titulo = partes[1]
            if len(partes) >= 3:
                album = partes[2]
                
            # Atualiza os metadados
            if definir_metadados(caminho_arquivo, artista, titulo, album):
                atualizados += 1
            else:
                falhas += 1
    
    print(f"\n✅ Atualização de metadados concluída!")
    print(f"📊 Resumo: {total_arquivos} arquivos encontrados, {atualizados} atualizados, {falhas} falhas.")
    
    if total_arquivos == 0:
        print("\n❓ Nenhum arquivo de áudio encontrado na biblioteca.")
        
    return atualizados > 0

def main():
    parser = argparse.ArgumentParser(
        description='gmrmusic - Gerenciador de download de músicas e vídeos do YouTube',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''
Exemplos de uso:
  gmrmusic -a -p URL          # Baixa apenas áudio de uma playlist
  gmrmusic -v -m URL          # Baixa vídeo de uma música individual
  gmrmusic -a -m URL -q 320   # Baixa áudio de melhor qualidade
  gmrmusic -v -p URL -q 720   # Baixa vídeos da playlist em 720p
  gmrmusic -p URL -n "Artista"# Baixa playlist e define o nome do artista
  gmrmusic --list             # Lista todas as músicas na biblioteca (corrigido para usar --)
  gmrmusic -a -m URL -f       # Força download mesmo se já existir
  gmrmusic --organize         # Organiza a biblioteca (novo exemplo)
  gmrmusic -h                 # Exibe esta mensagem de ajuda
        
Códigos de saída:
  0 - Operação concluída com sucesso
  1 - Erro durante a execução
  130 - Interrompido pelo usuário (Ctrl+C)
''')
    
    # Argumentos para tipo de conteúdo
    content_group = parser.add_mutually_exclusive_group(required=False)
    content_group.add_argument('-a', '--audio', action='store_true', 
                              help='Baixar apenas áudio (formato M4A)')
    content_group.add_argument('-v', '--video', action='store_true', 
                              help='Baixar vídeo completo (MP4/WEBM)')
   
    # Remover a redefinição: parser = argparse.ArgumentParser(description='Gerenciador de biblioteca de músicas')
    # Adicionar os argumentos restantes ao parser existente:

    parser.add_argument('-A', '--atualizar', action='store_true', 
                        help='Atualizar metadados dos arquivos com base no arquivo Excel')
    # O argumento -up/--update não parece ser utilizado no fluxo de código, mas sua definição é mantida caso seja um trabalho em progresso.
    parser.add_argument('-up', '--update', action='store_true',
                        help='Força a atualização de todos os arquivos mesmo sem alterações')

    # Argumentos para fonte
    source_group = parser.add_mutually_exclusive_group(required=False)
    source_group.add_argument('-p', '--playlist', metavar='URL', 
                             help='URL da playlist do YouTube')
    source_group.add_argument('-m', '--music', metavar='URL', 
                             help='URL do vídeo individual do YouTube')
    
    # Outros argumentos
    # O argumento -M/--meta não parece ser utilizado no fluxo de código, mas sua definição é mantida.
    parser.add_argument('-M','--meta', action='store_true',
                        help='Atualizar metadados')
    parser.add_argument('-q', '--quality', metavar='QUALITY', 
                       help='Qualidade do vídeo (ex: 1080, 720, 480) ou do áudio')
    parser.add_argument('-f', '--force', action='store_true', 
                       help='Forçar download mesmo que já exista na biblioteca')
    # É mais comum usar --list para argumentos longos sem valor.
    parser.add_argument('--list', action='store_true', 
                       help='Listar músicas na biblioteca')
    parser.add_argument('-n', '--artist-name', metavar='ARTIST',
                       help='Define um nome de artista personalizado para organizar os downloads')
    parser.add_argument('-pn', '--playlist-artist', action='store_true',
                       help='Solicita nome do artista ao baixar uma playlist')
    
    # Adicionar o argumento para 'organize'
    parser.add_argument('--organize', action='store_true',
                       help='Organiza a biblioteca usando IA para melhorar nomes de pastas e arquivos.')
    # O argumento -h/--help é adicionado automaticamente pelo argparse
    
    args = parser.parse_args()
    
    try:
        # Verificar se as dependências estão instaladas
        # (O restante do código permanece o mesmo)
        import tqdm # Movido para o início do arquivo, como é padrão
    except ImportError:
        print("Instalando dependências necessárias...")
        import subprocess
        import sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])
        print("Dependências instaladas com sucesso!")
        # Importar novamente após instalação - este import pode ser removido se já estiver no topo
        # import tqdm 
    
    # Verificar argumentos e executar ações correspondentes
    # Corrigido para usar args.list (com dois hífens como definido acima)
    if args.list: 
        listar_biblioteca()
        return True # main() deve retornar True/False ou códigos de saída numéricos
    
    if args.atualizar:
        print("Modo de atualização ativado")
        # Ler dados do Excel e atualizar metadados
        dados_excel = ler_excel()
        if dados_excel:
            atualizar_metadados(dados_excel)
            
            # Após atualizar, reescanear a biblioteca para atualizar o markdown
            print("\nReescaneando biblioteca para atualizar documentação...")
            dados = escanear_biblioteca()
            criar_markdown(dados)
            criar_excel(dados)
            print("Documentação atualizada com sucesso!")
        else:
            print("Sem dados para atualizar. Execute o script sem a flag -A primeiro.")
        return True
    
    # Determinar se é áudio ou vídeo (padrão é áudio se nem -a nem -v for especificado E um download for solicitado)
    # Se -v não for passado, args.video será False. not args.video será True.
    apenas_audio = not args.video
    
    # Definir o nome do artista se necessário
    artist_name = args.artist_name
    
    if args.organize: # Agora args.organize existe
        return organizar_biblioteca()
    elif args.playlist:
        # Se a flag -pn foi usada, solicita o nome do artista
        if args.playlist_artist and not artist_name:
            artist_name = input("\n🎙️ Digite o nome do artista para esta playlist: ").strip()
            if not artist_name:
                print("⚠️ Nome de artista não fornecido. Será usado o nome do uploader original.")
                artist_name = None
        
        return baixar_playlist(args.playlist, apenas_audio, args.quality, args.force, artist_name)
    elif args.music:
        # Permitir o uso de -n também para vídeos individuais
        return baixar_video_individual(args.music, apenas_audio, args.quality, args.force, artist_name)
    else:
        # Modo padrão: escanear biblioteca e atualizar arquivos
        # (Se nenhum dos argumentos acima foi passado, executa esta ação)
        dados = escanear_biblioteca()
        criar_markdown(dados)
        criar_excel(dados)
        print("Biblioteca escaneada e documentos atualizados com sucesso!")
        return True # Adicionado retorno para consistência

if __name__ == "__main__":
    try:
        print(f"🐧 Sistema detectado: {platform.system()}")
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Interrompido pelo usuário.")
        exit(130)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        exit(1)
