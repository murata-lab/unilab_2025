import pygame
import random
import math
import time
import threading
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
from brainflow.data_filter import DataFilter, FilterTypes, DetrendOperations
import requests
import json

current_ratio = 0
stop_flag = False

class measure():
    def __init__(self) -> None:
        pass
    
    def calcurate():
        global current_ratio, stop_flag
        
        # OpenBCI Ganglionボードの設定
        params = BrainFlowInputParams()
        params.serial_port = 'COM3'  # シリアルポートを指定

        # ボードIDを指定してセッションを準備
        board = BoardShim(BoardIds.GANGLION_BOARD, params)
        board.prepare_session()
        print("Session Prepared")

        # サンプリングレートを取得
        sampling_rate = BoardShim.get_sampling_rate(BoardIds.GANGLION_BOARD)   # sampling_late = 200

        # EEGチャネルを取得
        eeg_channels = BoardShim.get_eeg_channels(BoardIds.GANGLION_BOARD)

        # リアルタイムプロットのセットアップ
        fig, ax = plt.subplots(3, 1, sharex=True)
        xdata, alpha_ydata, beta_ydata, ratio_ydata = [], [], [], []
        alpha_ln, = ax[0].plot([], [], 'b-', animated=True, label='Alpha')
        beta_ln, = ax[1].plot([], [], 'r-', animated=True, label='Beta')
        ratio_ln, = ax[2].plot([], [], 'g-', animated=True, label='ratio')

        window_size = 5  # 移動平均のウィンドウサイズ

        # エネルギーとその比率を表示するテキスト要素
        alpha_energy_text = ax[0].text(0.02, 0.95, '', transform=ax[0].transAxes)
        beta_energy_text = ax[1].text(0.02, 0.95, '', transform=ax[1].transAxes)
        ratio_text = ax[2].text(0.02, 0.95, '', transform=ax[2].transAxes)

        def moving_average(data, window_size):
            return np.convolve(data, np.ones(window_size) / window_size, mode='valid')

        def hard_threshold(data, threshold):
            return np.where(np.abs(data) > threshold, 0, data)

        def calculate_energy(data):
            return np.mean(data ** 2)

        def init():
            for a in ax:
                a.set_xlim(0, 50)  # 50秒間のデータを表示
                if a==ax[0] or a==ax[1]:
                    a.set_ylim(-100, 100)  # α波とβ波の値の範囲を設定
                else:
                    a.set_ylim(0, 5)  # 比率の値の範囲を設定
                a.legend(loc='upper right')  
            return alpha_ln, beta_ln, alpha_energy_text, beta_energy_text, ratio_text

        def update(frame):
            global current_ratio
            data = board.get_current_board_data(sampling_rate)  # 最新のデータを取得
            alpha_data, beta_data = [], []
            
            for channel in eeg_channels[:3]:  # 3チャネルのみを使用
                DataFilter.detrend(data[channel], DetrendOperations.LINEAR.value)
                
                # アルファ波の抽出
                alpha_channel_data = data[channel].copy()
                DataFilter.perform_bandpass(alpha_channel_data, sampling_rate, 8.0, 13.0, 2, FilterTypes.BUTTERWORTH_ZERO_PHASE.value, 0)
                alpha_channel_data = hard_threshold(alpha_channel_data, 150)
                alpha_data.append(alpha_channel_data)
                
                # ベータ波の抽出
                beta_channel_data = data[channel].copy()
                DataFilter.perform_bandpass(beta_channel_data, sampling_rate, 13.0, 30.0, 2, FilterTypes.BUTTERWORTH_ZERO_PHASE.value, 0)
                beta_channel_data = hard_threshold(beta_channel_data, 150)
                beta_data.append(beta_channel_data)
                
            alpha_mean = np.mean(alpha_data, axis=0)
            beta_mean = np.mean(beta_data, axis=0)
            
            # エネルギーの計算
            alpha_energy = calculate_energy(alpha_mean)
            beta_energy = calculate_energy(beta_mean)
            ratio = 2*beta_energy / alpha_energy if alpha_energy != 0 else 0
            current_ratio =  ratio
            
            # テキスト要素の更新
            alpha_energy_text.set_text(f'Alpha Energy: {alpha_energy:.2f} µV²')
            beta_energy_text.set_text(f'Beta Energy: {beta_energy:.2f} µV²')
            ratio_text.set_text(f'Beta/Alpha Ratio: {ratio:.2f}')
            
            current_time = time.time() % 50  # 時間を100秒間隔でループ
            
            xdata.append(current_time)
            alpha_ydata.append(alpha_mean[0])
            beta_ydata.append(beta_mean[0])
            ratio_ydata.append(ratio)
            
            if len(xdata) > 1 and xdata[-1] < xdata[-2]:  # 100秒を超えた場合
                xdata.clear()
                alpha_ydata.clear()
                beta_ydata.clear()
                ratio_ydata.clear()
                xdata.append(current_time)
                alpha_ydata.append(alpha_mean[0])
                beta_ydata.append(beta_mean[0])
                ratio_ydata.append(ratio)
                
            if len(alpha_ydata) > window_size:
                smoothed_alpha_ydata = moving_average(alpha_ydata, window_size)
                smoothed_beta_ydata = moving_average(beta_ydata, window_size)
                smoothed_ratio_ydata = moving_average(ratio_ydata, window_size)
                
                alpha_ln.set_data(xdata[-len(smoothed_alpha_ydata):], smoothed_alpha_ydata)
                beta_ln.set_data(xdata[-len(smoothed_beta_ydata):], smoothed_beta_ydata)
                ratio_ln.set_data(xdata[-len(smoothed_ratio_ydata):], smoothed_ratio_ydata)
            else:
                alpha_ln.set_data(xdata, alpha_ydata)
                beta_ln.set_data(xdata, beta_ydata)
                ratio_ln.set_data(xdata, ratio_ydata)
                
            return alpha_ln, beta_ln, ratio_ln, alpha_energy_text, beta_energy_text, ratio_text
        # リアルタイムプロットのアニメーション
        ani = FuncAnimation(fig, update, init_func=init, blit=True, interval=30)  # 30ミリ秒ごとに更新

        # ボードからストリーミングを開始
        board.start_stream()
        print("Streaming started")

        # プロットを表示
        plt.show()

        # ストリーミングを停止してセッションを終了
        board.stop_stream()
        board.release_session()

graph = measure
ratio_thread  =threading.Thread(target=graph.calcurate)
ratio_thread.start()

time.sleep(5)

# 初期設定
pygame.init()
pygame.mixer.init()  # 音声機能を初期化

# WIDTH, HEIGHT = 800, 600
# screen = pygame.display.set_mode((WIDTH, HEIGHT))
# pygame.display.set_caption("弓矢の的あてゲーム")
# フルスクリーン
pygame.display.set_caption("弓矢の的あてゲーム")
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)

# 音声ファイルの読み込み
try:
    bgm = pygame.mixer.Sound("background.mp3")
    shoot_sound = pygame.mixer.Sound("arrow_shoot.mp3")
    hit_sound = pygame.mixer.Sound("arrow_hit.mp3")
    # BGMをループ再生
    bgm.set_volume(0.5)  # BGMの音量を50%に設定
    bgm.play(-1)  # -1でループ再生
except:
    print("音声ファイルが見つかりません。音声なしで実行します。")
    bgm = None
    shoot_sound = None
    hit_sound = None

# 色設定
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)

# フォント設定
font = pygame.font.Font("azukiLB.ttf", 70)
large_font = pygame.font.Font("azukiLB.ttf", 110)

# 画像読み込み
title_image = pygame.image.load("title.png")
title_image = pygame.transform.scale(title_image, (WIDTH, HEIGHT))
background_image = pygame.image.load("background.png")
background_image = pygame.transform.scale(background_image, (WIDTH, HEIGHT))
canvas_image = pygame.image.load("canvas.png")

# canvas_imageのサイズ設定（画面幅と高さの比率で設定）
CANVAS_WIDTH_RATIO = 0.6
CANVAS_HEIGHT_RATIO = 0.4
CANVAS_WIDTH = int(WIDTH * CANVAS_WIDTH_RATIO)
CANVAS_HEIGHT = int(HEIGHT * CANVAS_HEIGHT_RATIO)
canvas_image = pygame.transform.scale(canvas_image, (CANVAS_WIDTH, CANVAS_HEIGHT))
result_image = pygame.image.load("result.png")
result_image = pygame.transform.scale(result_image, (WIDTH, HEIGHT))

# canvas_imageの位置設定（画面中央）
canvas_rect = canvas_image.get_rect(center=(WIDTH // 2, HEIGHT))


# 的の設定
TARGET_WIDTH_RATIO = 0.5

# 的のサイズを画面の比率に基づいて設定
target_width = int(WIDTH * TARGET_WIDTH_RATIO)
target_image = pygame.image.load("target.png")
target_image = pygame.transform.scale(target_image, (target_width, target_width))

# 的のサイズ調整関数
def get_target_size():
    if game_mode == "Hard":
        return int(WIDTH * TARGET_WIDTH_RATIO * 0.7)  # ハードモードでは的を小さく
    else:
        return int(WIDTH * TARGET_WIDTH_RATIO)

speed_images = [
    pygame.image.load("speed_1.png"),
    pygame.image.load("speed_2.png"),
    pygame.image.load("speed_3.png")
]
speed_images = [pygame.transform.scale(img, (WIDTH, HEIGHT)) for img in speed_images]
arrow_image_1 = pygame.image.load("arrow_1.png")
arrow_image_2 = pygame.image.load("arrow_2.png")

# 矢のパラメータ（画面サイズに対する比率で指定）
ARROW_WIDTH_RATIO = 0.5
ARROW_HEIGHT_RATIO = 0.5
ARROW_ANGLE = 45  # 矢の回転角度（度数法）

# 矢の画像を調整する関数
def adjust_arrow(width_ratio, height_ratio, angle):
    global arrow_image_1, arrow_image_2, ARROW_WIDTH, ARROW_HEIGHT
    ARROW_WIDTH = int(WIDTH * width_ratio)
    ARROW_HEIGHT = int(HEIGHT * height_ratio)
    arrow_image_1 = pygame.image.load("arrow_1.png")
    arrow_image_1 = pygame.transform.scale(arrow_image_1, (ARROW_WIDTH, ARROW_HEIGHT))
    arrow_image_1 = pygame.transform.rotate(arrow_image_1, angle)
    arrow_image_2 = pygame.image.load("arrow_2.png")
    arrow_image_2 = pygame.transform.scale(arrow_image_2, (ARROW_WIDTH, ARROW_HEIGHT))
    arrow_image_2 = pygame.transform.rotate(arrow_image_2, 48)

# 初期の矢の調整
adjust_arrow(ARROW_WIDTH_RATIO, ARROW_HEIGHT_RATIO, ARROW_ANGLE)

# 的の設定
target_rect = target_image.get_rect(center=(WIDTH // 2, HEIGHT // 2))
target_radius = target_rect.width // 2

# 的の更新
def update_target_size():
    global target_rect, target_radius
    target_size = get_target_size()
    target_rect = pygame.Rect(WIDTH // 2 - target_size // 2, HEIGHT // 2 - target_size // 2, target_size, target_size)
    target_radius = target_size // 2

# 得点範囲の半径
r = target_radius
score_ranges = {
    10: 0.86 * r / 5,
    7: 1.9 * r / 5,
    5: 2.95 * r / 5,
    3: 3.96 * r / 5,
    1: r
}

# 得点範囲の更新
def update_score_ranges():
    global score_ranges
    current_target_size = get_target_size()
    current_radius = current_target_size // 2
    score_ranges = {
        10: 0.86 * current_radius / 5,
        7: 1.9 * current_radius / 5,
        5: 2.95 * current_radius / 5,
        3: 3.96 * current_radius / 5,
        1: current_radius
    }

# ゲーム状態
initial_aim_radius = 800
aim_radius = initial_aim_radius
aim_shrink_rate = 3.5
initial_min = 100
score = 0
hit_pos = None
game_over = False
animation_running = False
animation_start_time = 0
ANIMATION_DURATION = 2500  # 3秒間
FADE_OUT_DURATION = 500  # フェードアウトの時間（ミリ秒）
SPEED_IMAGE_DURATION = 100  # 各速度画像の表示時間（ミリ秒）

# 照準の揺れに関する変数
initial_sway_radius = 50
aim_center_x, aim_center_y = target_rect.center
aim_target_x, aim_target_y = target_rect.center
sway_speed = 2



# ゲーム状態の定数を追加
START_SCREEN = 0
NAME_INPUT = 1
MODE_SELECT = 2
PLAYING = 3
RESULT_SCREEN = 4
FINAL_RESULT_SCREEN = 5

# グローバル変数を追加
game_state = START_SCREEN
game_count = 0
total_score = 0
scores = []
game_start_time = 0  # ゲーム開始時刻
AUTO_SHOOT_TIME = 20000  # 自動発射までの時間（ミリ秒）

# カウントダウン関連の変数
countdown_active = False
countdown_start_time = 0
COUNTDOWN_DURATION = 3000  # カウントダウンの時間（ミリ秒）
COUNTDOWN_TOTAL = 3000  # カウントダウンの総時間（ミリ秒）

# ゲームモード関連の変数
game_mode = "Normal"
selected_mode = 0  # 0: Normal, 1: Hard

# プレイヤー名関連の変数
player_name = "名無し"
name_input_active = False
name_input_text = ""
name_input_cursor = 0



def calculate_score(hit_pos):
    distance = math.hypot(hit_pos[0] - target_rect.centerx, hit_pos[1] - target_rect.centery)
    for points, radius in score_ranges.items():
        if distance <= radius:
            return points
    return 0

def get_random_point_in_circle(center, radius):
    angle = random.uniform(0, 2 * math.pi)
    r = radius * math.sqrt(random.uniform(0, 1))
    x = center[0] + r * math.cos(angle)
    y = center[1] + r * math.sin(angle)
    
    # ハードモードでは風の影響を追加
    if game_mode == "Hard":
        wind_x = random.uniform(-20, 20)
        wind_y = random.uniform(-20, 20)
        x += wind_x
        y += wind_y
    
    return (int(x), int(y))

def update_aim_position(initial_sway_radius):
    global aim_center_x, aim_center_y, aim_target_x, aim_target_y, current_ratio
    
    sway_radius = initial_sway_radius + 50 * current_ratio
    current_sway_speed = sway_speed
    
    # ハードモードでは揺れを強くする
    if game_mode == "Hard":
        sway_radius += 30 * current_ratio
        current_sway_speed += 1
    
    if math.hypot(aim_center_x - aim_target_x, aim_center_y - aim_target_y) < 1:
        aim_target_x, aim_target_y = get_random_point_in_circle(target_rect.center, sway_radius)
    
    dx = aim_target_x - aim_center_x
    dy = aim_target_y - aim_center_y
    distance = math.hypot(dx, dy)
    
    if distance > 0:
        aim_center_x += (dx / distance) * current_sway_speed
        aim_center_y += (dy / distance) * current_sway_speed

def draw_arrow_animation(progress):
    if progress < (ANIMATION_DURATION - FADE_OUT_DURATION) / ANIMATION_DURATION:
        # 通常のアニメーション
        alpha = 255
        # 速度画像のローテーション
        speed_image_index = int((progress * ANIMATION_DURATION) / SPEED_IMAGE_DURATION) % len(speed_images)
        speed_image = speed_images[speed_image_index]
    else:
        # フェードアウト
        fade_progress = (progress * ANIMATION_DURATION - (ANIMATION_DURATION - FADE_OUT_DURATION)) / FADE_OUT_DURATION
        alpha = int(255 * (1 - fade_progress))
        speed_image = speed_images[-1]  # フェードアウト中は最後の画像を使用

    # speed_imageのアルファ値を変更
    speed_image_copy = speed_image.copy()
    speed_image_copy.set_alpha(alpha)
    screen.blit(speed_image_copy, (0, 0))
    
    # 矢のアルファ値を変更
    if progress < 0.5:
        arrow_copy = arrow_image_1.copy()
    else:
        arrow_copy = arrow_image_2.copy()
    arrow_copy.set_alpha(alpha)
    
    # 矢を中央に配置
    arrow_x = WIDTH // 2 - arrow_copy.get_width() // 2
    arrow_y = HEIGHT // 2 - arrow_copy.get_height() // 2
    screen.blit(arrow_copy, (arrow_x, arrow_y))

    # 背景を徐々に白くする
    white_overlay = pygame.Surface((WIDTH, HEIGHT))
    white_overlay.fill(WHITE)
    white_overlay.set_alpha(255 - alpha)
    screen.blit(white_overlay, (0, 0))

def draw_start_screen():
    screen.blit(title_image, (0, 0))

def draw_countdown():
    current_time = pygame.time.get_ticks()
    elapsed = current_time - countdown_start_time
    
    if elapsed >= COUNTDOWN_TOTAL:
        global countdown_active
        countdown_active = False
        return
    
    # カウントダウンの表示
    remaining = COUNTDOWN_TOTAL - elapsed
    if remaining > 2000:
        count_text = "3"
    elif remaining > 1000:
        count_text = "2"
    else:
        count_text = "1"
    
    count_surface = large_font.render(count_text, True, BLACK)
    count_rect = count_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(count_surface, count_rect)

def draw_name_input_screen():
    screen.fill(WHITE)
    title_text = font.render("プレイヤー名を入力してください", True, BLACK)
    title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100))
    screen.blit(title_text, title_rect)
    
    # 名前入力欄の表示
    name_text = font.render(player_name, True, BLUE)
    name_rect = name_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(name_text, name_rect)
    
    instruction_text = font.render("Enterキーを押して決定", True, BLACK)
    instruction_rect = instruction_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 100))
    screen.blit(instruction_text, instruction_rect)

def draw_mode_select_screen():
    screen.fill(WHITE)
    title_text = large_font.render("モード選択", True, BLACK)
    title_rect = title_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 150))
    screen.blit(title_text, title_rect)
    
    # モード選択の表示
    modes = ["Normal", "Hard"]
    for i, mode in enumerate(modes):
        color = RED if i == selected_mode else BLACK
        mode_text = font.render(mode, True, color)
        mode_rect = mode_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50 + i * 80))
        screen.blit(mode_text, mode_rect)
    
    instruction_text = font.render("上下キーで選択、スペースキーで決定", True, BLACK)
    instruction_rect = instruction_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 150))
    screen.blit(instruction_text, instruction_rect)



def draw_result_screen():
    screen.blit(result_image, (0, 0))
    score_text = font.render(f'得点: {score}点', True, BLACK)
    screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 2))
    instruction_text = font.render('スペースキーを押して再開', True, BLACK)
    screen.blit(instruction_text, (WIDTH // 2 - instruction_text.get_width() // 2, HEIGHT // 2 + 50))

# メインループ内で使用する関数を追加
def reset_game():
    global aim_radius, score, game_over, animation_running, game_start_time, countdown_active, countdown_start_time
    aim_radius = initial_aim_radius
    score = 0
    game_over = False
    animation_running = False
    countdown_active = True
    countdown_start_time = pygame.time.get_ticks()  # カウントダウン開始時刻を記録
    game_start_time = countdown_start_time + COUNTDOWN_TOTAL  # ゲーム開始時刻をカウントダウン後に設定
    
    # 得点範囲の更新
    update_score_ranges()

def draw_final_result_screen():
    screen.blit(result_image, (0, 0))
    total_score_text = large_font.render(f'合計得点: {total_score}点', True, BLACK)
    screen.blit(total_score_text, (WIDTH // 2 - total_score_text.get_width() // 2, HEIGHT // 2 - 230))
    for i, score in enumerate(scores):
        score_text = large_font.render(f'{i+1}回目: {score}点', True, BLACK)
        screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 2 - 120 + i*90))
    instruction_text = font.render('Rキーでランキングに送信、スペースキーでスタート画面に戻る', True, BLACK)
    screen.blit(instruction_text, (WIDTH // 2 - instruction_text.get_width() // 2, HEIGHT - 100))

def submit_score_to_server():
    try:
        data = {
            'player_name': player_name,
            'total_score': total_score,
            'game_mode': game_mode,
            'scores': scores
        }
        print(f"送信データ: {data}")
        response = requests.post('http://localhost:5000/submit_score', json=data, timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("スコアをサーバーに送信しました")
            else:
                print(f"スコアの送信に失敗しました: {result.get('message')}")
        else:
            print(f"スコアの送信に失敗しました: HTTP {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("Webサーバーに接続できません。サーバーが起動しているか確認してください。")
    except Exception as e:
        print(f"サーバーとの通信エラー: {e}")



clock = pygame.time.Clock()

while True:
    current_time = pygame.time.get_ticks()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
        elif event.type == pygame.TEXTINPUT:
            if game_state == NAME_INPUT:
                player_name += event.text
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if game_state == START_SCREEN:
                    game_state = NAME_INPUT
                    pygame.key.start_text_input()
                elif game_state == MODE_SELECT:
                    pygame.key.stop_text_input()
                    game_mode = "Normal" if selected_mode == 0 else "Hard"
                    game_state = PLAYING
                    reset_game()
                elif game_state == PLAYING and not game_over and not animation_running and not countdown_active:
                    hit_pos = get_random_point_in_circle((aim_center_x, aim_center_y), aim_radius)
                    score = calculate_score(hit_pos)
                    animation_running = True
                    animation_start_time = current_time
                    # 矢を打った時の効果音を再生
                    if shoot_sound:
                        shoot_sound.play()
                elif game_state == PLAYING and game_over:
                    game_count += 1
                    scores.append(score)
                    total_score += score
                    if game_count < 3:
                        game_state = PLAYING
                        reset_game()
                    else:
                        game_state = FINAL_RESULT_SCREEN
                elif game_state == FINAL_RESULT_SCREEN:
                    # スタート画面に戻る
                    game_state = START_SCREEN
                    game_count = 0
                    total_score = 0
                    scores = []
            elif event.key == pygame.K_RETURN:
                if game_state == NAME_INPUT:
                    pygame.key.stop_text_input()
                    game_state = MODE_SELECT
            elif event.key == pygame.K_BACKSPACE:
                if game_state == NAME_INPUT and len(player_name) > 0:
                    player_name = player_name[:-1]
            elif event.key == pygame.K_UP:
                if game_state == MODE_SELECT:
                    selected_mode = (selected_mode - 1) % 2
            elif event.key == pygame.K_DOWN:
                if game_state == MODE_SELECT:
                    selected_mode = (selected_mode + 1) % 2
            elif event.key == pygame.K_r:
                if game_state == FINAL_RESULT_SCREEN:
                    submit_score_to_server()

    screen.fill(WHITE)

    if game_state == START_SCREEN:
        draw_start_screen()
    elif game_state == NAME_INPUT:
        draw_name_input_screen()
    elif game_state == MODE_SELECT:
        draw_mode_select_screen()
    elif game_state == PLAYING:
        screen.fill(WHITE)
        screen.blit(background_image, (0, 0))
        # カウントダウン中でない場合のみcanvas_imageを表示
        if not countdown_active:
            screen.blit(canvas_image, canvas_rect.topleft)

        # remaining_timeを常に計算
        if not game_over and not animation_running:
            elapsed_time = current_time - game_start_time
            remaining_time = max(0, AUTO_SHOOT_TIME - elapsed_time)
        
        # カウントダウンの処理
        if countdown_active:
            draw_countdown()
        else:
            # 10秒タイマーの処理
            if not game_over and not animation_running:
                # 10秒経過したら自動発射
                if remaining_time <= 0 and not animation_running:
                    hit_pos = get_random_point_in_circle((aim_center_x, aim_center_y), aim_radius)
                    score = calculate_score(hit_pos)
                    animation_running = True
                    animation_start_time = current_time
                    # 矢を打った時の効果音を再生
                    if shoot_sound:
                        shoot_sound.play()

        if animation_running:
            animation_progress = (current_time - animation_start_time) / ANIMATION_DURATION
            if animation_progress >= 1:
                animation_running = False
                game_over = True
                # 矢が的に刺さった時の効果音を再生
                if hit_sound:
                    hit_sound.play()
            else:
                draw_arrow_animation(animation_progress)
        else:
            # カウントダウン中でない場合のみ的と照準を表示
            if not countdown_active:
                # 的の描画
                target_size = get_target_size()
                scaled_target = pygame.transform.scale(target_image, (target_size, target_size))
                target_rect = scaled_target.get_rect(center=(WIDTH // 2, HEIGHT // 2))
                screen.blit(scaled_target, target_rect)

                # 照準の位置更新と描画
                if aim_radius > 0 and not game_over:
                    update_aim_position(initial_sway_radius)
                    pygame.draw.circle(screen, BLACK, (int(aim_center_x), int(aim_center_y)), int(aim_radius), 5)
                    print(current_ratio)

            # 当たった点の描画
            if hit_pos and game_over:
                pygame.draw.circle(screen, BLUE, hit_pos, 10)
                # スコアをヒット位置の上に表示する関数
                score_text = font.render(f'得点: {score}点', True, BLUE)
                score_rect = score_text.get_rect(center=(WIDTH // 2, 30))
                screen.blit(score_text, score_rect)
            
            else:
                # カウントダウン中でない場合のみスコアとタイマーを表示
                if not countdown_active:
                    # スコアの表示
                    score_text = font.render('集中して的を狙おう！', True, BLUE)
                    score_text_rect = score_text.get_rect(center=(WIDTH // 2, 30))  # 画面の中央上側に位置
                    screen.blit(score_text, score_text_rect)
                    
                    # タイマーの表示
                    if not game_over and not animation_running:
                        timer_text = font.render(f'残り時間: {remaining_time // 1000}.{(remaining_time % 1000) // 100}秒', True, RED)
                        timer_rect = timer_text.get_rect(center=(WIDTH // 2, 80))
                        screen.blit(timer_text, timer_rect)
                    


            min_aim_radius = initial_min + 130 * current_ratio

            # 照準の縮小（最小サイズの制限付き）
            if aim_radius > min_aim_radius and not game_over and not countdown_active:
                aim_radius = max(aim_radius - aim_shrink_rate, min_aim_radius)
            
            # 標準の拡大
            if aim_radius < min_aim_radius and not game_over and not countdown_active:
                aim_radius = max(aim_radius , min_aim_radius + aim_shrink_rate)

            if game_over:
                instruction_text = font.render('スペースキーを押して再開', True, BLACK)
                screen.blit(instruction_text, (WIDTH // 2 - instruction_text.get_width() // 2, HEIGHT - 50))
    elif game_state == RESULT_SCREEN:
        draw_result_screen()
    elif game_state == FINAL_RESULT_SCREEN:
        draw_final_result_screen()
    pygame.display.flip()
    clock.tick(60)  # 60FPSに制限

ratio_thread.join()