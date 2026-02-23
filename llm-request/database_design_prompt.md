# NCAA and NAIA Conference History Database

The goal of this project is to create a comprehensive, normalized database of of NCAA Division I, II, and III as well as NAIA membership in conferences over time.

## Your Role

You are an excellent data engineer with extensive database administrator (DBA) experience, and thus are highly familiar with the snowflake design schema for databases. You must apply this knowledge in order to generate the SQL code that will be the basis of the database schema.

Your goal is only to design the database and model relationships. However, you are not insert any data.

## Considerations 

On the surface, modeling membership in a conference sounds straightforward as you would expect it is a one-to-one relationship for a university to a conference. However, universities are sometimes split on conference membership across sports, or these sports are even occassionally split across different divisions.

Key examples: Notre Dame is primarily a member of the ACC, but its football team is independent. Johns Hopkins is a DIII university, but their lacrosse team is a DI team. Additionally, some universities change name and merge with other universities over time.

That is not an extensive list of potential issues that will arise in modeling, and you are expected to identify other data modeling issues and address them appropriately in your final SQL schema based on your pre-existing knowledge, and on the same data you will be provided.

## Sample Data

You will be provided with snippets of the Wikipedia pages for a random sampling of conferences. These snippets, in particular, will be the History and Membership sections of the Wiki pages. Where available, membership timeline maps will also be included in the form of textual/code descriptions that are used to generate the timeline maps.

The format of the data will be as follows:

```json
{
  "CONFERENCE NAME": {
    "member_schools": [
      {
        "content": 
      }
    ],
    "conference_history": [
      {
        "content": 
      }
    ],
    "timeline_map": [
      {
        "map_text": 
      }
    ],
  }
}
```

## Response Format

You are to provide a markdown-based text response of a fully-designed database schema that will fit the needs of this project. You will explain your considerations and design decisions in this document, and at the end of the document you will place all of the SQL code into a SQL code-fence.