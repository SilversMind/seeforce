"""
@c1:system
name: SeeForce
description: |
  - Turns C4 annotations in a codebase's source files into an interactive architecture diagram
  - Shows what a pull request changes in that architecture
  - Answers "what does this codebase actually do, and how do its pieces talk to each other?"
short_desc: Turns C4 annotations in your code into an interactive architecture diagram
"""

"""
@c1:person
name: Developer
description: |
  - Annotates their codebase and scans it into a workspace
  - Imports it into SeeForce, then explores and enriches the diagram
  - Opens share links to other people's diagrams, read-only
short_desc: Maps a codebase, then explores and enriches the diagram
uses:
- SeeForce: "signs in, imports workspaces, explores and edits diagrams, opens share links"
  technology: HTTPS
"""

"""
@c2:container
name: Backend
system: SeeForce
technology: Python Django
description: |
  - Serves the REST API for:
    - Project CRUD
    - Node/edge overlays
    - Lexicon entries
    - Share links
    - Pull request architecture deltas
    - GitHub:
      - Import
      - Sync
      - Link
  - Persists data in the Database
short_desc: Serves the REST API behind the app and stores every project
uses:
    - Database: "Reads and writes architecture graph data via Django ORM"
    - GitHub: "signs users in with OAuth and fetches repo content with installation tokens"
      technology: HTTPS
    - Annotation Parser: "parses and builds workspace.json when scanning a repo locally via manage.py scan"
"""
