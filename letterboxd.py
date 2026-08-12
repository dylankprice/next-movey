import pandas as pd
import rapidfuzz
import data_pull 

# Date,Name,Year,Letterboxd URI,Rating

path = "./test_data/ratings.csv"
df = pd.read_csv(path)

#filters to only include movies with a rating of 4.0 or higher
filterdf = df[df["Rating"] >= 4.0]

#print(len(filterdf))
#print(filterdf[["Name", "Year", "Rating"]].head(10))

conn = data_pull.get_conn() #connection to tmdb database


movies_df = pd.read_sql("SELECT tmdb_id, title FROM movies", conn)


ratings = {}
for my_index, my_row in filterdf.iterrows():
    best_score = 0
    best_match = None
    for tmdb_index, tmdb_row in movies_df.iterrows():   
        if rapidfuzz.fuzz.ratio(tmdb_row["title"], my_row["Name"]) > best_score:
            best_score = rapidfuzz.fuzz.ratio(tmdb_row["title"], my_row["Name"])

            best_match = tmdb_row
    if best_score >= 85:
        ratings[best_match["title"]] = my_row["Rating"]


#print(len(ratings))