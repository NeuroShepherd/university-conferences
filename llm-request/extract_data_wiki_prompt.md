# Project Goals

The aim of this project is to extract NCAA and NAIA conference membership information from Wikipedia pages, and place that information into a structured, queryable format. A database design along with detailed notes on the tables, their structure, and how they fit together have been provided.

Your objective is to extract information for each university conference member (both current and former) from the provided Wiki text, and provide PostgresQL SQL commands to insert the appropriate information into the tables outlined in the database schema.

It is far more acceptable to not insert data than to insert incorrect data. That is, accuracy of your answers must be prioritized over the quantity or completeness of your answers.

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

I expect your response to formatted in JSON with the following fields:

* a `notes` field for any useful information or points of ambiguity where you believe I should be provided with information
* a `commands` field where you will include the SQL commands for inserting the appropriate data.
* a `text_description` field which will briefly describe the changes proposed in `commands`, but in a human-readable format. This information will later be used for cross-checking results across conference pages so you must write an accurate description.

```json
{
    "notes": [],
    "commands": [],
    "text_description": [],
}
```