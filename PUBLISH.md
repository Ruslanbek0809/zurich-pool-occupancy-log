# Publishing (run once)

Requirements: `git` with your name and email configured, and `gh` logged in (`gh auth status`).
Run everything from inside this folder.

```sh
git init -b main
git add .
git status            # expect: README.md, PUBLISH.md, log_feed.py, .github/workflows/log.yml, data/.gitkeep
git commit -m "Add feed logger and schedule"
gh repo create zurich-pool-occupancy-log --public --source . --push --description "15-minute log of the City of Zurich open-data feed of current pool guests (CC0 source)"
gh workflow run log.yml
```

If `gh workflow run` says the workflow is not found, wait half a minute and run it again (GitHub needs a moment to register a new workflow).

## Check the first run

```sh
gh run list --limit 3
```

Healthy: the newest line has status `completed` and conclusion `success` (shown as a check mark), event `workflow_dispatch`.
Then pull and look at the data:

```sh
git pull
ls data
head -3 data/*.csv
```

Healthy: one file `data/YYYY-MM.csv` with the header `logged_at_utc,retrievaltime,name,currentfill,occupancy_icons,uid` and one block of rows with the same `logged_at_utc`, and no `data/failures.log` (or one with only an occasional line).
Scheduled runs (event `schedule`) start on their own, usually within an hour; GitHub may delay them.

If a run failed: `gh run view --log-failed` shows the failing step.

## Weekly check

```sh
gh api 'repos/{owner}/{repo}/commits?path=data&per_page=1' --jq '.[0].commit.committer.date + "  " + .[0].commit.message'
```

Healthy: a date from the last hour or so. Also glance at `data/failures.log` on GitHub for repeated failures.

## If runs stop

1. `gh run list --limit 10`: are runs failing (look at `gh run view <id> --log-failed`) or not starting at all?
2. Not starting: `gh workflow list --all`. If `log feed` shows as disabled (GitHub disables scheduled workflows in public repositories after 60 days without repository activity), run `gh workflow enable log.yml`, then `gh workflow run log.yml`.
3. Failing on push: someone else pushed conflicting changes to `data/`; fix the conflict locally, push, and start a run with `gh workflow run log.yml`.
4. Failing fetches only (rows in `data/failures.log`, run itself green): the source is down or moved; check the dataset page https://data.stadt-zuerich.ch/dataset/ssd_spo_badi_aktuell.
