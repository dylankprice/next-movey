import os
import time
import json
import requests
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
load_dotenv() #get .env vars
from pgvector.psycopg2 import register_vector


#hyperparams
TMDB_ACCESS_TOKEN = os.environ["TMDB_ACCESS_TOKEN"]
DATABASE_URL = os.environ["DATABASE_URL"]

BASE_URL = "https://api.themoviedb.org/3"
HEADERS = {
    "Authorization": f"Bearer {TMDB_ACCESS_TOKEN}",
    "accept": "application/json",
}

TARGET_COUNT = 3000
DISCOVER_PARAMS = {
    "sort_by": "vote_count.desc",  #sort movies by popularity
    "vote_count.gte": 50,
    "include_adult": "false",
}


#grabs movie ids
def discover_movie_ids(target_count=TARGET_COUNT):
    ids = []
    page = 1
    while len(ids) < target_count:
        resp = _get(f"{BASE_URL}/discover/movie", params={**DISCOVER_PARAMS, "page": page})
        results = resp.get("results", [])
        if not results:
            break
        ids.extend(m["id"] for m in results)
        page += 1
        if page > resp.get("total_pages", page):
            break
    return ids[:target_count]


#uses movie ids to grab metadata
def fetch_movie_detail(movie_id):
    return _get(
        f"{BASE_URL}/movie/{movie_id}",
        params={"append_to_response": "credits,keywords"},
    )

#metadata get
def _get(url, params=None, max_retries=5):
    for attempt in range(max_retries):
        resp = requests.get(url, headers=HEADERS, params=params, timeout=20)
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 2))
            time.sleep(wait)
            continue
        if resp.status_code >= 500:
            time.sleep(2 ** attempt)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Failed after {max_retries} retries: {url}")



SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS movies (
    tmdb_id     INTEGER PRIMARY KEY,
    title       TEXT,
    overview    TEXT,
    genres      TEXT[],
    cast_names  TEXT[],
    keywords    TEXT[],
    raw_json    JSONB,
    embedding   VECTOR(384)  -- 384 = all-MiniLM-L6-v2 dimension; change if you swap models
);
"""

UPSERT_SQL = """
INSERT INTO movies (tmdb_id, title, overview, genres, cast_names, keywords, raw_json)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (tmdb_id) DO UPDATE SET
    title = EXCLUDED.title,
    overview = EXCLUDED.overview,
    genres = EXCLUDED.genres,
    cast_names = EXCLUDED.cast_names,
    keywords = EXCLUDED.keywords,
    raw_json = EXCLUDED.raw_json;
"""

UPDATE_EMBEDDING_SQL = """
UPDATE movies SET embedding = %s WHERE tmdb_id = %s;
"""


def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    register_vector(conn)
    return conn


def ensure_schema(conn):
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(SCHEMA_SQL)
    conn.commit()


def extract_fields(detail):
    title = detail.get("title")
    overview = detail.get("overview") or ""
    genres = [g["name"] for g in detail.get("genres", [])]
    cast_names = [c["name"] for c in detail.get("credits", {}).get("cast", [])[:10]]
    keywords = [k["name"] for k in detail.get("keywords", {}).get("keywords", [])]
    return title, overview, genres, cast_names, keywords


def save_movie(conn, movie_id, detail):
    title, overview, genres, cast_names, keywords = extract_fields(detail)
    with conn.cursor() as cur:
        cur.execute(
            UPSERT_SQL,
            (movie_id, title, overview, genres, cast_names, keywords, json.dumps(detail)),
        )
    conn.commit()
    return title, overview, genres, cast_names, keywords


def build_embedding_text(title, overview, genres, cast_names, keywords):
    return (
        f"Title: {title}\n"
        f"Overview: {overview}\n"
        f"Genres: {', '.join(genres)}\n"
        f"Cast: {', '.join(cast_names)}\n"
        f"Keywords: {', '.join(keywords)}"
    )


def main():
    from sentence_transformers import SentenceTransformer

    print("Loading embedding model")
    model = SentenceTransformer("all-MiniLM-L6-v2")  

    conn = get_conn()
    ensure_schema(conn)

    print("Discovering movie IDs")
    movie_ids = discover_movie_ids()

    for i, movie_id in enumerate(movie_ids, 1):
        try:
            detail = fetch_movie_detail(movie_id)
            title, overview, genres, cast_names, keywords = save_movie(conn, movie_id, detail)

            text = build_embedding_text(title, overview, genres, cast_names, keywords)
            vector = model.encode(text).tolist()

            with conn.cursor() as cur:
                cur.execute(UPDATE_EMBEDDING_SQL, (vector, movie_id))
            conn.commit()

            if i % 100 == 0:
                print(f"Processed {i}/{len(movie_ids)}")

        except Exception as e:
            print(f"Error on movie {movie_id}: {e}")
            continue

        time.sleep(0.02)  # gentle pacing; TMDB allows ~50 req/sec

    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()