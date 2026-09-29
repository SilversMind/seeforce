# Contributing to SeeForce

Contributions are welcome. Issues and pull requests are the right place to start.

## License of your contribution

SeeForce is **source available, not open source**: it is licensed under the
[Functional Source License 1.1 with an Apache 2.0 future license](LICENSE)
(FSL-1.1-ALv2). You may read, modify, run and self-host it — including inside a
company — for any purpose except building a product or service that competes
with SeeForce. Each release becomes Apache-2.0 two years after it ships.

By opening a pull request you license your contribution to the project under
those same terms.

## Sign your commits (DCO)

Every commit must carry a `Signed-off-by` line. It is a statement that you wrote
the code, or otherwise have the right to submit it under the project's license —
see [DCO](DCO) for the exact text you are certifying.

Add it automatically with `-s`:

```bash
git commit -s -m "fix: stop dropping the last edge on reload"
```

This appends `Signed-off-by: Your Name <your@email>` using your `git config`
`user.name` and `user.email`, which must be your real name and a reachable
address.

Forgot to sign? You don't have to rewrite your branch — push a follow-up
remediation commit instead. The failed DCO check on your pull request spells out
the exact line to put in it.

If you would rather fix the history, amend the last commit:

```bash
git commit --amend -s --no-edit && git push --force-with-lease
```

Or sign the whole branch at once:

```bash
git rebase --signoff main && git push --force-with-lease
```

## Before you open a PR

CI runs pytest on `backend`, `cli` and `packages/c4parser`, plus `ruff` and the
frontend lint and type-check. Run the parts you touched:

```bash
cd backend && uv run pytest
cd frontend && npm run lint && npx tsc -b
uvx ruff@0.16.9 check .
```

## Architecture annotations

SeeForce documents its own architecture with C4 annotations in source
docstrings. If your change adds a service, a distinct module, an external
dependency or a new relationship between components, update the annotations in
the same PR — see [CLAUDE.md](CLAUDE.md) for what counts as significant.
