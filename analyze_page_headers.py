

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


# count the number of characters within the sections delineated by the member_h2_variants headers, 
# to get a sense of how much content is typically included in the Member Schools section
# i have to determine what is a section by first identifying the h2 header that matches one of the 
# member_h2_variants, and then counting the characters in the content until the next h2 header

member_schools_character_counts: list[int] = []
for conference, sections in json_data.items():
    for i, section in enumerate(sections):
        h2_text = section["h2"]
        if h2_text in member_h2_variants:
            # this is the start of the Member Schools section
            # we will count characters until the next h2 header or the end of the sections list
            character_count = 0
            for j in range(i + 1, len(sections)):
                next_h2_text = sections[j]["h2"]
                if next_h2_text in member_h2_variants:
                    break  # stop counting when we reach the next Member Schools section
                # count characters in this section's h3 headers and any content (if available)
                h3_headers = section.get("h3", [])
                character_count += sum(len(h3) for h3 in h3_headers)
                # if there was additional content under this section, we would count it here as well
            member_schools_character_counts.append(character_count)

if member_schools_character_counts:
    average_characters = sum(member_schools_character_counts) / len(member_schools_character_counts)
    print("==================")
    print(f"Average number of characters in Member Schools sections: {average_characters:.2f}")
else:
    print("==================")
    print("No Member Schools sections found to analyze character counts.")

# print the count for each conference that has a Member Schools section
print("==================")
print("Character counts for Member Schools sections by conference:")
for conference, sections in json_data.items():
    for i, section in enumerate(sections):
        h2_text = section["h2"]
        if h2_text in member_h2_variants:
            character_count = 0
            for j in range(i + 1, len(sections)):
                next_h2_text = sections[j]["h2"]
                if next_h2_text in member_h2_variants:
                    break
                h3_headers = section.get("h3", [])
                character_count += sum(len(h3) for h3 in h3_headers)
            print(f"{conference}: {character_count} characters")

            