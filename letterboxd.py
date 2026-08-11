import pandas as pd

# Date,Name,Year,Letterboxd URI,Rating

path = "./test_data/ratings.csv"
df = pd.read_csv(path)

filterdf = df[df["Rating"] >= 4.0]

print(len(filterdf))