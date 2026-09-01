from c4parser.static_facts.backend import extract_python

SAMPLE = '''
import os
import stripe
from apps.subscriptions import manager


def create_intent(amount):
    """Creates a Stripe payment intent for the given amount."""
    return stripe.PaymentIntent.create(amount=amount)


class PaymentService:
    """Orchestrates payment intent creation and confirmation."""
    pass
'''


def test_extract_python_imports():
    imports, _ = extract_python("sample.py", SAMPLE)
    assert "os" in imports
    assert "stripe" in imports
    assert "apps.subscriptions" in imports


def test_extract_python_defines_function():
    _, defines = extract_python("sample.py", SAMPLE)
    func = next(d for d in defines if d.name == "create_intent")
    assert func.kind == "function"
    assert func.docstring == "Creates a Stripe payment intent for the given amount."


def test_extract_python_defines_class():
    _, defines = extract_python("sample.py", SAMPLE)
    cls = next(d for d in defines if d.name == "PaymentService")
    assert cls.kind == "class"
    assert cls.docstring == "Orchestrates payment intent creation and confirmation."
