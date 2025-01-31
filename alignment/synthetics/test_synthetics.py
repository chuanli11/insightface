from trainer_synthetics import FaceSynthetics
import sys
import glob
import torch
import os
import numpy as np
import cv2
import os.path as osp
import insightface
from insightface.app import FaceAnalysis
from insightface.utils import face_align

flip_parts = (
    [1, 17],
    [2, 16],
    [3, 15],
    [4, 14],
    [5, 13],
    [6, 12],
    [7, 11],
    [8, 10],
    [18, 27],
    [19, 26],
    [20, 25],
    [21, 24],
    [22, 23],
    [32, 36],
    [33, 35],
    [37, 46],
    [38, 45],
    [39, 44],
    [40, 43],
    [41, 48],
    [42, 47],
    [49, 55],
    [50, 54],
    [51, 53],
    [62, 64],
    [61, 65],
    [68, 66],
    [59, 57],
    [60, 56],
)

app = FaceAnalysis()
app.prepare(ctx_id=0, det_size=(224, 224))
input_size = 256
USE_FLIP = False

directory_path = "/home/ubuntu/Chimp/insightface_chuan/detection/scrfd/outputs/Chimp_5000_0.3_scrfd10g_cleaned"
output_dir = "Chimp_5000_0.3_scrfd10g_cleaned_lmrk/"

if not osp.exists(output_dir):
    os.makedirs(output_dir)

model = FaceSynthetics.load_from_checkpoint(
    "/home/ubuntu/Chimp/models/synthetic_resnet50d.ckpt"
).cuda()

model.eval()

# Use glob to find all .jpg and .png files in the specified directory
img_paths = glob.glob(os.path.join(directory_path, "*.png")) + glob.glob(
    os.path.join(directory_path, "*.png")
)

for img_path in img_paths:
    img = cv2.imread(img_path)
    dimg = img.copy()
    faces = app.get(img, max_num=1)
    if len(faces) != 1:
        continue
    bbox = faces[0].bbox
    w, h = (bbox[2] - bbox[0]), (bbox[3] - bbox[1])
    center = (bbox[2] + bbox[0]) / 2, (bbox[3] + bbox[1]) / 2
    rotate = 0
    _scale = input_size / (max(w, h) * 1.5)
    aimg, M = face_align.transform(img, center, input_size, _scale, rotate)

    aimg = cv2.cvtColor(aimg, cv2.COLOR_BGR2RGB)
    kps = None
    flips = [0, 1] if USE_FLIP else [0]
    for flip in flips:
        input = aimg.copy()
        if flip:
            input = input[:, ::-1, :].copy()
        input = np.transpose(input, (2, 0, 1))
        input = np.expand_dims(input, 0)
        imgs = torch.Tensor(input).cuda()
        imgs.div_(255).sub_(0.5).div_(0.5)
        pred = model(imgs).detach().cpu().numpy().flatten().reshape((-1, 2))
        pred[:, 0:2] += 1
        pred[:, 0:2] *= input_size // 2
        if flip:
            pred_flip = pred.copy()
            pred_flip[:, 0] = input_size - 1 - pred_flip[:, 0]
            for pair in flip_parts:
                tmp = pred_flip[pair[0] - 1, :].copy()
                pred_flip[pair[0] - 1, :] = pred_flip[pair[1] - 1, :]
                pred_flip[pair[1] - 1, :] = tmp
            pred = pred_flip
        if kps is None:
            kps = pred
        else:
            kps += pred
            kps /= 2.0

    IM = cv2.invertAffineTransform(M)
    kps = face_align.trans_points(kps, IM)

    box = bbox.astype(np.int)
    color = (0, 0, 255)
    # cv2.rectangle(dimg, (box[0], box[1]), (box[2], box[3]), color, 2)
    kps = kps.astype(np.int)

    for l in range(kps.shape[0]):
        color = (0, 0, 255)
        cv2.circle(dimg, (kps[l][0], kps[l][1]), 1, color, 2)

    filename = img_path.split("/")[-1]

    # roi = dimg[box[1] : box[3], box[0] : box[2], :]

    cv2.imwrite(output_dir + "%s" % filename, dimg)
