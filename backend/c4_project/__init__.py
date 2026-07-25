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
"""
