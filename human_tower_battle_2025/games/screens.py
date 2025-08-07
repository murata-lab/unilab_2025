import pygame
import os
from ranking import RankingManager

class Button:
    def __init__(self, x, y, width, height, text, font_size=32, color=(100, 100, 100), hover_color=(150, 150, 150)):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.current_color = color
        self.font_size = font_size
        
        # フォント設定（macOS対応）
        try:
            # macOS用の日本語フォント
            self.font = pygame.font.Font("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", font_size)
        except:
            try:
                # 代替フォント
                self.font = pygame.font.Font("/System/Library/Fonts/Arial Unicode MS.ttf", font_size)
            except:
                # デフォルトフォント
                self.font = pygame.font.Font(None, font_size)
    
    def draw(self, surface):
        # ボタンの背景を描画
        pygame.draw.rect(surface, self.current_color, self.rect)
        pygame.draw.rect(surface, (255, 255, 255), self.rect, 3)  # 白い枠線
        
        # テキストを描画
        text_surface = self.font.render(self.text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            if self.rect.collidepoint(event.pos):
                self.current_color = self.hover_color
            else:
                self.current_color = self.color
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False

class StartScreen:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.ranking_manager = RankingManager()
        
        # ウィンドウサイズに応じてスケールを計算
        base_width, base_height = 1440, 2489
        scale = min(width / base_width, height / base_height)
        
        # ボタンの作成（スケール適用）
        button_width = int(300 * scale)
        button_height = int(80 * scale)
        button_x = (width - button_width) // 2
        button_y = height // 2 + int(100 * scale)
        
        title_font_size = int(60 * scale)  # タイトルフォントを大きく
        subtitle_font_size = int(32 * scale)  # サブタイトルフォントを大きく
        button_font_size = int(44 * scale)  # ボタンフォントを大きく
        ranking_font_size = int(52 * scale)  # ランキングフォントをさらに大きく
        
        self.start_button = Button(button_x, button_y, button_width, button_height, "ゲーム開始", button_font_size)
        
        # フォント設定（macOS対応、スケール適用）
        try:
            # macOS用の日本語フォント
            self.title_font = pygame.font.Font("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", title_font_size)
            self.subtitle_font = pygame.font.Font("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", subtitle_font_size)
            self.ranking_font = pygame.font.Font("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", ranking_font_size)
        except:
            try:
                # 代替フォント
                self.title_font = pygame.font.Font("/System/Library/Fonts/Arial Unicode MS.ttf", title_font_size)
                self.subtitle_font = pygame.font.Font("/System/Library/Fonts/Arial Unicode MS.ttf", subtitle_font_size)
                self.ranking_font = pygame.font.Font("/System/Library/Fonts/Arial Unicode MS.ttf", ranking_font_size)
            except:
                # デフォルトフォント
                self.title_font = pygame.font.Font(None, title_font_size)
                self.subtitle_font = pygame.font.Font(None, subtitle_font_size)
                self.ranking_font = pygame.font.Font(None, ranking_font_size)
    
    def draw(self, surface):
        # 背景画像を読み込んで表示
        try:
            background = pygame.image.load("Background.png")
            background = pygame.transform.scale(background, (self.width, self.height))
            surface.blit(background, (0, 0))
        except:
            # 背景画像が見つからない場合は白で塗りつぶす
            surface.fill((255, 255, 255))
        
        # ウィンドウサイズに応じてスケールを計算
        base_width, base_height = 1440, 2489
        scale = min(self.width / base_width, self.height / base_height)
        
        # タイトルを描画（スケール適用）
        title_text = self.title_font.render("人間タワーバトル", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(self.width // 2, self.height // 2 - int(100 * scale)))
        surface.blit(title_text, title_rect)
        
        # サブタイトルを描画（スケール適用）
        subtitle_text = self.subtitle_font.render("カメラで撮影してタワーを積み上げよう！", True, (255, 255, 255))
        subtitle_rect = subtitle_text.get_rect(center=(self.width // 2, self.height // 2 - int(50 * scale)))
        surface.blit(subtitle_text, subtitle_rect)
        
        # ランキングを描画
        self.draw_rankings(surface, scale)
        
        # ボタンを描画
        self.start_button.draw(surface)
    
    def draw_rankings(self, surface, scale):
        """ランキングを描画"""
        # 本日のランキングを取得
        daily_rankings = self.ranking_manager.get_daily_rankings()
        
        # ランキング表示
        if daily_rankings:
            top_score = daily_rankings[0]
            rank_text = f"今日の1位：{top_score['score']}人"
            rank_surface = self.ranking_font.render(rank_text, True, (255, 215, 0))  # 金色
            rank_rect = rank_surface.get_rect()
            rank_rect.topleft = (int(50 * scale), int(50 * scale))
            surface.blit(rank_surface, rank_rect)
        else:
            no_data_text = self.ranking_font.render("今日の1位：まだきろくがありません", True, (255, 215, 0))  # 金色
            no_data_rect = no_data_text.get_rect()
            no_data_rect.topleft = (int(50 * scale), int(50 * scale))
            surface.blit(no_data_text, no_data_rect)
    
    def handle_event(self, event):
        return self.start_button.handle_event(event)

class GameOverScreen:
    def __init__(self, width, height, score=0, ranking_manager=None):
        self.width = width
        self.height = height
        self.score = score
        
        # ランキングマネージャーを共有するか新しく作成
        if ranking_manager:
            self.ranking_manager = ranking_manager
        else:
            self.ranking_manager = RankingManager()
        
        # スコアをランキングに追加（重複を防ぐため、既に記録されているかチェック）
        if score > 0:
            # 同じスコアが既に記録されているかチェック
            daily_rankings = self.ranking_manager.get_daily_rankings()
            already_recorded = any(entry['score'] == score for entry in daily_rankings)
            
            if not already_recorded:
                self.ranking_manager.add_score(score)
        
        # ウィンドウサイズに応じてスケールを計算
        base_width, base_height = 1440, 2489
        scale = min(width / base_width, height / base_height)
        
        
        # ボタンの作成（スケール適用）
        button_width = int(300 * scale)
        button_height = int(80 * scale)
        button_x = (width - button_width) // 2
        button_y = height // 2 + int(100 * scale)
        
        title_font_size = int(60 * scale)  # タイトルフォントを大きく
        score_font_size = int(48 * scale)  # スコアフォントを大きく
        button_font_size = int(40 * scale)  # ボタンフォントを大きく
        ranking_font_size = int(52 * scale)  # ランキングフォントをさらに大きく
        
        self.restart_button = Button(button_x, button_y - int(50 * scale), button_width, button_height, "もう一度プレイ", button_font_size)
        self.quit_button = Button(button_x, button_y + int(50 * scale), button_width, button_height, "終了", button_font_size)
        
        # フォント設定（macOS対応、スケール適用）
        try:
            # macOS用の日本語フォント
            self.title_font = pygame.font.Font("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", title_font_size)
            self.score_font = pygame.font.Font("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", score_font_size)
            self.ranking_font = pygame.font.Font("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", ranking_font_size)
        except:
            try:
                # 代替フォント
                self.title_font = pygame.font.Font("/System/Library/Fonts/Arial Unicode MS.ttf", title_font_size)
                self.score_font = pygame.font.Font("/System/Library/Fonts/Arial Unicode MS.ttf", score_font_size)
                self.ranking_font = pygame.font.Font("/System/Library/Fonts/Arial Unicode MS.ttf", ranking_font_size)
            except:
                # デフォルトフォント
                self.title_font = pygame.font.Font(None, title_font_size)
                self.score_font = pygame.font.Font(None, score_font_size)
                self.ranking_font = pygame.font.Font(None, ranking_font_size)
    
    def draw(self, surface):
        # 背景画像を読み込んで表示
        try:
            background = pygame.image.load("Background.png")
            background = pygame.transform.scale(background, (self.width, self.height))
            surface.blit(background, (0, 0))
        except:
            # 背景画像が見つからない場合は白で塗りつぶす
            surface.fill((255, 255, 255))
        
        # ウィンドウサイズに応じてスケールを計算
        base_width, base_height = 1440, 2489
        scale = min(self.width / base_width, self.height / base_height)
        
        # ゲームオーバーテキストを描画（スケール適用）
        game_over_text = self.title_font.render("GAME OVER", True, (255, 0, 0))
        game_over_rect = game_over_text.get_rect(center=(self.width // 2, self.height // 2 - int(100 * scale)))
        surface.blit(game_over_text, game_over_rect)
        
        # スコアを描画（スケール適用）
        score_text = self.score_font.render(f"つみあげた人数: {self.score}人", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(self.width // 2, self.height // 2 - int(50 * scale)))
        surface.blit(score_text, score_rect)
        
        # ランキングを描画
        self.draw_rankings(surface, scale)
        
        # ボタンを描画
        self.restart_button.draw(surface)
        self.quit_button.draw(surface)
    
    def draw_rankings(self, surface, scale):
        """ランキングを描画"""
        # 本日のランキングを取得
        daily_rankings = self.ranking_manager.get_daily_rankings()
       
        # プレイヤーの順位を取得
        player_rank = self.ranking_manager.get_player_rank(self.score)
        
        # ランキング表示（中央配置）
        if daily_rankings:
            top_score = daily_rankings[0]
            rank_text = f"今日の1位：{top_score['score']}人"
            rank_surface = self.ranking_font.render(rank_text, True, (255, 215, 0))  # 金色
            rank_rect = rank_surface.get_rect()
            rank_rect.center = (self.width // 2, self.height // 2 - int(500 * scale))  # さらに上に移動
            surface.blit(rank_surface, rank_rect)
        else:
            no_data_text = self.ranking_font.render("今日の1位：まだきろくがありません", True, (255, 215, 0))  # 金色
            no_data_rect = no_data_text.get_rect()
            no_data_rect.center = (self.width // 2, self.height // 2 - int(500 * scale))  # さらに上に移動
            surface.blit(no_data_text, no_data_rect)
        
        # プレイヤーの順位表示（金色、中央配置）
        rank_text = f"あなたの順位：{player_rank}位"
        rank_surface = self.ranking_font.render(rank_text, True, (255, 215, 0))  # 金色で表示
        rank_rect = rank_surface.get_rect()
        rank_rect.center = (self.width // 2, self.height // 2 - int(430* scale))  # さらに上に移動
        surface.blit(rank_surface, rank_rect)
    
    def handle_event(self, event):
        if self.restart_button.handle_event(event):
            return "restart"
        elif self.quit_button.handle_event(event):
            return "quit"
        return None 