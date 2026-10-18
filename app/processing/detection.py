from retinaface import RetinaFace
import json

CONFIDENCE_THRESHOLD = 0.5

def detectFaces(img_path):
    detections = RetinaFace.detect_faces(img_path)
    if not isinstance(detections, dict):
        return []
    
    faces = []

    for face_id, data in detections.items():
        if data["score"] < CONFIDENCE_THRESHOLD:
            continue

        faces.append({
            "bbox": [int(v) for v in data["facial_area"]],           # np.int64 -> int
            "landmarks": {
                name: [float(x), float(y)]                            # np.float32 -> float
                for name, (x, y) in data["landmarks"].items()
            },
            "confidence": float(data["score"]),                       # np.float64 -> float
        })
    return faces


# face = detectFaces("/home/bhushan/Desktop/project/snapTrace/processingService/img2.jpeg")
# print(json.dumps(face, indent=2))