from deepface import DeepFace

def getEmbedding(alignedFace):
    result = DeepFace.represent(
        img_path=alignedFace,
        model_name="ArcFace",
        detector_backend="skip",
        enforce_detection=False
    )

    embedding = result[0]["embedding"]

    return embedding