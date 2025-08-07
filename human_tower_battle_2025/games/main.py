import pygame
import os
import numpy as np
from animal import Animal
from game import create_space
from photo import capture_and_segment, capture_from_existing_camera
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor
from screens import StartScreen, GameOverScreen
from ranking import RankingManager
import cv2

# ウィンドウを外部モニターに配置（pygame.init()の前に設定）
# 外部モニターは1440×2489、メインディスプレイは1536×960
# 外部モニターが左側にある場合（負の座標を使用）
BASE_WIDTH, BASE_HEIGHT = 1440,2489
window_x = -1440 + 50  # 外部モニターの左端から50ピクセル（負の座標）
window_y = 50  # 上端から50ピクセル下
os.environ['SDL_VIDEO_WINDOW_POS'] = f"{window_x},{window_y}"



# 初期設定
pygame.init()

screen = pygame.display.set_mode((BASE_WIDTH, BASE_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("動物タワーバトル物理版")

clock = pygame.time.Clock()



# Pymunkスペース作成 & 台の座標も取得（BASE_WIDTH, BASE_HEIGHTで固定）
space, platform_rect = create_space(BASE_WIDTH, BASE_HEIGHT)

# SAM2 セグメンテーションモデルの読み込み
config_path = "../sam2/configs/sam2.1/sam2.1_hiera_l.yaml"
ckpt_path = "../sam2/checkpoints/sam2.1_hiera_large.pt"
predictor = SAM2ImagePredictor(build_sam2(config_path, ckpt_path, device="cpu"))

# ゲーム状態の初期化
animal_ingame = []
current_animal = None
number = 0
running = True
game_state = "start"  # "start", "playing", "game_over"

# ランキングマネージャーの初期化
ranking_manager = RankingManager()

# 画面の初期化
start_screen = StartScreen(BASE_WIDTH, BASE_HEIGHT)
game_over_screen = None

# カメラプレビュー用の変数
camera_cap = None
preview_surface = None

# 初期ウィンドウサイズ
window_width, window_height = BASE_WIDTH, BASE_HEIGHT



# プリセット位置の矢印を描画する関数
def draw_preset_arrows(surface, platform_rect):
    """プリセット位置を示す矢印を描画"""
    # 矢印の色とサイズ
    arrow_color = (255, 255, 0)  # 黄色
    arrow_size = 60  # 矢印サイズを大きく
    
    # 3つのプリセット位置
    positions = [
        (platform_rect["x1"] + 200, "1"),  # 左端（より中央に）
        ((platform_rect["x1"] + platform_rect["x2"]) // 2, "2"),  # 中央
        (platform_rect["x2"] - 200, "3")   # 右端（より中央に）
    ]
    
    for x, key_num in positions:
        # 矢印の位置（動物の上に表示）
        arrow_y = platform_rect["y"] - 250  # 動物の上に表示（少し上に）
        
        # 矢印を描画（下向きの三角形）
        arrow_points = [
            (x, arrow_y),
            (x - arrow_size//2, arrow_y + arrow_size),
            (x + arrow_size//2, arrow_y + arrow_size)
        ]
        pygame.draw.polygon(surface, arrow_color, arrow_points)
        
        # キー番号を表示（大きく）
        try:
            font = pygame.font.Font("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 48)
        except:
            try:
                font = pygame.font.Font("/System/Library/Fonts/Arial Unicode MS.ttf", 48)
            except:
                font = pygame.font.Font(None, 48)
        
        key_text = font.render(key_num, True, (255, 255, 255))
        key_rect = key_text.get_rect()
        key_rect.center = (x, arrow_y + arrow_size + 30)
        surface.blit(key_text, key_rect)
        
        # 矢印の枠線を描画（太く）
        pygame.draw.polygon(surface, (0, 0, 0), arrow_points, 4)

# ランキング表示関数
def draw_rankings(surface, ranking_manager):
    """ランキングを描画"""
    # 本日のランキングを取得
    daily_rankings = ranking_manager.get_daily_rankings()
    
    # フォント設定（大きなフォント）
    try:
        font = pygame.font.Font("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 64)  # フォントサイズを大きく
    except:
        try:
            font = pygame.font.Font("/System/Library/Fonts/Arial Unicode MS.ttf", 64)  # フォントサイズを大きく
        except:
            font = pygame.font.Font(None, 64)  # フォントサイズを大きく
    
    # プレビューカメラの位置を考慮してランキングを表示（左側に配置）
    # プレビューカメラは右上にあるので、左上にランキングを表示
    ranking_x = 80  # 右側に移動
    ranking_y = 50
    
    # 1位のみ表示
    if daily_rankings:
        top_score = daily_rankings[0]
        rank_text = f"今日の1位：{top_score['score']}人"
        rank_surface = font.render(rank_text, True, (255, 215, 0))  # 金色
        rank_rect = rank_surface.get_rect()
        rank_rect.topleft = (ranking_x, ranking_y)  # 1行で表示
        surface.blit(rank_surface, rank_rect)
    else:
        no_data_text = font.render("まだきろくがありません", True, (255, 215, 0))  # 金色
        no_data_rect = no_data_text.get_rect()
        no_data_rect.topleft = (ranking_x, ranking_y + 60)  # 間隔を広げる
        surface.blit(no_data_text, no_data_rect)

# カメラプレビューを初期化
def init_camera_preview():
    global camera_cap
    cameras_to_try = [1, 0, 2, 3]
    
    for camera_id in cameras_to_try:
        print(f"プレビュー用カメラ{camera_id}を試しています...")
        camera_cap = cv2.VideoCapture(camera_id)
        if camera_cap.isOpened():
            print(f"プレビュー用カメラ{camera_id}が使用可能です")
            camera_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            camera_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            camera_cap.set(cv2.CAP_PROP_FPS, 30)
            return True
        else:
            camera_cap.release()
            camera_cap = None
    
    print("プレビュー用カメラが見つかりませんでした")
    return False

# カメラプレビューを初期化
init_camera_preview()

# メインループ
while running:
    dt = 1 / 120.0  # 物理演算の精度を上げるためにタイムステップを小さく  

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.VIDEORESIZE:
            window_width, window_height = event.w, event.h
            screen = pygame.display.set_mode((window_width, window_height), pygame.RESIZABLE)
            
            # ウィンドウサイズが変更された時に重力を再計算
            # 新しい重力を計算（重力を下げる）
            base_width, base_height = 1440, 2489
            base_gravity = 1500
            gravity_scale = window_height / base_height
            gravity_y = base_gravity * gravity_scale
            space.gravity = (0, gravity_y)
            
            # 画面オブジェクトを新しいサイズで再作成
            start_screen = StartScreen(window_width, window_height)
            if game_over_screen:
                game_over_screen = GameOverScreen(window_width, window_height, number)
            
            print(f"ウィンドウサイズ変更: 重力加速度: (0, {gravity_y:.1f}) - ウィンドウサイズ: {window_width}x{window_height}")

        # ゲーム状態に応じてイベント処理
        if game_state == "start":
            if start_screen.handle_event(event):
                game_state = "playing"
                print("ゲーム開始！")
        elif game_state == "game_over":
            if game_over_screen:
                result = game_over_screen.handle_event(event)
                if result == "restart":
                    # ゲームをリセット
                    # 古い動物の物理オブジェクトを削除
                    for animal in animal_ingame:
                        animal.remove_from_space()
                    animal_ingame = []
                    current_animal = None
                    number = 0
                    game_over_screen = None  # ゲームオーバー画面をクリア
                    game_state = "playing"
                    print("ゲームをリスタートしました")
                elif result == "quit":
                    running = False
        elif game_state == "playing":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and (not current_animal or current_animal.falling):
                    # スペースキーで撮影して動物生成（既存のカメラから直接撮影）
                    # 動物が落ちていない時は撮影できない
                    rgb, mask = capture_from_existing_camera(camera_cap, predictor)
                    
                    # 現在の動物の最大高さを取得
                    max_y = 50  # デフォルトの高さ
                    if animal_ingame:
                        max_y = min([animal.body.position.y for animal in animal_ingame])
                        # 最大高さから800ピクセル上に配置（より上に移動）
                        spawn_y = max_y - 800
                    else:
                        # 最初の動物は台の上に配置（より上に移動）
                        spawn_y = platform_rect["y"] - 800
                    
                    current_animal = Animal(space, BASE_WIDTH // 2, spawn_y,
                                            rgb=rgb, mask=mask, scale=0.6)
                    print("A")
                    animal_ingame.append(current_animal)
                    number += 1

                elif event.key == pygame.K_d and current_animal and not current_animal.falling:
                    # Dキーで現在の動物を破棄
                    current_animal.remove_from_space()
                    animal_ingame.remove(current_animal)
                    current_animal = None
                    print("現在の動物を破棄しました")
                elif event.key == pygame.K_1 and current_animal and not current_animal.falling:
                    # 1キーで左端に配置
                    current_animal.body.position = (platform_rect["x1"] + 200, current_animal.body.position.y)
                    current_animal.start_fall()
                    print("左端に配置して落下開始")
                elif event.key == pygame.K_2 and current_animal and not current_animal.falling:
                    # 2キーで中央に配置
                    center_x = (platform_rect["x1"] + platform_rect["x2"]) // 2
                    current_animal.body.position = (center_x, current_animal.body.position.y)
                    current_animal.start_fall()
                    print("中央に配置して落下開始")
                elif event.key == pygame.K_3 and current_animal and not current_animal.falling:
                    # 3キーで右端に配置
                    current_animal.body.position = (platform_rect["x2"] - 200, current_animal.body.position.y)
                    current_animal.start_fall()
                    print("右端に配置して落下開始")

    # ゲーム状態に応じて画面を描画
    if game_state == "start":
        start_screen.draw(screen)
        pygame.display.flip()
        clock.tick(60)
        continue
    elif game_state == "game_over":
        if game_over_screen:
            game_over_screen.draw(screen)
            pygame.display.flip()
            clock.tick(60)
            continue
    elif game_state == "playing":
        # 仮描画サーフェス（BASEサイズ）
        base_surface = pygame.Surface((BASE_WIDTH, BASE_HEIGHT))

    # 背景画像を読み込んで表示
    try:
        background = pygame.image.load("Background.png")
        background = pygame.transform.scale(background, (BASE_WIDTH, BASE_HEIGHT))
        base_surface.blit(background, (0, 0))
    except:
        # 背景画像が見つからない場合は白で塗りつぶす
        base_surface.fill((255, 255, 255))

    # カメラプレビューを更新・表示
    if camera_cap and camera_cap.isOpened():
        ret, frame = camera_cap.read()
        if ret:
            # OpenCV画像（BGR）をRGBに変換
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # プレビューサイズを設定（画面の上部に表示）
            preview_width = 640
            preview_height = 480
            
            # フレームをリサイズ
            frame_resized = cv2.resize(frame_rgb, (preview_width, preview_height))
            
            # 画像を水平反転（鏡像にする）
            frame_resized = cv2.flip(frame_resized, 1)  # 1 = 水平反転
            
            # 中央に赤い点を描画
            center_x = preview_width // 2
            center_y = preview_height // 2
            cv2.circle(frame_resized, (center_x, center_y), 8, (255, 0, 0), -1)  # 赤い円を描画
            
            # numpy配列をPygameのSurfaceに変換
            preview_surface = pygame.surfarray.make_surface(frame_resized.swapaxes(0, 1))
            
            # プレビューを画面の右上に表示
            preview_x = BASE_WIDTH - preview_width - 30
            preview_y = 30
            base_surface.blit(preview_surface, (preview_x, preview_y))
            
            # プレビュー枠を描画
            pygame.draw.rect(base_surface, (255, 255, 255), 
                           (preview_x - 2, preview_y - 2, preview_width + 4, preview_height + 4), 2)
            
            # 撮影準備中の表示（macOS対応、大きなフォント）
            try:
                # macOS用の日本語フォント
                font = pygame.font.Font("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 32)
            except:
                try:
                    # 代替フォント
                    font = pygame.font.Font("/System/Library/Fonts/Arial Unicode MS.ttf", 32)
                except:
                    # デフォルトフォント
                    font = pygame.font.Font(None, 32)
            
            # テキスト表示を削除（playing中は何も表示しない）
        else:
            # カメラが利用できない場合のメッセージ（macOS対応、大きなフォント）
            try:
                # macOS用の日本語フォント
                font = pygame.font.Font("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 36)
            except:
                try:
                    # 代替フォント
                    font = pygame.font.Font("/System/Library/Fonts/Arial Unicode MS.ttf", 36)
                except:
                    # デフォルトフォント
                    font = pygame.font.Font(None, 36)
            text = font.render("カメラが利用できません", True, (255, 0, 0))
            text_rect = text.get_rect()
            text_rect.center = (BASE_WIDTH // 2, 50)
            base_surface.blit(text, text_rect)

    # 地面の線を描画
    pygame.draw.line(base_surface, (255, 0, 0), (0, BASE_HEIGHT - 10), (BASE_WIDTH, BASE_HEIGHT - 10), 5)

    # 台を描画
    pygame.draw.rect(
        base_surface,
        (100, 100, 100),
        pygame.Rect(
            platform_rect["x1"],
            platform_rect["y"] - 25,  # platform_height/2 = 50/2 = 25
            platform_rect["x2"] - platform_rect["x1"],
            50  # platform_heightに合わせる
        )
    )

    # 動物を描画（base_surface に対して）
    for animal in animal_ingame:
        animal.draw(base_surface)

    # プリセット位置の矢印を描画（現在の動物が存在し、落下していない場合のみ）
    if current_animal and not current_animal.falling:
        draw_preset_arrows(base_surface, platform_rect)

    # ランキング表示
    draw_rankings(base_surface, ranking_manager)

    # base_surface をスケーリングして画面に描画
    scaled_surface = pygame.transform.scale(base_surface, (window_width, window_height))
    screen.blit(scaled_surface, (0, 0))
    pygame.display.flip()

    # 物理演算の更新（滑らかな動きのため複数回ステップ実行）
    for _ in range(2):  # 物理演算を2回実行して滑らかさを向上
        space.step(dt)

    # ゲームオーバー判定
    for animal in animal_ingame:
        x, y = animal.body.position
        # 床に落ちた場合（動物の下部が床に触れた場合）
        animal_bottom = y + 50  # 動物の下部位置（概算）
        if animal_bottom > BASE_HEIGHT - 10:  # 床の位置（BASE_HEIGHT - 10）
            print("GAME OVER! 床に落ちました！")
            # 落とした数-1を表示するため、numberを1減らす
            number = max(0, number - 1)
            game_state = "game_over"
            game_over_screen = GameOverScreen(window_width, window_height, number, ranking_manager)
            break

    # フレームレートを安定化（滑らかな動きのため）
    clock.tick(120)  # フレームレートを120FPSに上げて滑らかさを向上
info = pygame.display.Info()

# カメラをリリース
if camera_cap:
    camera_cap.release()

pygame.quit()

