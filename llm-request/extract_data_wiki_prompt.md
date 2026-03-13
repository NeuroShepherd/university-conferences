# Project Goals

The aim of this project is to extract NCAA and NAIA conference membership information from Wikipedia pages, and place that information into a structured, queryable format. A database design along with detailed notes on the tables, their structure, and how they fit together have been provided.

Your objective is to extract information for each university conference member (both current and former) from the provided Wiki text, and provide structured text output that maps to the tables and columns in the database schema.

It is far more acceptable to not insert data than to insert incorrect data. That is, accuracy of your answers must be prioritized over the quantity or completeness of your answers.

Do not output SQL.

# Prompt Format


```json
{
    "member_schools": [
        "content": "HTML description of the conference",
    ],
    "conference_history": [
        "content": "HTML description of the conference history",
    ],
    "timeline_map": [
        "map_text": "HTML of Wikipedia's timeline chart markup language",
    ]
}
```

# Response Format

Return one JSON object in plaintext with table names as top-level keys.

Each table key must contain:

1. "columns": ordered list of column names
2. "rows": array of row arrays in the same order as "columns" (compact mode)
3. "notes": brief table-specific caveats (optional)

Preferred mode: compact mode (rows as arrays) to minimize token usage.

Fallback mode: readable mode (rows as objects) is allowed only if explicitly requested.

Use null for unknown values. Do not guess values.

Use only values grounded in the provided input text.

If no rows are found for a table, include the table with an empty rows array.

Do not include explanations outside the JSON.

Use this exact compact shape:

```json
{
    "dim_associations": {
        "columns": ["association_name"],
        "rows": [
            ["NCAA"]
        ]
    },
    "dim_divisions": {
        "columns": ["division_name", "association_name"],
        "rows": [
            ["Division I", "NCAA"]
        ]
    },
    "dim_states": {
        "columns": ["state_name", "state_abbreviation"],
        "rows": []
    },
    "dim_cities": {
        "columns": ["city_name", "state_abbreviation"],
        "rows": []
    },
    "dim_affiliations": {
        "columns": ["affiliation_type", "denomination"],
        "rows": []
    },
    "dim_sports": {
        "columns": ["sport_name_normalized"],
        "rows": []
    },
    "dim_membership_types": {
        "columns": ["type_name", "description"],
        "rows": []
    },
    "dim_universities": {
        "columns": [
            "current_university_name",
            "founded_year",
            "current_enrollment",
            "current_colors",
            "main_campus_city_name",
            "main_campus_state_abbreviation",
            "main_campus_latitude",
            "main_campus_longitude",
            "current_affiliation_type",
            "current_denomination"
        ],
        "rows": []
    },
    "dim_conferences": {
        "columns": ["current_conference_name", "short_name", "founded_year"],
        "rows": []
    },
    "bridge_university_names": {
        "columns": ["current_university_name", "university_name", "start_year", "end_year"],
        "rows": []
    },
    "bridge_university_nicknames": {
        "columns": ["current_university_name", "nickname", "start_year", "end_year", "sport_name_normalized"],
        "rows": []
    },
    "bridge_university_sports": {
        "columns": [
            "current_university_name",
            "sport_name_normalized",
            "division_name",
            "association_name",
            "start_year",
            "end_year",
            "is_varsity",
            "sport_notes"
        ],
        "rows": []
    },
    "bridge_conference_names": {
        "columns": ["current_conference_name", "conference_name", "start_year", "end_year"],
        "rows": []
    },
    "bridge_conference_divisions": {
        "columns": ["current_conference_name", "division_name", "association_name", "start_year", "end_year"],
        "rows": []
    },
    "fact_membership": {
        "columns": [
            "current_university_name",
            "current_conference_name",
            "membership_type_name",
            "joined_year",
            "left_year",
            "sport_name_normalized",
            "division_name",
            "association_name",
            "primary_conference_for_sport_name",
            "previous_conference_name",
            "next_conference_name",
            "reason_for_change",
            "membership_notes"
        ],
        "rows": []
    }
}
```

Readable fallback example (only if requested):

```json
{
    "dim_associations": {
        "columns": ["association_name"],
        "rows": [
            {"association_name": "NCAA"}
        ]
    }
}
```

Output rules:

1. Return one valid JSON object only.
2. Do not output SQL, markdown tables, or prose.
3. Keep records deduplicated within each table.
4. Preserve timeline history where available.
5. Favor omission over uncertain inference.
6. In compact mode, every row array length must exactly match the columns length.
