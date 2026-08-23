from fastapi import FastAPI, UploadFile
import data_pull
import numpy as np
import letterboxd
from pydantic import BaseModel
from contextlib import asynccontextmanager
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
load_dotenv()

model = SentenceTransformer("all-MiniLM-L6-v2")

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = model

    yield
    
app = FastAPI(lifespan = lifespan)
class RecommendRequest(BaseModel):
    query: str
    limit: int = 10
    taste_vector: list[float] | None = None

class MovieResult(BaseModel):
    tmdb_id: int
    title: str
    distance: float



conn = data_pull.get_conn()
cur = conn.cursor() 
    
@app.post('/recommend')
def recommend(request: RecommendRequest):
    #creating query vector from text
    query_vector = model.encode(request.query).tolist()

    alpha = 0.5

    if request.taste_vector:
        taste_vector = np.array(request.taste_vector)
        blended = alpha * taste_vector + (1-alpha) * query_vector
    else:
        blended = query_vector
    combined_vector = blended.tolist()
    #using cosine similarity SQL with querry vector as param
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
    return [
        MovieResult(tmdb_id=row[0], title=row[1], distance=row[2])
        for row in rows
    ]
    
@app.post('/similar/{movie_id}')
def find_similar(movie_id : int, limit:int = 10):
    #using cosine similarity SQL with querry vector as param


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

    return [MovieResult(tmdb_id=row[0], title=row[1], distance=row[2]) for row in rows] 

@app.post("/upload_file/")
async def upload_file(file: UploadFile):
    taste_vector = letterboxd.compute_taste_vector(file.file, conn=conn)
    return f'taste vector: {taste_vector.tolist()}'
