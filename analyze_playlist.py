"""
Personal Music Taste Analysis
Pipeline: pandas (clean) -> SQLite (store + query with SQL) -> scipy (stats) -> matplotlib (visualize)
"""

import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

sns.set_style("whitegrid")

# ---------- 1. LOAD + CLEAN (pandas) ----------
df = pd.read_csv("my_playlist.csv")
df["artist_list"] = df["artists"].str.split(", ")
df["num_artists"] = df["artist_list"].apply(len)
df["is_collab"] = df["num_artists"] > 1
df["title_length"] = df["track_name"].str.len()
df["title_word_count"] = df["track_name"].str.split().apply(len)
df["title_is_lowercase"] = df["track_name"].apply(lambda x: x == x.lower())
df["title_is_uppercase"] = df["track_name"].apply(lambda x: x == x.upper() and x.isalpha() == False and any(c.isalpha() for c in x))

print(f"Loaded {len(df)} tracks.")

# ---------- 2. LOAD INTO SQLITE ----------
conn = sqlite3.connect("playlist.db")
df_to_sql = df.drop(columns=["artist_list"])  # can't store lists directly
df_to_sql.to_sql("tracks", conn, if_exists="replace", index=False)

# Also build an exploded artist table for per-artist SQL queries
exploded = df.explode("artist_list").rename(columns={"artist_list": "artist"})
exploded[["track_name", "artist"]].to_sql("track_artists", conn, if_exists="replace", index=False)

# ---------- 3. SQL QUERIES ----------
print("\n--- Top 10 most frequent artists (SQL) ---")
top_artists = pd.read_sql_query("""
    SELECT artist, COUNT(*) as track_count
    FROM track_artists
    GROUP BY artist
    ORDER BY track_count DESC
    LIMIT 10
""", conn)
print(top_artists)

print("\n--- Collab vs Solo breakdown (SQL) ---")
collab_breakdown = pd.read_sql_query("""
    SELECT is_collab, COUNT(*) as num_tracks,
           ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM tracks), 1) as pct
    FROM tracks
    GROUP BY is_collab
""", conn)
print(collab_breakdown)

print("\n--- Title style breakdown (SQL) ---")
title_style = pd.read_sql_query("""
    SELECT
        SUM(title_is_lowercase) as all_lowercase_titles,
        SUM(title_is_uppercase) as all_uppercase_titles,
        ROUND(AVG(title_word_count), 2) as avg_words_per_title,
        ROUND(AVG(title_length), 1) as avg_char_length
    FROM tracks
""", conn)
print(title_style)

print("\n--- Distribution of tracks per artist (SQL) ---")
artist_dist = pd.read_sql_query("""
    SELECT track_count, COUNT(*) as num_artists_with_this_many_tracks
    FROM (
        SELECT artist, COUNT(*) as track_count
        FROM track_artists
        GROUP BY artist
    )
    GROUP BY track_count
    ORDER BY track_count
""", conn)
print(artist_dist)

# ---------- 4. STATS ----------
# Is there a statistically meaningful skew in tracks-per-artist (i.e., a few artists dominate)?
artist_counts = pd.read_sql_query("""
    SELECT artist, COUNT(*) as track_count FROM track_artists GROUP BY artist
""", conn)["track_count"]

skewness = stats.skew(artist_counts)
print(f"\n--- Stats ---")
print(f"Number of unique artists: {len(artist_counts)}")
print(f"Skewness of tracks-per-artist distribution: {skewness:.2f}")
print("(Positive skew = a small number of artists account for a disproportionate share of tracks)")

# Chi-square-style check: is the collab/solo split significantly different from 50/50?
collab_count = df["is_collab"].sum()
solo_count = len(df) - collab_count
chi2, p_value = stats.chisquare([solo_count, collab_count], f_exp=[len(df)/2, len(df)/2])
print(f"Solo: {solo_count}, Collab: {collab_count}")
print(f"Chi-square test vs. 50/50 split: chi2={chi2:.2f}, p={p_value:.4f}")
if p_value < 0.05:
    print("-> Statistically significant preference for solo tracks over collabs.")
else:
    print("-> No statistically significant preference between solo and collab tracks.")

# ---------- 5. VISUALIZATIONS ----------
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Top artists bar chart
axes[0,0].barh(top_artists["artist"][::-1], top_artists["track_count"][::-1], color="#1DB954")
axes[0,0].set_title("Top 10 Most Frequent Artists in Playlist")
axes[0,0].set_xlabel("Track Count")

# Collab vs solo pie
axes[0,1].pie(collab_breakdown["num_tracks"], labels=["Solo" if not c else "Collab" for c in collab_breakdown["is_collab"]],
              autopct="%1.1f%%", colors=["#1DB954", "#191414"])
axes[0,1].set_title("Solo vs. Collaboration Tracks")

# Title word count distribution
axes[1,0].hist(df["title_word_count"], bins=range(1, df["title_word_count"].max()+2), color="#1DB954", edgecolor="black")
axes[1,0].set_title("Distribution of Track Title Word Count")
axes[1,0].set_xlabel("Number of Words in Title")
axes[1,0].set_ylabel("Number of Tracks")

# Tracks-per-artist distribution
axes[1,1].bar(artist_dist["track_count"], artist_dist["num_artists_with_this_many_tracks"], color="#1DB954", edgecolor="black")
axes[1,1].set_title("How Many Artists Have N Tracks in the Playlist")
axes[1,1].set_xlabel("Tracks by that Artist")
axes[1,1].set_ylabel("Number of Artists")

plt.tight_layout()
plt.savefig("playlist_analysis.png", dpi=150)
print("\nSaved visualization to playlist_analysis.png")

conn.close()
