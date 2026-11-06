# Building a SeeForce feature catalogue

You are turning a repo's C4 annotations into a catalogue of the **intentions** the repo serves —
the things it lets someone do — written to `.seeforce/features.json`.

The model already exists in `.seeforce/workspace.json`. You are not inventing architecture. You are
naming what the architecture is *for*, and pointing each name at the elements that serve it.

## The rules that are easy to get wrong

**One feature is one intention.** A name containing a conjunction is two features. "Import and
share a project" is `Import a project` and `Share a project`. Split it, even when the code path is
shared — the reader is looking for an intention, not a code path.

**A category is a bag.** If a feature's name ends up equal to its category's name, the grouping
found a bag rather than an intention: either the category is too narrow or the feature is too
vague. Fix the one that is wrong.

**Prerequisites are classified apart from capabilities.** `Sign in with GitHub` is a prerequisite:
it enables other things rather than being the thing someone came for. `kind` is `"prerequisite"`
for those and `"capability"` for the rest, so a reader sees the onboarding path on its own.

**`components` entries are element paths copied from the model, not prose.** The path format is
exactly what the model produces:

| Element | Path |
|---|---|
| System | `SeeForce` |
| Container | `SeeForce CLI (SeeForce)` |
| Component | `Annotation Parser (SeeForce CLI)` |

Anything that does not resolve against the model makes the whole catalogue fail to load. Copy the
names; do not retype them from memory and do not translate or tidy them.

**`reviewed_at` is never written by generation.** Leave it `null`. It holds a git commit SHA, and
only a human advancing it in a commit makes a feature reviewed. Writing it yourself destroys the
only signal that separates your output from reviewed content.

**An existing reviewed feature is never edited or deleted.** A feature with a non-null
`reviewed_at` is settled. Append new candidates; leave the reviewed ones byte-identical. If a
reviewed feature now looks wrong, say so to the user instead of changing it.

**Anchor each feature on a real entry point.** Call `list_entry_points()` and put the ids a feature
is reached through in its `entry_points`. A feature claiming no entry point is flagged for review,
and the entry points nothing claims are where the features you have not written yet are.

## The file

```json
{
  "version": 1,
  "generated_at": "2026-11-06T12:00:00Z",
  "categories": [
    {
      "name": "Projects",
      "features": [
        {
          "id": "import-a-project",
          "name": "Import a project",
          "intent": "Turn a GitHub repo's annotations into a browsable map.",
          "kind": "capability",
          "components": ["GitHub Import (Backend)", "Annotation Scanner (Annotation Parser)"],
          "reviewed_at": null,
          "entry_points": ["http:POST /api/graph/import/"],
          "paths": []
        }
      ]
    }
  ]
}
```

`id` is a stable slug and is what a reviewed feature is recognised by across regenerations — never
renumber or re-slug an existing one. `intent` is one sentence. `paths` stays empty; the step-level
flow is a later slice and the field exists so adding it needs no format change.

## When you are done

Run `seeforce features` and fix whatever it refuses to load. Then show the user the review flags
and let **them** decide what to mark reviewed; the commit is the attestation, not your say-so.
