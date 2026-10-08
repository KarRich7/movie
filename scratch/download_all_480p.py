import json
import os
import re
import sys
import yt_dlp
import urllib.parse

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


trailers_map = {
    '258687': 'https://vkvideo.ru/video-227596514_456242995',
    '326': 'https://vkvideo.ru/video-90253744_456243412',
    '435': 'https://vkvideo.ru/video-217157892_456239618',
    '3498': 'https://vkvideo.ru/video-212496568_456253107',
    '1143242': 'https://vkvideo.ru/video-80551593_456241635'
}

trailers_dir = os.path.abspath('parsed_movies/trailers')
os.makedirs(trailers_dir, exist_ok=True)

def download_480p(url, out_path):
    ydl_opts = {
        'format': 'best[height<=480][acodec!=none][vcodec!=none]/url480/best[acodec!=none][vcodec!=none]',
        'outtmpl': out_path,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

for mid, url in trailers_map.items():
    dest = os.path.join(trailers_dir, f'film_{mid}.mp4')
    print(f"Downloading {mid} in 480p...", flush=True)
    download_480p(url, dest)
    size_mb = os.path.getsize(dest) / (1024 * 1024)
    print(f"✅ {mid} saved: {size_mb:.2f} MB", flush=True)

print("🎉 Все 5 трейлеров успешно скачаны в 480p!")
