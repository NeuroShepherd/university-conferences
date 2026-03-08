
# Data Assembly Procedure

This folder is admittedly a bit messy as it followed an organic development process (i.e. I never knew what I was going to find next). However, I'll try to clarify the structure as seen on GitHub.

First, create a folder called `json` within this directory if it does not already exist.

```bash
mkdir json
```

I explicitly ignored this folder in git because:

1. The output json files were generally too large
2. The files can be reproduced with the scripts in this folder. (Not entirely true given that Wikipedia pages may be updated, and the LLMs will always give slightly different output. But for the purposes of this project, this is reproducible enough)

The following describes the execution order of the scripts.


## Overall Order of Scripts

1. `query_wikipedia_api.py` queries the API for the conference pages
2. `extract_section_headers.py` extracts the h2 and h3 headers across all pages
3. `analyze_page_headers.py` counts up the common h2 and h3 headers across conference pages
4. `analyze_page_content.py` is not very well named, and actually extracts and saves the History and Member Universities sections from the Wiki pages
5. `identify_timeline_maps.py` finds which conference pages have a dedicated "Membership timeline" section which use a particular mapping/coding system that lends itself well to being an accurate record for a school's conference history. This script gets the links to this maps.
6. `query_membership_maps.py` queries the Wiki API for these pages, and saves the response.
7. `add_timeline_maps_to_other_data.py` combines the regular History and Member Universities pages with the separate, explicit Membership timeline information. Note: while the Membership Timelines typically appear as an h3 section within the h2 Members sections, what is displayed is an image rather than parseable text so adding in this information is *not* redundant.
8. `sanity_check_final_data.py` checks that the `final_data.json` file contains conferences as expected.




## Unused Scripts


1. `infer_wiki_links.py` creates its best guess at the Wikipedia links from the conference names in `conferences.csv`. However, creating these links was ultimately not needed for scraping or querying the Wiki API.