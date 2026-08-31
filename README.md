# next-movey

A personal movie recommendation tool I built to learn FastAPI, Postgres/pgvector, and basic vector search.

## What it does

You describe what you're in the mood to watch in natural language and it searches a database of ~3,000 movies pulled from TMDB, using sentence embeddings and cosine similarity to find the closest matches. Main feature is you can upload your Letterboxd ratings export to build "taste vector," which gets blended into search results.

## How it works

- **Data:** `data_pull.py` pulls movie metadata from TMDB and generates a 384-dimension embedding for each movie (title, overview, genres, cast, keywords) using `sentence-transformers`, storing everything in Postgres with the `pgvector` extension.
- **Search:** the FastAPI backend embeds your search query the same way and finds nearest neighbors by vector distance.
- **Personalization:** `letterboxd.py` fuzzy-matches your Letterboxd ratings against the database, then computes a weighted average embedding across your highly-rated movies — that becomes your "taste vector," blended 50/50 with whatever you search for.
- **Frontend:** a small React app for searching, browsing results, and uploading the Letterboxd file.

## Known Improvements

- Only has popular movies, top 3k, due to project size and scale
- Structure is only built to work for that amount, scalability is weak
- No persistence between sessions, single time use and repeated upload
- Only local deployment
