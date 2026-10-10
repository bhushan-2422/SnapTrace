import os
import csv
import json
import cv2

from detection import detectFaces
from alignment import alignFace
from embeding import getEmbedding

FOLDER = "public/upload"
OUTPUT_CSV = "embeddings.csv"

def processImage(img_path):
    img = cv2.imread(img_path)
    faces = detectFaces(img_path)

    results = []

    for i, face in enumerate(faces):

        print(
            f"Face {i}: "
            f"bbox={face['bbox']} "
            f"confidence={face['confidence']}"
        )

        alignedFace = alignFace(
            img,
            face["landmarks"]
        )

        # # DEBUG: save each aligned face
        # cv2.imwrite(
        #     f"debug_face_{i}.jpg",
        #     alignedFace
        # )

        embedding = getEmbedding(
            alignedFace
        )

        results.append({
            "bbox": face["bbox"],
            "confidence": face["confidence"],
            "embedding": embedding
        })

    return results

def main():
    with open(OUTPUT_CSV, 'w', newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["img_path","face_index","embedding",  "bbox", "confidence"])

        for filename in os.listdir(FOLDER):
            if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
                continue

            img_path = os.path.join(FOLDER, filename)
            faces = processImage(img_path)

            for i, face in enumerate(faces):
                writer.writerow([
                    img_path, i,
                    json.dumps(face["embedding"]),
                    json.dumps(face["bbox"]),
                    face["confidence"]
                ])
            print(f"{filename}: {len(faces)} faces processed")
    print(f"Done. Saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
