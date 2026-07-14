class OrderService:
    """
    @c3:component
    name: Order Service
    container: API Backend
    technology: Django
    uses:
      - Payment Service
      - kafka:order-events
    """

class PaymentService:
    """
    @c3:component
    name: Payment Service
    container: API Backend
    technology: Django
    """
