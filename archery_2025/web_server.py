from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

# ランキングデータを保存するファイル
RANKING_FILE = 'ranking.json'

def load_ranking():
    """ランキングデータを読み込む"""
    if os.path.exists(RANKING_FILE):
        with open(RANKING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_ranking(ranking_data):
    """ランキングデータを保存する"""
    with open(RANKING_FILE, 'w', encoding='utf-8') as f:
        json.dump(ranking_data, f, ensure_ascii=False, indent=2)

def add_score(player_name, total_score, game_mode, scores):
    """新しいスコアをランキングに追加"""
    ranking = load_ranking()
    
    # game_modeが文字列の場合はそのまま使用、数値の場合は変換
    if isinstance(game_mode, str):
        mode_display = 'むずかしい' if game_mode == 'Hard' else 'ふつう'
    else:
        mode_display = 'むずかしい' if game_mode == 1 else 'ふつう'
    
    new_score = {
        'player_name': player_name,
        'total_score': total_score,
        'game_mode': mode_display,
        'scores': scores,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    ranking.append(new_score)
    
    # スコアでソート（降順）
    ranking.sort(key=lambda x: x['total_score'], reverse=True)
    
    # 上位100件のみ保持
    ranking = ranking[:100]
    
    save_ranking(ranking)
    return ranking

@app.route('/')
def index():
    """メインページ"""
    ranking = load_ranking()
    return render_template('index.html', ranking=ranking)

@app.route('/submit_score', methods=['POST'])
def submit_score():
    """スコアを送信するAPI"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'データがありません'}), 400
        
        player_name = data.get('player_name', '名無し')
        total_score = data.get('total_score', 0)
        game_mode = data.get('game_mode', 'Normal')
        scores = data.get('scores', [])
        
        ranking = add_score(player_name, total_score, game_mode, scores)
        
        return jsonify({
            'success': True,
            'message': 'スコアが登録されました！',
            'ranking': ranking[:10]  # 上位10件を返す
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'エラーが発生しました: {str(e)}'}), 500

@app.route('/ranking')
def ranking_api():
    """ランキングデータを取得するAPI"""
    ranking = load_ranking()
    return jsonify(ranking)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False) 