import cv2
import torch
import numpy as np
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor
from photo import capture_and_segment
# モデルの初期化は外に出しておく
config_path = "../sam2/configs/sam2.1/sam2.1_hiera_l.yaml"
ckpt_path = "../sam2/checkpoints/sam2.1_hiera_large.pt"
predictor = SAM2ImagePredictor(build_sam2(config_path, ckpt_path, device="cpu"))

rgb,mask = capture_and_segment(predictor, save_rgb_path="rgb.jpg", save_mask_path="seg.jpg")