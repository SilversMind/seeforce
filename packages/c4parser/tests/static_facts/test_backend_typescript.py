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


EXPORTED = '''
/** Charges the customer's saved card. */
export function charge(amount) {}

/** Long-lived connection pool wrapper. */
export class Pool {}

/**
 * Refunds a previous charge.
 * Falls back to a partial refund when the balance is short.
 */
export async function refund(chargeId) {}

/** Entry point for the worker process. */
export default function main() {}
'''


def test_exported_function_keeps_docstring():
    """`export function f() {}` wraps the declaration in an export_statement, so the
    comment is the *parent's* prev_sibling, not the declaration's."""
    _, defines = extract_typescript("sample.ts", EXPORTED)
    fn = next(d for d in defines if d.name == "charge")
    assert fn.docstring == "Charges the customer's saved card."


def test_exported_class_keeps_docstring():
    _, defines = extract_typescript("sample.ts", EXPORTED)
    cls = next(d for d in defines if d.name == "Pool")
    assert cls.kind == "class"
    assert cls.docstring == "Long-lived connection pool wrapper."


def test_export_default_function_keeps_docstring():
    _, defines = extract_typescript("sample.ts", EXPORTED)
    fn = next(d for d in defines if d.name == "main")
    assert fn.docstring == "Entry point for the worker process."


def test_multiline_jsdoc_is_flattened_without_interior_stars():
    """Multi-line JSDoc must lose its per-line `*` gutter and collapse to one line."""
    _, defines = extract_typescript("sample.ts", EXPORTED)
    fn = next(d for d in defines if d.name == "refund")
    assert fn.docstring == (
        "Refunds a previous charge. "
        "Falls back to a partial refund when the balance is short."
    )
    assert "*" not in fn.docstring
    assert "\n" not in fn.docstring


def test_unexported_declaration_without_comment_has_empty_docstring():
    _, defines = extract_typescript("sample.ts", "export function bare() {}\n")
    assert defines[0].docstring == ""
