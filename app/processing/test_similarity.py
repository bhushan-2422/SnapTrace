import pandas as pd
import numpy as np
import ast
from sklearn.metrics.pairwise import cosine_similarity


CSV = "embeddings.csv"


def parse_embedding(value):
    return np.array(
        ast.literal_eval(str(value)),
        dtype=np.float32
    ).flatten()


df = pd.read_csv(CSV)

embeddings = np.array([
    parse_embedding(x)
    for x in df["embedding"]
])

print("Embedding matrix shape:")
print(embeddings.shape)


# Normalize
normalized = embeddings / np.linalg.norm(
    embeddings,
    axis=1,
    keepdims=True
)


similarities = cosine_similarity(normalized)


print("\nPairwise similarity matrix:\n")

np.set_printoptions(
    precision=3,
    suppress=True
)

print(similarities)


print("\nStatistics:")

# Remove diagonal
mask = ~np.eye(
    similarities.shape[0],
    dtype=bool
)

different_face_scores = similarities[mask]

print(
    "Minimum similarity:",
    different_face_scores.min()
)

print(
    "Maximum similarity:",
    different_face_scores.max()
)

print(
    "Mean similarity:",
    different_face_scores.mean()
)