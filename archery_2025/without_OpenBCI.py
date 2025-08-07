import pygame
import random
import math

# 初期設定
pygame.init()
WIDTH, HEIGHT = 1000, 750
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("弓矢の的あてゲーム")
# フルスクリーン
# info = pygame.display.Info()
# WIDTH, HEIGHT = info.current_w, info.current_h
# screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
# pygame.display.set_caption("弓矢の的あてゲーム")

# 色設定
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)

# フォント設定
font = pygame.font.SysFont(None, 36)
title_font = pygame.font.SysFont(None, 72)

# 画像読み込み
title_image = pygame.image.load("title.png")
title_image = pygame.transform.scale(title_image, (WIDTH, HEIGHT))
background_image = pygame.image.load("background.png")
background_image = pygame.transform.scale(background_image, (WIDTH, HEIGHT))
canvas_image = pygame.image.load("canvas.png")

# canvas_imageのサイズ設定（画面幅と高さの比率で設定）
CANVAS_WIDTH_RATIO = 0.25
CANVAS_HEIGHT_RATIO = 0.2
CANVAS_WIDTH = int(WIDTH * CANVAS_WIDTH_RATIO)
CANVAS_HEIGHT = int(HEIGHT * CANVAS_HEIGHT_RATIO)
canvas_image = pygame.transform.scale(canvas_image, (CANVAS_WIDTH, CANVAS_HEIGHT))

# canvas_imageの位置設定（画面中央）
canvas_rect = canvas_image.get_rect(center=(WIDTH // 2, 3 * HEIGHT // 4))

target_image = pygame.image.load("target.png")
target_image = pygame.transform.scale(target_image, (250, 250))
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

# 得点範囲の半径
r = target_radius
score_ranges = {
    10: 0.86 * r / 5,
    7: 1.9 * r / 5,
    5: 2.95 * r / 5,
    3: 3.96 * r / 5,
    1: r
}

# ゲーム状態
initial_aim_radius = 250
aim_radius = initial_aim_radius
aim_shrink_rate = 0.5
min_aim_radius = 50
score = 0
hit_pos = None
game_over = False
animation_running = False
animation_start_time = 0
ANIMATION_DURATION = 3000  # 3秒間
FADE_OUT_DURATION = 500  # フェードアウトの時間（ミリ秒）
SPEED_IMAGE_DURATION = 100  # 各速度画像の表示時間（ミリ秒）

# 照準の揺れに関する変数
sway_radius = 30
aim_center_x, aim_center_y = target_rect.center
aim_target_x, aim_target_y = target_rect.center
sway_speed = 2

# ゲーム状態
START_SCREEN = 0
PLAYING = 1
game_state = START_SCREEN

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
    return (int(x), int(y))

def update_aim_position():
    global aim_center_x, aim_center_y, aim_target_x, aim_target_y
    
    if math.hypot(aim_center_x - aim_target_x, aim_center_y - aim_target_y) < 1:
        aim_target_x, aim_target_y = get_random_point_in_circle(target_rect.center, sway_radius)
    
    dx = aim_target_x - aim_center_x
    dy = aim_target_y - aim_center_y
    distance = math.hypot(dx, dy)
    
    if distance > 0:
        aim_center_x += (dx / distance) * sway_speed
        aim_center_y += (dy / distance) * sway_speed

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

clock = pygame.time.Clock()

while True:
    current_time = pygame.time.get_ticks()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if game_state == START_SCREEN:
                    game_state = PLAYING
                    aim_radius = initial_aim_radius
                    score = 0
                    game_over = False
                elif game_state == PLAYING and not game_over and not animation_running:
                    hit_pos = get_random_point_in_circle((aim_center_x, aim_center_y), aim_radius)
                    score = calculate_score(hit_pos)
                    animation_running = True
                    animation_start_time = current_time

    if game_state == START_SCREEN:
        draw_start_screen()
    elif game_state == PLAYING:
        screen.fill(WHITE)
        screen.blit(background_image, (0, 0))
        screen.blit(canvas_image, canvas_rect.topleft)

        if animation_running:
            animation_progress = (current_time - animation_start_time) / ANIMATION_DURATION
            if animation_progress >= 1:
                animation_running = False
                game_over = True
            else:
                draw_arrow_animation(animation_progress)
        else:
            # 的の描画
            screen.blit(target_image, target_rect)

            # 照準の位置更新と描画
            if aim_radius > 0 and not game_over:
                update_aim_position()
                pygame.draw.circle(screen, BLACK, (int(aim_center_x), int(aim_center_y)), int(aim_radius), 2)

            # 当たった点の描画
            if hit_pos and game_over:
                pygame.draw.circle(screen, BLUE, hit_pos, 5)

            # スコアの表示
            score_text = font.render(f'Score: {score}', True, BLACK)
            screen.blit(score_text, (10, 10))

            # 照準の縮小（最小サイズの制限付き）
            if aim_radius > min_aim_radius and not game_over:
                aim_radius = max(aim_radius - aim_shrink_rate, min_aim_radius)

            # if game_over:
            #     restart_text = font.render("スペースキーを押して再スタート", True, BLACK)
            #     screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT * 3 // 4))

    pygame.display.flip()
    clock.tick(60)  # 60FPSに制限