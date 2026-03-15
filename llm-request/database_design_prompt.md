# University Primary Conference Timeline Database

The goal of this project is to design a normalized database that captures only the following:

1. University name
2. University city
3. University state
4. Primary conference memberships over time, with start year and end year (if available)

## Your Role

You are an experienced data engineer and DBA. Design the schema and relationships only. Do not include INSERT statements or load scripts.

## Scope Constraints

Keep the design tightly scoped. Do not model extra domains unless absolutely required to support the core timeline requirement.

Include only what is necessary for:

1. Uniquely identifying universities
2. Storing current university location (city, state)
3. Storing conference entities
4. Storing each university's primary conference membership periods (start year, end year nullable)

Do not include:

1. Sports-specific memberships
2. Divisions or associations
3. Nicknames, colors, affiliations, enrollment, coordinates, or other metadata
4. Non-primary conference relationships

## Data Rules

Design for these minimum rules:

1. A university can have many primary conference periods over time.
2. A conference can have many universities over time.
3. Membership periods should allow open-ended rows (end year is NULL for ongoing membership).
4. Prevent exact duplicate membership timeline rows for the same university and conference.

## Sample Data

You will receive conference-page snippets (for example, membership and history sections) in this format:

```json
{
  "CONFERENCE NAME": {
    "member_schools": [
      {
        "content": "..."
      }
    ],
    "conference_history": [
      {
        "content": "..."
      }
    ],
    "timeline_map": [
      {
        "map_text": "..."
      }
    ]
  }
}
```

## Response Format

Provide a markdown response that includes:

1. A concise explanation of design decisions focused only on the scoped requirements above.
2. A single SQL code block containing the complete schema DDL.

Do not include anything outside that scope unless required for relational integrity.