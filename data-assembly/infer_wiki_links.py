
import pandas as pd

with open("data-assembly/conferences.csv", "r") as f:
    conferences = pd.read_csv(f)



missing = conferences["wikipedia_url"].isna() | conferences["wikipedia_url"].str.strip().eq("")

# Create temporary slug from name (does NOT modify conferences["name"])
name_slug = (
    conferences.loc[missing, "name"]
    .str.strip()
    .str.replace(r"\s+", "_", regex=True)
)

# Fill only missing wikipedia_url values
conferences.loc[missing, "wikipedia_url"] = "https://en.wikipedia.org/wiki/" + name_slug

conferences.to_csv("conferences.csv", index=False)