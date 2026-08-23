import pandas as pd
import rapidfuzz
import data_pull 
import numpy as np


# Date,Name,Year,Letterboxd URI,Rating

def compute_taste_vector(csv_path, conn, threshold = 85, min_rating = 4.0):
    df = pd.read_csv(csv_path)

    #filters to only include movies with a rating of 4.0 or higher
    filterdf = df[df["Rating"] >= min_rating]

    #print(len(filterdf))
    #print(filterdf[["Name", "Year", "Rating"]].head(10))

    movies_df = pd.read_sql("SELECT tmdb_id, title FROM movies", conn)


    ratings = {}
    for _, my_row in filterdf.iterrows():
        best_score = 0
        best_match = None
        for _, tmdb_row in movies_df.iterrows():   
            if rapidfuzz.fuzz.ratio(tmdb_row["title"], my_row["Name"]) > best_score:
                best_score = rapidfuzz.fuzz.ratio(tmdb_row["title"], my_row["Name"])
                best_match = tmdb_row
        if best_score >= threshold:
            ratings[best_match["tmdb_id"]] = my_row["Rating"]


    #print(len(ratings))
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
    return(taste_vector)


if __name__ == "__main__":
    conn = data_pull.get_conn()
    taste_vector = compute_taste_vector("./test_data/ratings.csv", conn)
    print(taste_vector)