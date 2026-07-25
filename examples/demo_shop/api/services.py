"""
@c3:component
name: Order Service
container: API Backend
technology: Python
description: Handles order lifecycle
uses:
  - Payment Service
  - Database
"""

"""
@c3:component
name: Payment Service
container: API Backend
technology: Python
description: Charges customers
uses:
  - Stripe
"""


"""
@c3:component
name: Catalog Service
container: API Backend
technology: Python
description: Product catalog queries
uses:
  - Database
"""
