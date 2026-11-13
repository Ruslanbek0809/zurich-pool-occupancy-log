# Zürich pool occupancy log

A scheduled log of the City of Zürich open-data feed of the **current** number of guests in its public pools.
The source publishes only the latest snapshot and keeps no history; this repository keeps one, by fetching the feed every 15 minutes and appending it to monthly CSV files.

## Source

- Dataset: "Aktuelle «Anzahl der Badegäste»", https://data.stadt-zuerich.ch/dataset/ssd_spo_badi_aktuell
- Feed: https://data.stadt-zuerich.ch/dataset/ssd_spo_badi_aktuell/download/crowd-monitor.csv
- Publisher: Stadt Zürich, Sportamt (Schul- und Sportdepartement), via Open Data Zürich
- Licence: Creative Commons CC0 (`cc-zero`). The logged files are redistributed under the same terms.

According to the dataset description, the numbers are sensor counts of guests currently inside each pool (a snapshot), the same numbers shown on the city's "Badi aktuell" page, and they run about 20 % higher than ticket counts.
See the dataset page for details on how the data are collected.

## Files

- `data/YYYY-MM.csv`: one file per month (month of the UTC fetch time). UTF-8, comma-separated, header in the first line.
- `data/YYYY-MM_schema2.csv`, `_schema3.csv`, …: only created if the source changes its columns during a month; a file never mixes two headers.
- `data/failures.log`: one line per failed fetch (see below).
- `log_feed.py`: one fetch (Python standard library only). `log_loop.sh`: calls it every 15 minutes and commits each fetch. `.github/workflows/log.yml`: runs the loop on GitHub Actions.

### Columns

| column | meaning |
|---|---|
| `logged_at_utc` | time this repository fetched the feed, UTC, ISO 8601 (`2026-11-10T22:56:18Z`). Identical for all rows of one fetch. |
| `retrievaltime` | source column, copied unchanged |
| `name` | source column: pool name |
| `currentfill` | source column: current number of guests |
| `occupancy_icons` | source column: occupancy as four dots (e.g. `●●●○`) |
| `uid` | source column: pool identifier |

All source columns are copied unchanged and in source order; only `logged_at_utc` is added.
The source header when logging started was `retrievaltime,name,currentfill,occupancy_icons,uid`, with 22 pools.

### About `retrievaltime`

Observed on 2026-11-10: `retrievaltime` looks like `2026-11-10 19:09:53.392708+01:00`, i.e. local Zürich time with an explicit UTC offset (`+01:00` in winter) and microseconds, space-separated.
It differs per row (the source appears to read the pools one after another, about a second apart).
It is the time the **source** read its sensors, not the time of this fetch: when the source does not update, consecutive fetches log the same snapshot again with the same `retrievaltime`.
For example, on 2026-11-10 the feed still showed the 19:09–19:10 local-time snapshot at 23:58 local time.
The source also stalls for longer: the fetches of 2026-11-12 16:52 and 22:40 UTC and of 2026-11-13 02:57 UTC all showed the snapshot of 2026-11-12 14:37 local time.
Use `retrievaltime` to detect repeated snapshots; use `logged_at_utc` to know when the snapshot was seen.

## How it runs and its limits

One workflow run fetches the feed at minutes 7, 22, 37 and 52 of every hour for 5 hours 30 minutes (GitHub ends a job after 6 hours), then starts the next run.
The next run waits for its first slot, so a hand-over normally loses no fetch; if GitHub starts it late, slots are missing.
Each fetch appends one block of rows and makes one commit; runs never overlap.
Gaps between `logged_at_utc` values are real missing observations, not zero guests.

Before 2026-11-14 the log relied on GitHub's cron schedule alone, which started a run of this repository only every 4 to 9 hours: the days 2026-11-11 to 2026-11-13 hold nine fetches in total.
The cron line is kept only to restart the chain of runs if it breaks.

## Failures

If the download fails after three attempts, or the response is empty, not UTF-8, HTML, has no data rows, or has rows with a different number of fields than the header, the logger writes **no** rows and appends one line to `data/failures.log`:

```
2026-11-10T22:56:48Z	fetch failed after 3 attempts: URLError: <urlopen error [Errno 61] Connection refused>
```

(UTC time, a tab, the reason.) A slot with no running workflow leaves no trace at all; only the gap in `logged_at_utc` shows it.

## Running it locally

```
python3 log_feed.py              # fetch once and append to data/
python3 log_feed.py <url>        # use another feed URL (also: FEED_URL environment variable)
RUN_MIN=45 bash log_loop.sh      # fetch at every slot for 45 minutes, commit and push each fetch
```
