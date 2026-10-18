import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import cv2
import ast
import shutil
from pathlib import Path

from detection import detectFaces
from alignment import alignFace
from embeding import getEmbedding


# ============================================================
# CONFIGURATION
# ============================================================

# Folder containing the user's search/selfie image
SEARCH_FOLDER = Path("public/search")

# CSV containing stored face embeddings
EMBEDDING_CSV = Path("embeddings.csv")

# Folder where matching photos will be copied
RETRIEVED_DIR = Path("public/retrieved")

# Initial prototype threshold
SIMILARITY_THRESHOLD = 0.45


# ============================================================
# FIND SEARCH IMAGE
# ============================================================

def get_search_image():
    """
    Find the search image inside public/search/.

    Supported:
        search.png
        search.jpeg
        search.jpg
    """

    possible_files = [
        SEARCH_FOLDER / "search.png",
        SEARCH_FOLDER / "search.jpeg",
        SEARCH_FOLDER / "search.jpg"
    ]

    for image_path in possible_files:
        if image_path.exists():
            return image_path

    raise FileNotFoundError(
        "Search image not found.\n"
        "Put search.png, search.jpeg or search.jpg "
        "inside public/search/"
    )


# ============================================================
# PARSE EMBEDDING
# ============================================================

def parse_embedding(value):
    """
    Convert embedding stored in CSV into NumPy array.
    """

    if isinstance(value, np.ndarray):
        embedding = value

    else:
        try:
            embedding = np.array(
                ast.literal_eval(str(value)),
                dtype=np.float32
            )
        except Exception as e:
            raise ValueError(
                f"Could not parse embedding: {e}"
            )

    # Flatten in case the embedding is not 1-D
    if embedding.ndim != 1:
        embedding = embedding.flatten()

    return embedding


# ============================================================
# GENERATE QUERY EMBEDDING
# ============================================================

def getQueryEmbedding(img_path):
    """
    Detect the face in the search image,
    align it and generate its ArcFace embedding.
    """

    # --------------------------------------------------------
    # Read image
    # --------------------------------------------------------

    img = cv2.imread(str(img_path))

    if img is None:
        raise ValueError(
            f"Could not read image: {img_path}"
        )

    # --------------------------------------------------------
    # Detect faces
    # --------------------------------------------------------

    faces = detectFaces(str(img_path))

    if len(faces) == 0:
        raise ValueError(
            "No face detected in search image."
        )

    if len(faces) > 1:
        raise ValueError(
            "Multiple faces detected in search image. "
            "Please provide an image containing one face."
        )

    # --------------------------------------------------------
    # Get the only detected face
    # --------------------------------------------------------

    face = faces[0]

    # --------------------------------------------------------
    # Align face
    # --------------------------------------------------------

    aligned_face = alignFace(
        img,
        face["landmarks"]
    )

    # --------------------------------------------------------
    # Generate ArcFace embedding
    # --------------------------------------------------------

    embedding = getEmbedding(
        aligned_face
    )

    # --------------------------------------------------------
    # Convert to NumPy
    # --------------------------------------------------------

    embedding = np.asarray(
        embedding,
        dtype=np.float32
    ).flatten()

    return embedding


# ============================================================
# COSINE SIMILARITY
# ============================================================

def calculate_similarity(
    query_embedding,
    stored_embedding
):
    """
    Calculate cosine similarity between
    query and stored face embeddings.
    """

    query_embedding = query_embedding.reshape(
        1, -1
    )

    stored_embedding = stored_embedding.reshape(
        1, -1
    )

    similarity = cosine_similarity(
        query_embedding,
        stored_embedding
    )[0][0]

    return float(similarity)


# ============================================================
# LOAD CSV
# ============================================================

def load_embeddings():
    """
    Load face embeddings from CSV.

    Expected columns:

        img_path
        face_index
        embedding
        bbox
        confidence
    """

    # --------------------------------------------------------
    # Check CSV exists
    # --------------------------------------------------------

    if not EMBEDDING_CSV.exists():
        raise FileNotFoundError(
            f"Embedding CSV not found: "
            f"{EMBEDDING_CSV}"
        )

    # --------------------------------------------------------
    # Read CSV
    # --------------------------------------------------------

    df = pd.read_csv(
        EMBEDDING_CSV
    )

    # --------------------------------------------------------
    # Expected columns
    # --------------------------------------------------------

    required_columns = {
        "img_path",
        "face_index",
        "embedding",
        "bbox",
        "confidence"
    }

    # --------------------------------------------------------
    # Validate columns
    # --------------------------------------------------------

    if not required_columns.issubset(
        df.columns
    ):
        raise ValueError(
            f"CSV must contain columns: "
            f"{required_columns}\n"
            f"Found: {list(df.columns)}"
        )

    return df


# ============================================================
# RETRIEVE PHOTOS
# ============================================================

def retrieve_photos(
    threshold=SIMILARITY_THRESHOLD
):

    # --------------------------------------------------------
    # 1. Find search image
    # --------------------------------------------------------

    search_img = get_search_image()

    print(
        f"Search image: {search_img}"
    )

    # --------------------------------------------------------
    # 2. Generate query embedding
    # --------------------------------------------------------

    query_embedding = getQueryEmbedding(
        search_img
    )

    print(
        "Query embedding dimension:",
        query_embedding.shape
    )

    # --------------------------------------------------------
    # 3. Load stored embeddings
    # --------------------------------------------------------

    df = load_embeddings()

    print(
        f"Loaded {len(df)} face embeddings."
    )

    # --------------------------------------------------------
    # 4. Compare query against every stored face
    # --------------------------------------------------------

    matches = []

    for index, row in df.iterrows():

        # ----------------------------------------------------
        # Get image path from CSV
        # ----------------------------------------------------

        image_path = Path(
            str(row["img_path"])
        )

        image_name = image_path.name

        try:

            # ------------------------------------------------
            # Parse stored embedding
            # ------------------------------------------------

            stored_embedding = parse_embedding(
                row["embedding"]
            )
            print(
                f"{image_name} | "
                f"face={row['face_index']} | "
                f"embedding norm={np.linalg.norm(stored_embedding):.4f} | "
                f"first5={stored_embedding[:5]}"
            )

            # ------------------------------------------------
            # Check embedding dimensions
            # ------------------------------------------------

            if (
                stored_embedding.shape
                != query_embedding.shape
            ):

                print(
                    f"Skipping {image_name} "
                    f"(face {row['face_index']}): "
                    f"embedding dimension mismatch."
                )

                continue

            # ------------------------------------------------
            # Calculate similarity
            # ------------------------------------------------

            similarity = calculate_similarity(
                query_embedding,
                stored_embedding
            )

            # ------------------------------------------------
            # Print score
            # ------------------------------------------------

            print(
                f"{image_name} "
                f"| face={row['face_index']} "
                f"| similarity={similarity:.4f}"
            )

            # ------------------------------------------------
            # Check threshold
            # ------------------------------------------------

            if similarity >= threshold:

                matches.append({
                    "image_name": image_name,
                    "image_path": image_path,
                    "face_index": row["face_index"],
                    "similarity": similarity
                })

        except Exception as e:

            print(
                f"Error processing "
                f"{image_name}: {e}"
            )

    # --------------------------------------------------------
    # 5. Sort matches by similarity
    # --------------------------------------------------------

    matches.sort(
        key=lambda x: x["similarity"],
        reverse=True
    )

    # --------------------------------------------------------
    # 6. Create retrieved directory
    # --------------------------------------------------------

    RETRIEVED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # 7. Copy matching photos
    # --------------------------------------------------------

    copied_images = set()

    for match in matches:

        image_name = match["image_name"]

        # ----------------------------------------------------
        # Multiple faces can belong to same photo.
        #
        # Example:
        #
        # photo1.jpg -> face 0 -> match
        # photo1.jpg -> face 1 -> match
        #
        # We only want to copy photo1.jpg once.
        # ----------------------------------------------------

        if image_name in copied_images:
            continue

        # ----------------------------------------------------
        # Get actual source path from CSV
        # ----------------------------------------------------

        source_path = match["image_path"]

        # ----------------------------------------------------
        # Check image exists
        # ----------------------------------------------------

        if not source_path.exists():

            print(
                f"Warning: image not found: "
                f"{source_path}"
            )

            continue

        # ----------------------------------------------------
        # Destination
        # ----------------------------------------------------

        destination_path = (
            RETRIEVED_DIR / image_name
        )

        # ----------------------------------------------------
        # Copy image
        # ----------------------------------------------------

        shutil.copy2(
            source_path,
            destination_path
        )

        copied_images.add(
            image_name
        )

        print(
            f"MATCH: {image_name} "
            f"| similarity = "
            f"{match['similarity']:.4f}"
        )

    # --------------------------------------------------------
    # 8. Final result
    # --------------------------------------------------------

    print("\n==============================")
    print("PHOTO RETRIEVAL COMPLETE")
    print("==============================")

    print(
        f"CSV entries       : {len(df)}"
    )

    print(
        f"Matching entries  : {len(matches)}"
    )

    print(
        f"Photos retrieved  : "
        f"{len(copied_images)}"
    )

    print(
        f"Output directory  : "
        f"{RETRIEVED_DIR}"
    )

    return matches


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    results = retrieve_photos()

    print("\nFinal matches:")

    for result in results:

        print(
            f"{result['image_name']} "
            f"-> "
            f"{result['similarity']:.4f}"
        )