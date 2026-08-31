import pandas as pd
from rapidfuzz import process, fuzz
import data_pull
import numpy as np


# Date,Name,Year,Letterboxd URI,Rating

def compute_taste_vector(csv_path, conn, threshold=85, min_rating=4.0):
    df = pd.read_csv(csv_path)

    # filters to only include movies with a rating of 4.0 or higher
    filterdf = df[df["Rating"] >= min_rating]

    movies_df = pd.read_sql("SELECT tmdb_id, title FROM movies", conn)
    titles = movies_df["title"].tolist()

    ratings = {}
    for _, my_row in filterdf.iterrows():
        match = process.extractOne(
            my_row["Name"], titles, scorer=fuzz.ratio, score_cutoff=threshold
        )
        if match is not None:
            matched_title, score, idx = match
            tmdb_id = movies_df.iloc[idx]["tmdb_id"]
            ratings[tmdb_id] = my_row["Rating"]

    tmdb_ids = [int(tid) for tid in ratings.keys()]
    cur = conn.cursor()
    cur.execute(
        "SELECT tmdb_id, embedding FROM movies WHERE tmdb_id = ANY(%s::int[])",
        (tmdb_ids,)
    )
    rows = cur.fetchall()

    vectors = []
    weights = []
    for tmdb_id, embedding in rows:
        vectors.append(embedding.to_numpy())
        weights.append(ratings[tmdb_id])

    vectors = np.array(vectors, dtype=np.float64)
    weights = np.array(weights, dtype=np.float64)

    taste_vector = np.average(vectors, axis=0, weights=weights)
    return taste_vector, tmdb_ids


if __name__ == "__main__":
    conn = data_pull.get_conn()
    taste_vector, watched_ids = compute_taste_vector("./test_data/ratings.csv", conn)
    print(taste_vector, watched_ids)