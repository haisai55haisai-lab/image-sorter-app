#!/usr/bin/env python3
"""
画像仕分けツール
画像をサムネイル表示し、チェックボックスで選択したものを指定フォルダに移動
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
import json
import webbrowser
from threading import Timer
import sys

app = Flask(__name__)

# ブラウザが既に開かれたかを追跡
browser_opened = False

# パス設定
BASE_DIR = "/Users/johnstakickm1pro/Library/CloudStorage/GoogleDrive-ozhnsales01@gmail.com/マイドライブ/テスト環境"
SOURCE_DIR = os.path.join(BASE_DIR, "1_生成元画像")
SELECTED_DIR = os.path.join(BASE_DIR, "2_仕分け後元画像")
UNSELECTED_DIR = os.path.join(BASE_DIR, "4_予備保管ファイル")

def get_images():
    """ソースディレクトリから画像ファイル一覧を取得"""
    if not os.path.exists(SOURCE_DIR):
        return []

    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
    images = []

    for filename in sorted(os.listdir(SOURCE_DIR)):
        ext = os.path.splitext(filename)[1].lower()
        if ext in image_extensions:
            images.append(filename)

    return images

@app.route('/')
def index():
    """メインページ"""
    filter_char = request.args.get('filter', 'all')

    all_images = get_images()

    # 頭文字でフィルタリング
    if filter_char != 'all':
        images = [img for img in all_images if img[0].upper() == filter_char.upper()]
    else:
        images = all_images

    # 利用可能な頭文字を取得
    available_chars = sorted(set(img[0].upper() for img in all_images))
    char_counts = {char: sum(1 for img in all_images if img[0].upper() == char) for char in available_chars}

    return render_template('index.html',
                         images=images,
                         all_images_count=len(all_images),
                         filtered_count=len(images),
                         filter_char=filter_char,
                         available_chars=available_chars,
                         char_counts=char_counts)

@app.route('/api/images')
def api_images():
    """画像リストAPIエンドポイント"""
    images = get_images()
    return jsonify(images)

@app.route('/images/<filename>')
def serve_image(filename):
    """画像ファイルを配信"""
    return send_from_directory(SOURCE_DIR, filename)

@app.route('/api/all_images', methods=['GET'])
def all_images():
    """全画像リストを取得"""
    images = get_images()
    return jsonify(images)

@app.route('/api/move', methods=['POST'])
def move_images():
    """選択された画像を移動"""
    data = request.json
    selected = data.get('selected', [])
    unselected = data.get('unselected', [])

    # 今日の日付フォルダ（枝番付き）
    today = datetime.now().strftime('%Y%m%d')
    branch_num = 1
    while True:
        folder_name = f"{today}_{branch_num:02d}"
        selected_date_dir = os.path.join(SELECTED_DIR, folder_name)
        if not os.path.exists(selected_date_dir):
            break
        branch_num += 1

    # ディレクトリ作成
    os.makedirs(selected_date_dir, exist_ok=True)
    os.makedirs(UNSELECTED_DIR, exist_ok=True)

    results = {
        'selected_moved': [],
        'unselected_moved': [],
        'errors': []
    }

    # チェックされた画像を出品フォルダに移動
    for filename in selected:
        src = os.path.join(SOURCE_DIR, filename)
        dst = os.path.join(selected_date_dir, filename)

        try:
            if os.path.exists(src):
                shutil.move(src, dst)
                results['selected_moved'].append(filename)
            else:
                results['errors'].append(f"{filename} が見つかりません")
        except Exception as e:
            results['errors'].append(f"{filename}: {str(e)}")

    # チェックされなかった画像を予備保管フォルダに移動
    for filename in unselected:
        src = os.path.join(SOURCE_DIR, filename)
        dst = os.path.join(UNSELECTED_DIR, filename)

        try:
            if os.path.exists(src):
                shutil.move(src, dst)
                results['unselected_moved'].append(filename)
            else:
                results['errors'].append(f"{filename} が見つかりません")
        except Exception as e:
            results['errors'].append(f"{filename}: {str(e)}")

    return jsonify(results)

@app.route('/api/move_from_backup', methods=['POST'])
def move_from_backup():
    """予備保管フォルダから元画像フォルダへ全ファイルを移動"""
    if not os.path.exists(UNSELECTED_DIR):
        return jsonify({'error': '予備保管フォルダが見つかりません', 'moved': []})

    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
    moved_files = []
    errors = []

    for filename in os.listdir(UNSELECTED_DIR):
        ext = os.path.splitext(filename)[1].lower()
        if ext in image_extensions:
            src = os.path.join(UNSELECTED_DIR, filename)
            dst = os.path.join(SOURCE_DIR, filename)

            try:
                shutil.move(src, dst)
                moved_files.append(filename)
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")

    return jsonify({
        'moved': moved_files,
        'count': len(moved_files),
        'errors': errors
    })

@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    """サーバーをシャットダウン"""
    import signal
    os.kill(os.getpid(), signal.SIGINT)
    return jsonify({'status': 'shutting down'})

def open_browser():
    """ブラウザを自動で開く（一度だけ）"""
    global browser_opened
    if not browser_opened:
        browser_opened = True
        webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    # 1.5秒後にブラウザを開く
    Timer(1.5, open_browser).start()

    # デバッグモードをオフにして実行
    app.run(debug=False, port=5000, use_reloader=False)
