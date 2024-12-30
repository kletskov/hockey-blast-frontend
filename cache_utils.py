import os
import time
import requests
from threading import Thread
from options import base_directory_tts_players_html_cache
from html_utils import beautify_tts_html

CACHE_DIR = base_directory_tts_players_html_cache('hello')
CACHE_EXPIRATION = 60 * 60 * 72  # Cache expiration time in seconds (e.g., 1 hour)

def get_cache_file_path(cache_id):
    return os.path.join(CACHE_DIR, f"{cache_id}.html")

def is_cache_valid(file_path):
    if not os.path.exists(file_path):
        return False
    file_mod_time = os.path.getmtime(file_path)
    current_time = time.time()
    return (current_time - file_mod_time) < CACHE_EXPIRATION

def fetch_html(url):
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    return None

def get_html(cache_id, url):
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    
    cache_file_path = get_cache_file_path(cache_id)
    
    if is_cache_valid(cache_file_path):
        with open(cache_file_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    html_content = fetch_html(url)
    if html_content:
        beautified_html = beautify_tts_html(html_content)
        with open(cache_file_path, 'w', encoding='utf-8') as file:
            file.write(beautified_html)
    
    return html_content

def update_cache_async(cache_id, url):
    def update_cache():
        cache_file_path = get_cache_file_path(cache_id)
        html_content = fetch_html(url)
        if html_content:
            beautified_html = beautify_tts_html(html_content)
            with open(cache_file_path, 'w', encoding='utf-8') as file:
                file.write(beautified_html)
    
    if not is_cache_valid(get_cache_file_path(cache_id)):
        thread = Thread(target=update_cache)
        thread.start()