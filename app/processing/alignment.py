import cv2
import numpy as np
from skimage import transform as trans

REFERENCE_LANDMARKS = np.array([
    [38.2946, 51.6963],   # left eye
    [73.5318, 51.5014],   # right eye
    [56.0252, 71.7366],   # nose
    [41.5493, 92.3655],   # mouth left
    [70.7299, 92.2041],   # mouth right
], dtype=np.float32)


def alignFace(img, landmarks):

    # RetinaFace "left_eye" is the person's left eye, which appears on the
    # image RIGHT for a camera-facing person. The reference template's
    # "left eye" is on the image LEFT. Swap sides so the point sets
    # are not mirrored (a mirrored fit collapses the similarity scale).
    detected_points = np.array([
        landmarks["right_eye"],
        landmarks["left_eye"],
        landmarks["nose"],
        landmarks["mouth_right"],
        landmarks["mouth_left"],
    ], dtype=np.float32)

    transform = trans.SimilarityTransform()

    # Source face landmarks -> ArcFace reference landmarks
    transform.estimate(
        detected_points,
        REFERENCE_LANDMARKS
    )

    warp_matrix = transform.params[:2, :]

    aligned = cv2.warpAffine(
        img,
        warp_matrix,
        (112, 112),
        flags=cv2.INTER_LINEAR
    )

    return aligned