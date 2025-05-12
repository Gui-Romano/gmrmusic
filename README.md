🎵 GMRMusic

YouTube Music & Video Downloader and Library Manager

GMRMusic is a powerful Python script for downloading music and videos from YouTube, managing their metadata, and organizing them into a clean, searchable library. Whether you're downloading single tracks or entire playlists, GMRMusic helps you maintain a well-structured and customizable music collection.
🚀 Features

    🎧 Download YouTube Content

        Individual videos or entire playlists

        Audio-only (M4A) or full video (MP4/WEBM) options

    🛠️ Audio & Video Processing

        Convert videos to audio

        Choose download quality (e.g., 1080p, 320kbps audio)

    🏷️ Metadata Management

        Auto-embed title, artist, album info

        Manually update metadata via Excel

        Add cover art (thumbnails)

    📁 Library Organization

        Organize by artist folders

        Generate Markdown and Excel catalogs

        AI-powered file/folder name normalization (via Ollama)

    🔁 Duplicate Detection

        Skip files already in the library (optional override)

    ⚙️ System Checks

        Ensure ffmpeg and yt-dlp are installed and ready

    💻 Command-Line Interface

        Simple CLI options for downloading, organizing, and managing your library

📦 Requirements

    Python 3.x

    ffmpeg (in system PATH)

    yt-dlp (in system PATH)

    Python Libraries:

        requests

        pandas

        tqdm

        mutagen

        ollama (optional, for AI organization)

    💡 The script auto-installs tqdm if missing.

🛠️ Installation

    Clone or Download:

git clone <your-repository-url>
cd <repository-name>

Install ffmpeg
Add to system PATH after installation.

Install yt-dlp:

pip install yt-dlp

Install Python Dependencies:

    pip install requests pandas tqdm mutagen ollama

📚 Default Paths

    Music Library: ./biblioteca/ (organized by artist)

    CSV Log: ./biblioteca/biblioteca.csv (download registry)

    SecondBrain Directory: /mnt/shared_folder/SecondBrain/

        musicas.md (Markdown catalog)

        musicas.xlsx (Excel metadata file)

    ✏️ You can edit SECONDBRAIN_PATH in the script to change the export location.

💡 Usage

Run from the command line:

python gmrmusic.py [OPTIONS]

🔽 Download Options
Option	Description
-a, --audio	Download audio (M4A) (default)
-v, --video	Download full video
-m URL	Individual YouTube video URL
-p URL	Playlist URL
-q QUALITY	Set quality (e.g., 720, 1080, 320)
-f, --force	Force download even if already in library
-n NAME, --artist-name NAME	Set custom artist name
-pn, --playlist-artist	Prompt for artist name when downloading a playlist
📂 Library & Metadata
Option	Description
--list	Show songs in the library's CSV
-A, --atualizar	Update metadata based on Excel
--organize	Use AI (Ollama) to normalize names
-M, --meta	(Reserved for metadata actions)
(no args)	Scan library and update Markdown/Excel
🆘 Help

python gmrmusic.py -h

✨ Examples

Download audio (default):

python gmrmusic.py -m "https://youtube.com/..."

Download video in 720p:

python gmrmusic.py -v -m "https://youtube.com/..." -q 720

Download playlist and set artist:

python gmrmusic.py -p "https://youtube.com/..." -n "Artist Name"

List all songs:

python gmrmusic.py --list

Update catalogs (Markdown & Excel):

python gmrmusic.py

Organize library with AI (Ollama required):

python gmrmusic.py --organize

Update metadata from musicas.xlsx:

python gmrmusic.py -A

🧠 Script Overview

Main Functions:

    obter_metadados(): Extract metadata from M4A

    escanear_biblioteca(): Scan library for cataloging

    criar_markdown(), criar_excel(): Generate/update musicas.md and musicas.xlsx

    ler_excel(), atualizar_metadados(): Read metadata edits and apply them

    verificar_ffmpeg(), verificar_ytdlp(): Check system dependencies

    verifica_biblioteca(): Avoid duplicate downloads

    listar_biblioteca(): Display CSV contents

    organizar_biblioteca(): Use AI to clean up names

    definir_metadados(): Write tags and album art

    obter_info_video(), baixar_video(): Gather info and handle downloads

    baixar_video_individual(), baixar_playlist(): Download logic

    atualizar_metadados_existentes(): Infer and update tags based on filenames

    main(): Entry point for argument parsing and dispatching

🤝 Contributing

We welcome contributions!
Found a bug or have an idea? Open an issue or submit a pull request.
