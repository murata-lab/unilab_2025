import pygame
import pymunk
import numpy as np
import cv2

def create_transparent_surface(rgb, mask, scale=1.0):
    import cv2
    import numpy as np
    import pygame

    if rgb is None or mask is None:
        print("RGBまたはマスク画像が提供されていません。")
    
    # マスク画像の白い部分を物体として使う（そのまま alpha に）
    _, mask_bin = cv2.threshold(mask, 250, 255, cv2.THRESH_BINARY)

    # アルファチャンネルとして使用（物体=白）
    masked_rgb = cv2.bitwise_and(rgb, rgb, mask=mask_bin)
    result = cv2.merge([masked_rgb[:, :, 0], masked_rgb[:, :, 1], masked_rgb[:, :, 2], mask_bin])

    # スケーリング
    result = cv2.resize(result, (0, 0), fx=scale, fy=scale)
    
    # 水平反転（プレビューカメラと同じ鏡像にする）
    result = cv2.flip(result, 1)  # 1 = 水平反転

    # Pygame Surfaceに変換
    result = cv2.cvtColor(result, cv2.COLOR_BGRA2RGBA)
    surface = pygame.image.frombuffer(result.tobytes(), result.shape[1::-1], "RGBA")

    return surface

class Animal:
    def __init__(self, space, x, y, rgb=None, mask=None, scale=0.1):
        self.space = space
        self.x = x
        self.y = y
        self.scale = scale
        
        # 回転キャッシュ（パフォーマンス向上）
        self._rotation_cache = {}
        self._cache_size_limit = 360



        self.image = create_transparent_surface(rgb, mask, scale)

        # 輪郭（物理ポリゴン）も mask から取得
        self.points = self.load_mask_points(mask, scale)
        if self.points:
            center_x = np.mean([p[0] for p in self.points])
            center_y = np.mean([p[1] for p in self.points])
            self.center_x = center_x
            self.center_y = center_y

            points_shifted = [(px - center_x, py - center_y) for (px, py) in self.points]

            self.body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
            self.body.position = (x, y)
            
            # 物理演算の最適化: ポリゴンの頂点数を制限
            if len(points_shifted) > 20:
                # 頂点数が多い場合は簡素化
                simplified_points = self.simplify_polygon(points_shifted, tolerance=2.0)
                self.shape = pymunk.Poly(self.body, simplified_points)
            else:
                self.shape = pymunk.Poly(self.body, points_shifted)
            
            self.shape.friction = 2.5  # 摩擦をさらに上げて滑りにくくする
            self.shape.elasticity = 0.2  # 反発を下げてより安定した積み重ねに
            # 密度は設定しない（質量で調整するため）
            self.space.add(self.body, self.shape)
            self.points = points_shifted
        else:
            raise ValueError("輪郭が見つかりませんでした")

        self.falling = False

    def simplify_polygon(self, points, tolerance=2.0):
        """ポリゴンの頂点数を削減して物理演算を軽量化"""
        if len(points) <= 8:
            return points
        
        # 簡易的な頂点削減アルゴリズム
        simplified = [points[0]]
        for i in range(1, len(points) - 1):
            p1 = simplified[-1]
            p2 = points[i]
            p3 = points[i + 1]
            
            # 3点間の距離を計算
            dist1 = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            dist2 = np.sqrt((p3[0] - p2[0])**2 + (p3[1] - p2[1])**2)
            
            # 距離が一定以上ある場合のみ頂点を保持
            if dist1 > tolerance or dist2 > tolerance:
                simplified.append(p2)
        
        simplified.append(points[-1])
        return simplified

    def remove_from_space(self):
        """物理空間からこの動物を削除する"""
        if hasattr(self, 'shape') and self.shape:
            self.space.remove(self.shape)
        if hasattr(self, 'body') and self.body:
            self.space.remove(self.body)

    def load_mask_points(self, mask, scale):
        _, mask_bin = cv2.threshold(mask, 250, 255, cv2.THRESH_BINARY)
        mask_bin = cv2.resize(mask_bin, (0, 0), fx=scale, fy=scale)
        
        # 水平反転（プレビューカメラと同じ鏡像にする）
        mask_bin = cv2.flip(mask_bin, 1)  # 1 = 水平反転
        
        contours, _ = cv2.findContours(mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            largest = max(contours, key=cv2.contourArea)
            return [(pt[0][0], pt[0][1]) for pt in largest]  # Y軸反転
        return None

    def start_fall(self):
        self.body.body_type = pymunk.Body.DYNAMIC
        
        # さらに軽い質量設定（より軽快な動きに）
        mass = 0.05  # 0.1から0.05に軽量化
        
        if self.image and self.points:
            moment = pymunk.moment_for_poly(mass, self.points)
        else:
            moment = pymunk.moment_for_box(mass, (50, 50))

        self.body.mass = mass
        self.body.moment = moment
        self.body.velocity = (0, 0)
        self.body.angular_velocity = 0  # 角速度を初期化
        self.falling = True



    def draw(self, screen):
        x, y = self.body.position
        angle = -self.body.angle * 57.2958  # pymunkは反時計回り → 度に変換

        if self.image:
            offset = pygame.Vector2(self.center_x, self.center_y)

            # 回転キャッシュを使用（パフォーマンス向上）
            angle_rounded = round(angle)
            
            if angle_rounded not in self._rotation_cache:
                # キャッシュサイズを制限
                if len(self._rotation_cache) >= self._cache_size_limit:
                    # 最も古いキャッシュを削除（LRU方式）
                    oldest_key = min(self._rotation_cache.keys())
                    del self._rotation_cache[oldest_key]
                
                # 高品質な回転処理
                rotated_image = pygame.transform.rotate(self.image, angle_rounded)
                # 回転後の画像を最適化
                rotated_image = rotated_image.convert_alpha()
                self._rotation_cache[angle_rounded] = rotated_image
            
            rotated_image = self._rotation_cache[angle_rounded]
            image_rect = self.image.get_rect()
            rotated_rect = rotated_image.get_rect()

            # 画像中心に対する相対オフセット（回転前）
            offset_from_center = offset - pygame.Vector2(image_rect.width / 2, image_rect.height / 2)

            # 回転角度を反転して、pymunkと一致させる
            rotated_offset = offset_from_center.rotate(-angle_rounded)

            # 左上座標で貼る
            draw_pos = (x - rotated_offset.x - rotated_rect.width / 2,
                        y - rotated_offset.y - rotated_rect.height / 2)

            screen.blit(rotated_image, draw_pos)


