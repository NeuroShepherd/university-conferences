

import json


with open("conference_section_headers.json", "r") as f:
    json_data = json.load(f)


# for the h2 headers, count how many times each unique header appears across all conferences

h2_counts: dict[str, int] = {}
conference_counter = 0
for conference, sections in json_data.items():
    conference_counter += 1
    for section in sections:
        h2_text = section["h2"]
        h2_counts[h2_text] = h2_counts.get(h2_text, 0) + 1

# sort the h2 headers by count in descending order
sorted_h2_counts = sorted(h2_counts.items(), key=lambda item: item[1], reverse=True)

print("H2 Headers by Frequency:")
for h2_text, count in sorted_h2_counts:
    print(f"{h2_text}: {count}")

print("==================")
print(f"Number of conferences analyzed: {conference_counter}")
print("==================")



# 104/106 conferences have a h2 section for History
# 95/106 conferences have a h2 section for Member Schools
# 84/106 conferences have a h2 section for Sports

# let's extract only the h3 headers under these 3 categories and count their frequencies as well

h3_counts: dict[str, int] = {}
for conference, sections in json_data.items():
    for section in sections:
        h2_text = section["h2"]
        if h2_text in ["History", "Member Schools", "Sports"]:
            h3_headers = section.get("h3", [])
            for h3_text in h3_headers:
                h3_counts[h3_text] = h3_counts.get(h3_text, 0) + 1


# sort the h3 headers by count in descending order
sorted_h3_counts = sorted(h3_counts.items(), key=lambda item: item[1], reverse=True)


print("H3 Headers under History, Member Schools, and Sports by Frequency:")
print("==================")
for h3_text, count in sorted_h3_counts:
    print(f"{h3_text}: {count}")




member_h2_variants = set(
    [
        "Member Schools",
        "Member schools",
        "Member universities",
        "Members",
        "Member institutions",
    ]
)

# identify conferences without an h2 header for Member Schools
conferences_without_member_schools_field = []
for conference, sections in json_data.items():
    has_member_schools = any(section["h2"] in member_h2_variants for section in sections)
    if not has_member_schools:
        conferences_without_member_schools_field.append(conference)

print("==================")
print("Conferences without a Member Schools section:")
for conference in conferences_without_member_schools_field:
    print(conference)