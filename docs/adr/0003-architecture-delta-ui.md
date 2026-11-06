# 3. Architecture delta UI: reviewing a change on the map instead of in the diff

Date: 2026-11-06

## Status

Accepted.

## Context

`seeforce delta` already tells a reviewer what a pull request did to the declared architecture, and
the `arch` CI job writes that markdown into the GitHub job summary. Text is enough to notice *that*
something changed; it is not enough to see *where*, because a change list has no map on it — a new
component reads as one line whether it sits at the edge of the system or between two containers that
were not talking before.

A visual delta adds exactly that: position. Everything below is about keeping the view honest while
adding it, and about not acquiring a snapshot store along the way.

## Decisions

### The view lives in the SeeForce app, and the pull request only links to it

GitHub renders the markdown; the app renders the map. The `arch` job's summary and its comment gain
one link carrying the project and the two refs. Nothing else about the publishing path changes, so
ADR 0001's decision to post under the reviewed repository's own token still holds.

The cost: the reviewer leaves the pull request, and the link only resolves for someone who can open
the project. The markdown stays complete on its own for everyone else.

Rejected: rendering the map to an image in the comment. It cannot be zoomed, panned or drilled
through, which is the whole value, and it needs an image host and a write permission the App lacks.

Rejected: a second renderer inside a GitHub check. Two renderers diverge.

### The comparison is a merge request, and nothing is stored

The route is `/project/:id?pr=<number>`. A merge request is what a reviewer actually has in hand, and
it declares both sides of the comparison itself, so the reviewer picks no base. The backend lists the
repository's open pull requests, takes the head commit and the commit the merge request is based on
from that same listing, fetches `.seeforce/workspace.json` at each through the Contents API call that
`sync-github` already makes, and runs `diff()`. No model, no migration, no snapshot per commit, no
webhook, and no cache.

Comparing against the merge request's base commit rather than the target branch's current tip is what
keeps the view about *this* branch: an architecture change landed on the target meanwhile would
otherwise be rendered as this reviewer's removal.

The cost: a branch with no open merge request cannot be compared in the app at all, and `seeforce
delta` on the command line stays the only way to compare two arbitrary commits. Every load costs
GitHub requests against the viewer's own rate limit, with nothing cached — accepted deliberately,
with measurement, not anticipation, as the trigger for adding a cache.

Rejected: arbitrary `?base=&head=` refs. They need the reviewer to know two commits, and a link built
from them rots on a force-push with nothing to re-resolve it from; a merge request number survives
both. Rejected: storing a snapshot per commit — a write on every push, a retention policy and a
garbage collector, bought to avoid a request that already works.

### The repository is read under the viewer's own credentials

Every GitHub call a comparison makes is authenticated with the requesting user's own installation
token, never the project owner's. Repository access is then decided by GitHub for the person actually
looking: no request can read a repository the requester cannot read, and no request can spend access
quota belonging to someone else. An anonymous visitor following a share link is refused before any
call is made.

The cost: a project member who can see the map but holds no installation covering a private
repository cannot use the comparison, and the view has to say that plainly rather than render an
empty delta.

### No verdict is stored, and none is displayed

ADR 0002 excluded drift indicators from the feature layer. A delta UI reopens the question, because a
view that already knows what was removed is one field away from saying whether that was wise. The
answer is the same, for a different reason: the delta is computed on demand, so it has no freshness
problem — and introducing a verdict would give it one. The view therefore shows what ADR 0001 defined
as facts (added, removed, changed, and the changed-file set per element) and nothing above them: no
risk level, no impact estimate, no merge recommendation, no badge.

The cost: a reviewer asking "is this change safe?" gets no answer from this view. That judgement needs
runtime knowledge the annotations do not hold, and ADR 0001 already refused to infer it.

### One renderer: the delta is a decoration on the head map, not a second diagram

The view endpoint keeps returning the existing ReactFlow shape, built from the *head* workspace, with
two fields added per node and per edge: a status of `added` / `removed` / `changed` / `unchanged`, and
the changed-file list. The node and edge components already read their data from that payload, so the
delta is a border, a tint and a sidebar section — not a new graph, a new layout or a new page.

An element that encloses a change reads as *modified* at every level above it, whatever the
descendant's own state: a container whose contents are not what they were has changed, and that is
what makes a component-level change findable from C1 instead of invisible until the third drill-down.
Amber therefore carries two readings — this element's own declaration changed, and this element
contains a change — which the badge wording and the detail panel keep apart.

Removed elements have no place in the head model, so they are injected into the view as ghost nodes in
order to be positioned at all. Where a removed element's parent is itself gone, the ghost attaches to
the nearest surviving ancestor, and the sidebar names the real parent it was declared under.

The cost: ghosts make the head map briefly untrue — it shows elements the code no longer declares.
The status field is what distinguishes them, so the rendering must make `removed` unmistakable at a
glance and not only in the legend.

Rejected: two maps side by side. It doubles the layout work and makes the reader compare node
positions, which carry no meaning, instead of reading the change.

### A modified element is outlined on the map and explained in the sidebar

`changed` marks the node; which fields changed, and their before and after values, appear as rows in
the existing overlay sidebar when the node is selected. The counters at the top of the view are what
tell a reader a modification exists before clicking anything.

The cost: a field change is invisible until the node is opened. This is deliberate — a description
edit is the commonest change of all, and surfacing each one on the map turns the map into noise while
the structural changes are what the view exists for.

### The documented pairing degradation is labelled, never guessed

ADR 0001 accepts that renaming an element inside a file declaring several of its kind comes out as a
removal plus an addition. Where a removed and an added element share a `(kind, source_file)` pair, the
view presents them together as *possibly a rename in a multi-element file*, with both names. That is
derived in the presenter from the existing `Delta` — no parser change, no new field, and no claim that
it is a rename.

The cost: a genuine deletion and an unrelated addition in one such file are labelled as possible too.
The label says "possibly" for that reason, and the authored `id:` that ADR 0001 rejected for now
remains the fix that removes the ambiguity rather than wording around it.

### A pull request that changes nothing renders the map, not an empty state

With zero changes the view is the ordinary head map plus one line saying the pull request changed no
architecture. The reviewer who followed the link gets the map they would otherwise have navigated to,
and the absence of marks is the answer.

The cost: a load that could have been a 204.

## Consequences

- Two new read-only endpoints, no new table, no new migration; the frontend gains a selector, a change
  list and a status decoration on components it already has.
- The view is unavailable for projects that are not linked to a GitHub repository, and for branches
  with no open merge request. The CLI's markdown remains the only delta for those.
- A comparison never writes the saved layout back, so reviewing one cannot rearrange the ordinary map.
- Every element shown as removed is shown in a position that the head model does not define.
- Nothing in this view tells a reviewer whether to merge.
