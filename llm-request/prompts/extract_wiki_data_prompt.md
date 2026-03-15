## Task

Extract structured data for a **single conference payload** from `data-assembly/json/final_data.json`.

The input object always represents one conference and follows this pre-formatted shape:

```json
{
	"name": "Conference Name",
	"member_schools": "...",
	"conference_history": "...",
	"timeline_map": "..."
}
```

Notes on structure:

1. `member_schools` is a single extracted text blob (or `null`) from source member-schools sections.
2. `conference_history` is a single extracted text blob (or `null`) from source history sections.
3. `timeline_map` is optional and, when present, is a text blob (or `null`) containing timeline markup/text.
4. `name` may be null in some inputs; if so, use the provided conference context/key if available.

Your job is to extract only:

1. University name
2. University Wikipedia href
3. University city
4. University state
5. Conference name
6. Conference Wikipedia href
7. Conference start year and end year (if known)
8. Primary membership period in the conference (start year, end year if known)

Do not extract sports-level, division-level, or association-level records.

## Scope Rules

1. Only output rows that represent a university's **primary** membership in the current conference.
2. Ignore sport-only affiliate/associate memberships.
3. If `timeline_map` exists and is non-null, use it as a high-priority source for years.
4. Use `member_schools` and `conference_history` text to resolve names and fill missing years/locations.
5. Do not invent facts. If a value is not present or cannot be inferred with high confidence, use `null`.
6. Prefer extracting university identity from wiki links (`[[Page|Label]]`, `[[Page]]`, or HTML links) and preserve href when available.
7. Extract conference identity from `name` and any available conference link context in the source text; include conference lifecycle years when available.

## Primary Membership Guidance

When reading timeline maps, keep only entries that indicate full or primary conference membership.

1. Include entries marked as full members (for example, labels equivalent to all-sports membership, including all-sports-except-football if it is the institution's primary conference membership context).
2. Exclude entries marked as associate/affiliate/sport-only.
3. Exclude bars that only indicate membership in other conferences after departure.

## Normalization and Naming Rules

1. Use canonical university names when an alias is shown (for example, `[[University Name|Alias]]` should map to `University Name` if clear).
2. Extract `university_wikipedia_href` whenever possible from source links.
3. Standardize `university_wikipedia_href` to a relative Wikipedia path format when possible (for example, `/wiki/University_of_Chicago`).
4. Keep conference name from `name` when present; otherwise use the conference context/key supplied with the payload.
5. Extract `conference_wikipedia_href` whenever possible and standardize to relative Wikipedia path format when possible (for example, `/wiki/Atlantic_Coast_Conference`).
6. City and state should represent the university's campus location in current/common usage when present in source text.
7. Keep years as integers.
8. Use `null` for unknown `start_year` or `end_year` when the source is ambiguous or unavailable.
9. If multiple universities have similar names, `university_wikipedia_href` is the primary disambiguator.

## Output Format

Return **only valid JSON** (no prose, no markdown, no code fences) using this exact top-level structure:

```json
{
	"universities": {
		"columns": ["university_name", "university_wikipedia_href", "city", "state"],
		"rows": []
	},
	"conferences": {
		"columns": ["conference_name", "conference_wikipedia_href", "conference_start_year", "conference_end_year"],
		"rows": []
	},
	"university_conference_memberships": {
		"columns": ["university_wikipedia_href", "conference_name", "start_year", "end_year"],
		"rows": []
	}
}
```

## Output Constraints

1. Include exactly one conference row for the current conference.
2. `universities.rows` should contain one row per distinct university referenced by included primary-membership rows.
3. `university_conference_memberships.rows` may contain multiple periods for the same university if it left and rejoined.
4. Do not output exact duplicate membership rows (`university_wikipedia_href`, `conference_name`, `start_year`, `end_year`).
5. Ensure all membership rows reference a university present in `universities.rows` by `university_wikipedia_href`.
6. `university_wikipedia_href` should be non-null whenever a link is present in source data.
7. Do not split continuous primary membership into multiple rows just because intermediate narrative context changes (for example, temporary sport-specific exceptions). If there is no true break in primary conference membership, return one continuous period.
8. `conferences.rows` should contain a single row with known conference metadata; set unknown conference years to `null`.
9. `conference_wikipedia_href` should be non-null whenever a conference link is present or can be derived with high confidence.

## Quality Checks Before Returning

1. Confirm JSON parses.
2. Confirm required keys and column lists match exactly.
3. Confirm each membership row has non-null `university_wikipedia_href` and `conference_name`. Keep `start_year` or `end_year` as `null` only when the source does not support a high-confidence year.
4. Confirm no sport-only/associate-only memberships are included.
5. Confirm `conferences.rows` has exactly one row with conference name populated.
