import cv2
import torch
import numpy as np
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor
from PIL import Image, ImageDraw, ImageFont

# OpenCV画像（BGR）をPillow画像（RGB）に変換
def put_japanese_text(img, text, position, font_path="C:/Windows/Fonts/msgothic.ttc", font_size=32):
    # OpenCV (BGR) -> PIL (RGB)
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    # 日本語フォント指定
    font = ImageFont.truetype(font_path, font_size)
    draw = ImageDraw.Draw(img_pil)
    draw.text(position, text, font=font, fill=(255,0, 0))

    # PIL (RGB) -> OpenCV (BGR)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)



def capture_and_segment(predictor):
    # 複数のカメラを順番に試す
    cameras_to_try = [1, 0, 2, 3]  # カメラ1を最初に試す（ウェブカメラの可能性が高い）
    
    cap = None
    for camera_id in cameras_to_try:
        print(f"カメラ{camera_id}を試しています...")
        cap = cv2.VideoCapture(camera_id)
        if cap.isOpened():
            print(f"カメラ{camera_id}が使用可能です")
            break
        else:
            cap.release()
    
    if not cap or not cap.isOpened():
        print("使用可能なカメラが見つかりませんでした。")
        return None, None
    
    # カメラの設定を最適化
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    print("スペースキーで撮影・確認、ESCキーで終了")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("カメラから画像が取得できませんでした")
            break

        height, width = frame.shape[:2]
        center = np.array([[width // 2, height // 2]])
        labels = np.array([1])

        # 表示用ポイント
        preview_frame = frame.copy()
        for pt in center:
            cv2.circle(preview_frame, tuple(pt), 5, (0, 0, 255), -1)

        # プレビュー画面を大きくする
        preview_width = 1280  # プレビュー画面の幅
        preview_height = 720  # プレビュー画面の高さ
        preview_frame_resized = cv2.resize(preview_frame, (preview_width, preview_height))

        cv2.imshow("Live Preview (ESC to quit, Space to capture)", preview_frame_resized)
        key = cv2.waitKey(1)

        if key == 27:  # ESC
            break

        elif key == 32:  # Space
            clean_frame = frame.copy()
            image = cv2.cvtColor(clean_frame, cv2.COLOR_BGR2RGB)
            predictor.set_image(image)
            with torch.inference_mode():
                masks, _, _ = predictor.predict(
                    point_coords=center,
                    point_labels=labels,
                    box=None,
                    mask_input=None,
                    multimask_output=True
                )

            final_mask = np.zeros((height, width), dtype=np.uint8)
            for m in masks:
                final_mask = np.maximum(final_mask, (m > 0.0).astype(np.uint8))

            # 表示用：マスクはグレースケール
            mask_display = cv2.cvtColor(final_mask * 255, cv2.COLOR_GRAY2BGR)
            combined = cv2.hconcat([clean_frame, mask_display])
            message = "この結果で良ければ 'y' キーをだめなら'n'キーをおしてください"
            combined = put_japanese_text(combined, message, (30, height - 40))  # 高さ少し上げて調整

            # 確認画面も大きくする
            check_width = 1300  # 確認画面の幅（1600から300小さく）
            check_height = 600  # 確認画面の高さ
            combined_resized = cv2.resize(combined, (check_width, check_height))

            cv2.imshow("check", combined_resized)

            key = cv2.waitKey(0)
            if key == ord("y"):
                print("撮影完了")
                cap.release()
                cv2.destroyAllWindows()
                return clean_frame, final_mask*255
            if key == ord("n"):
                print("再撮影します...")
                cv2.destroyWindow("check") 
                continue

    cap.release()
    cv2.destroyAllWindows()
    return None, None


def capture_from_existing_camera(camera_cap, predictor):
    """既に開いているカメラから直接撮影してセグメンテーションを行う"""
    if not camera_cap or not camera_cap.isOpened():
        print("カメラが利用できません")
        return None, None
    
    # 現在のフレームを取得
    ret, frame = camera_cap.read()
    if not ret:
        print("カメラから画像が取得できませんでした")
        return None, None
    
    height, width = frame.shape[:2]
    center = np.array([[width // 2, height // 2]])
    labels = np.array([1])
    
    # セグメンテーション実行
    clean_frame = frame.copy()
    image = cv2.cvtColor(clean_frame, cv2.COLOR_BGR2RGB)
    predictor.set_image(image)
    
    with torch.inference_mode():
        masks, _, _ = predictor.predict(
            point_coords=center,
            point_labels=labels,
            box=None,
            mask_input=None,
            multimask_output=True
        )
    
    final_mask = np.zeros((height, width), dtype=np.uint8)
    for m in masks:
        final_mask = np.maximum(final_mask, (m > 0.0).astype(np.uint8))
    
    print("撮影完了")
    return clean_frame, final_mask*255
