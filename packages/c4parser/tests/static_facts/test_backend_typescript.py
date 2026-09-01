from c4parser.static_facts.backend import extract_typescript

SAMPLE = '''
import axios from "axios";
import { manager } from "./subscriptions/manager";

/** Creates a Stripe payment intent for the given amount. */
function createIntent(amount) {
  return axios.post("/charge", { amount });
}

/** Orchestrates payment intent creation and confirmation. */
class PaymentService {}
'''


def test_extract_typescript_imports():
    imports, _ = extract_typescript("sample.ts", SAMPLE)
    assert "axios" in imports
    assert "./subscriptions/manager" in imports


def test_extract_typescript_defines_function():
    _, defines = extract_typescript("sample.ts", SAMPLE)
    func = next(d for d in defines if d.name == "createIntent")
    assert func.kind == "function"
    assert func.docstring == "Creates a Stripe payment intent for the given amount."


def test_extract_typescript_defines_class():
    _, defines = extract_typescript("sample.ts", SAMPLE)
    cls = next(d for d in defines if d.name == "PaymentService")
    assert cls.kind == "class"
    assert cls.docstring == "Orchestrates payment intent creation and confirmation."
