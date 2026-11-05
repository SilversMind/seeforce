"""
@c3:component
name: Feature Catalogue
container: Annotation Parser
technology: Python
description: Loads, validates and serialises the feature catalogue — the list of intentions a repo serves, grouped into categories, each naming the set of model elements it touches. Resolves every element the catalogue names against a workspace snapshot flattened by Delta Reporter, so the catalogue stays a reading of the model and can assert no structure of its own. Refuses to load rather than degrade — an unknown schema version, an element that resolves to nothing, or two model elements colliding on one path all raise instead of yielding a partial catalogue. Also owns the append-only merge that keeps a human-reviewed feature byte-identical across regenerations.
short_desc: Loads and validates the feature catalogue against a workspace snapshot
"""
