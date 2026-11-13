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

Healthy: the newest line has status `in_progress`, event `workflow_dispatch`. A run logs for 5 h 30 min, ends as `completed` / `success` and starts the next one, which shows up as a new `in_progress` line.
Lines with event `schedule` and conclusion `cancelled` are normal: a scheduled run that waited while the chain was alive is replaced by the chain's next run.
After the first slot (minutes 7, 22, 37, 52 of the hour), pull and look at the data:

```sh
git pull
ls data
head -3 data/*.csv
```

Healthy: one file `data/YYYY-MM.csv` with the header `logged_at_utc,retrievaltime,name,currentfill,occupancy_icons,uid`, one block of rows per slot with the same `logged_at_utc`, and no `data/failures.log` (or one with only an occasional line).

To see the hand-over without waiting 5 h 30 min: `gh workflow run log.yml -f minutes=20`, then `gh run list --limit 3` about 25 minutes later must show that run as `completed` / `success` and a new `in_progress` run.

If a run failed: `gh run view --log-failed` shows the failing step.

## Weekly check

```sh
gh api 'repos/{owner}/{repo}/commits?path=data&per_page=1' --jq '.[0].commit.committer.date + "  " + .[0].commit.message'
```

Healthy: a date from the last 20 minutes. Also glance at `data/failures.log` on GitHub for repeated failures.

## If runs stop

1. `gh run list --limit 10`: are runs failing (look at `gh run view <id> --log-failed`) or not starting at all?
2. No run `in_progress`: start the chain again with `gh workflow run log.yml`. If the step "Start the next run" failed in the last run, its log says why.
   If `gh workflow list --all` shows `log feed` as disabled (GitHub disables scheduled workflows in public repositories after 60 days without repository activity), run `gh workflow enable log.yml` first.
3. Failing on push: someone else pushed conflicting changes to `data/`; fix the conflict locally, push, and start a run with `gh workflow run log.yml`.
4. Failing fetches only (rows in `data/failures.log`, run itself green): the source is down or moved; check the dataset page https://data.stadt-zuerich.ch/dataset/ssd_spo_badi_aktuell.

## Stopping the logger

```sh
gh workflow disable log.yml
gh run list --limit 3          # note the id of the in_progress run
gh run cancel <id>
```

A cancelled run does not start a successor. To start again: `gh workflow enable log.yml`, then `gh workflow run log.yml`.
