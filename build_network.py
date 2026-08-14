"""
Interactive Artist Collaboration Network using PyVis (enhanced version).

Features:
- Node size = how many tracks that artist has in the playlist
- Node color = collaborator (teal) vs. solo-only artist (green)
- Edge thickness = number of times two artists collaborated
- Built-in search box to jump to any artist
- Click a node to highlight its direct connections
- Hover for track count / collab count details

Run locally:
    pip3 install pyvis pandas
    python3 build_network.py

Then open 'artist_network.html' in your browser.
"""

import pandas as pd
from pyvis.network import Network
from itertools import combinations

df = pd.read_csv("my_playlist.csv")
df["artist_list"] = df["artists"].str.split(", ")

exploded = df.explode("artist_list").rename(columns={"artist_list": "artist"})
track_counts = exploded["artist"].value_counts().to_dict()

edges = {}
for artist_list in df["artist_list"]:
    if len(artist_list) > 1:
        for a, b in combinations(sorted(artist_list), 2):
            edges[(a, b)] = edges.get((a, b), 0) + 1

collaborators = set()
for (a, b) in edges:
    collaborators.add(a)
    collaborators.add(b)

print(f"Artists: {len(track_counts)}")
print(f"Collaboration edges: {len(edges)}")

net = Network(
    height="850px",
    width="100%",
    bgcolor="#121212",
    font_color="white",
    notebook=False,
    select_menu=True,   # adds a dropdown to select/search nodes
    filter_menu=False,
)

# Include collaborators + top 20 solo artists so the graph stays readable but rich
included_artists = set(collaborators)
top_solo = sorted(track_counts.items(), key=lambda x: -x[1])[:20]
for artist, _ in top_solo:
    included_artists.add(artist)

max_count = max(track_counts.get(a, 1) for a in included_artists)

for artist in included_artists:
    count = track_counts.get(artist, 1)
    is_collaborator = artist in collaborators
    # Size scales with track count, exaggerated a bit for visual pop
    size = 15 + (count / max_count) * 55
    color = "#1ED760" if is_collaborator else "#535353"  # bright green vs muted gray
    net.add_node(
        artist,
        label=artist,
        size=size,
        title=f"<b>{artist}</b><br>{count} track(s) in playlist<br>{'Collaborator' if is_collaborator else 'Solo only'}",
        color=color,
        borderWidth=2,
        borderWidthSelected=4,
    )

for (a, b), weight in edges.items():
    net.add_edge(
        a, b,
        value=weight,
        width=1 + weight * 3,
        title=f"{a} & {b}: {weight} collab(s)",
        color="#1DB954",
    )

net.set_options("""
{
  "nodes": {
    "font": { "size": 16, "face": "arial", "strokeWidth": 2, "strokeColor": "#121212" },
    "shadow": { "enabled": true, "size": 10 }
  },
  "edges": {
    "smooth": { "type": "continuous" },
    "shadow": false,
    "color": { "opacity": 0.6 }
  },
  "physics": {
    "barnesHut": {
      "gravitationalConstant": -12000,
      "springLength": 180,
      "springConstant": 0.03,
      "damping": 0.5
    },
    "stabilization": { "iterations": 200 }
  },
  "interaction": {
    "hover": true,
    "hoverConnectedEdges": true,
    "selectConnectedEdges": true,
    "tooltipDelay": 100
  }
}
""")

net.write_html("artist_network.html")

# Add a title banner + legend directly into the HTML for extra polish
with open("artist_network.html", "r") as f:
    html = f.read()

banner = """
<div style="background:#121212; color:white; font-family:arial; padding:16px 24px; border-bottom:2px solid #1DB954;">
  <h1 style="margin:0; font-size:22px;">🎧 My Music Taste — Artist Collaboration Network</h1>
  <p style="margin:6px 0 0; font-size:14px; color:#b3b3b3;">
    Node size = tracks in playlist &nbsp;|&nbsp;
    <span style="color:#1ED760;">●</span> Collaborator &nbsp;
    <span style="color:#535353;">●</span> Solo-only &nbsp;|&nbsp;
    Click a node to highlight its connections. Use the search box to jump to an artist.
  </p>
</div>
"""
html = html.replace("<body>", f"<body>{banner}", 1)

with open("artist_network.html", "w") as f:
    f.write(html)

print("Saved enhanced interactive graph to artist_network.html -- open it in your browser!")
