# Dataset Validation

## Dataset chosen

- Repository: `nodejs/node`
- Scope: closed issues only
- Snapshot type: capped chronological snapshot
- Processed data hash: `db3e1d356b3202533fc16fe75a21fdf40c9a5c060a19172ec3d403398f7c6d27`

## Fetch strategy

The dataset was collected from the GitHub closed issues endpoint for `nodejs/node` using a capped chronological snapshot:

- Endpoint: `https://api.github.com/repos/nodejs/node/issues`
- Query: `state=closed`, `sort=created`, `direction=asc`, `per_page=100`
- Snapshot cap: 99 pages
- Raw endpoint items fetched: 9,900
- Pull requests removed from raw items: 5,691
- Remaining non-PR issues before label filtering: 4,209

The capped snapshot was used because deep page-number pagination on very large repositories can become unreliable.

## Label mapping

Maintainer labels were normalized into four classifier targets:

- `confirmed-bug` -> `bug`
- `feature request` -> `feature`
- `doc` -> `docs`
- `question` -> `question`

## Filtering rules

An issue was kept only if it satisfied all of the following:

- it was a real issue, not a pull request
- it had exactly one mapped label from the target mapping
- it was excluded if it had no mapped labels
- it was excluded if it had multiple mapped labels

Filtering totals from the frozen manifest:

- usable single-label issues: 1,306
- excluded issues: 2,903
- excluded for no mapped label: 2,859
- excluded for multiple mapped labels: 44

## Final usable count

- Total usable examples: 1,306

## Final class counts

- `bug`: 208
- `feature`: 317
- `docs`: 294
- `question`: 487

## Split strategy

The split is global chronological `70/15/15`. Issues were sorted by `created_at` ascending, then split into:

- train: 914
- val: 196
- test: 196

This keeps evaluation temporally honest by training on older issues and evaluating on newer ones.

## Dataset caveats

- `confirmed-bug` reflects maintainer-confirmed bugs, not every raw bug report opened by users.
- The dataset is a capped snapshot, not the full history of all Node.js issues ever opened.
- Labels are maintainer triage labels and should be treated as project workflow signals, not objective ground truth.
