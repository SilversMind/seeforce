"""
@c1:system
name: SeeForce
description: Architecture visualization tool
"""

"""
@c2:container
name: Backend
system: SeeForce
technology: Python Django
description: Parse codebase, generate architecture data
uses:
    - Database: "Reads and writes architecture graph data via Django ORM"
    - GitHub: "Delegates user authentication via GitHub OAuth 2.0 (django-allauth)"
      technology: HTTPS
    - Annotation Parser: "parses and builds workspace.json when scanning a repo locally via manage.py scan"
"""
