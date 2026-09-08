"""
@c1:system
name: SeeForce
description: Turns C4 annotations embedded in a codebase's own source files into an interactive architecture diagram. Used to answer "what does this codebase actually do, and how do its pieces talk to each other?"
"""

"""
@c2:container
name: Backend
system: SeeForce
technology: Python Django
description: Serves the REST API for project CRUD, node/edge overlays, lexicon entries, sharing, and GitHub import/sync/link. Persists everything to the Database and delegates codebase parsing to Annotation Parser — it does not parse source files itself.
uses:
    - Database: "Reads and writes architecture graph data via Django ORM"
    - GitHub: "Delegates user authentication via GitHub OAuth 2.0 (django-allauth); also mints short-lived GitHub App installation tokens (JWT-signed) to fetch repo content for import/sync"
      technology: HTTPS
    - Annotation Parser: "parses and builds workspace.json when scanning a repo locally via manage.py scan"
"""
