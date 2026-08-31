from urllib3 import request

from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from psycopg2 import pool
import data_pull
import numpy as np
import letterboxd
from pydantic import BaseModel
from contextlib import asynccontextmanager
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector

load_dotenv()

model = SentenceTransformer("all-MiniLM-L6-v2")

# --- connection pool instead of one shared conn/cur ---
db_pool = pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=os.environ["DATABASE_URL"],
)

def get_pooled_conn():
    conn = db_pool.getconn()
    register_vector(conn)  # safe to call every checkout
    return conn

def release_pooled_conn(conn):
    db_pool.putconn(conn)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = model
    yield
    db_pool.closeall()

app = FastAPI(lifespan=lifespan)

# Allow the local React dev server to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # vite's default dev port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RecommendRequest(BaseModel):
    query: str
    limit: int = 10
    taste_vector: list[float] | None = None

class MovieResult(BaseModel):
    tmdb_id: int
    title: str
    distance: float


@app.post('/recommend')
def recommend(request: RecommendRequest):
    query_vector = model.encode(request.query)
    alpha = 0.5

    if request.taste_vector is not None:
        taste_vector = np.array(request.taste_vector)
        blended = alpha * query_vector + (1 - alpha) * taste_vector
    else:
        blended = query_vector
    combined_vector = blended.tolist()

    conn = get_pooled_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT tmdb_id, title,
            embedding <=> %s::vector AS distance
            FROM movies
            ORDER BY distance ASC
            LIMIT %s;
            """,
            (combined_vector, request.limit)
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        release_pooled_conn(conn)

    return [
        MovieResult(tmdb_id=row[0], title=row[1], distance=row[2])
        for row in rows
    ]


@app.post('/similar/{movie_id}')
def find_similar(movie_id: int, limit: int = 10):
    conn = get_pooled_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT tmdb_id, title,
            embedding <=> (SELECT embedding FROM movies WHERE tmdb_id = %s) AS distance
            FROM movies
            WHERE tmdb_id != %s
            ORDER BY distance ASC
            LIMIT %s;
            """,
            (movie_id, movie_id, limit)
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        release_pooled_conn(conn)

    return [MovieResult(tmdb_id=row[0], title=row[1], distance=row[2]) for row in rows]


@app.post("/upload_file/")
async def upload_file(file: UploadFile):
    conn = get_pooled_conn()
    try:
        taste_vector = letterboxd.compute_taste_vector(file.file, conn=conn)
    finally:
        release_pooled_conn(conn)
    return {"taste_vector": taste_vector.tolist()}