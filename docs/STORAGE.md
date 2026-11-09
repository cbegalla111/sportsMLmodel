# Storage and feed health

The public GitHub Pages dashboard runs data collection and model review on GitHub Actions. Viewing it does not install Python, copy SQLite databases, or download historical training archives onto a visitor's laptop. The browser receives the public dashboard snapshot and stores a small local shortlist/preferences. A Git clone, Codespace or locally installed private app has separate storage costs; this audit measured the cloud workspace, not the user's laptop.

## Automatic retention

- Raw source downloads are content-hash deduplicated and stored as gzip. Existing SHA-256-named raw/CSV archives are verified, compressed and verified again before the uncompressed copy is removed. Unknown files and checksum mismatches are preserved.
- Replaceable source archives: 30 days, at most 128 MiB. Source hashes and normalized accepted results remain in the database/metadata; discarded payloads can be downloaded again from their provider where available.
- Compressed injury-report archives: 180 days, at most 64 MiB. The current injury reports and frozen injury-research observations are separate and are never pruned by this policy.
- Local backups: newest seven. Public GitHub prediction-ledger artifacts retain their existing 90-day policy.
- Existing player-log caches retain their 180-day window. This change does not shorten the player samples or delete model-training rows.
- SQLite data, fitted model weights, public prediction ledgers, historical grading records and injury-research features are never pruned by cache maintenance. Runtime size can still grow gradually as essential records accumulate; the cache limits are not a hard cap on all installed software or all data.

Maintenance runs before/after public builds and before private-app daily backups. New source archives are compressed at download time. The private refresh watcher defaults to one hour, matching the public workflow schedule; GitHub's schedule can be delayed. Manual maintenance:

```bash
python -m scripts.storage_maintenance --runtime /workspace/.sportsml-private
```

Backups now include public prediction ledgers, verified result reconciliation and injury-research observations, alongside SQLite, models and compressed source inputs. Authentication stays excluded. Restore to an empty directory with `python -m scripts.restore ARCHIVE NEW_DIRECTORY`.

## Measured audit

Cloud runtime files shrank from 302,064,104 to 120,039,834 bytes (about 60% less). Source downloads shrank from 203,179,569 to 21,155,299 bytes after losslessly compressing 220 files. No source archive or injury archive needed deletion during this cleanup. Sixteen protected database/model/ledger/research files retained identical SHA-256 hashes. A real backup restored 44,958 normalized events; saved public prediction and injury-research ledgers matched byte-for-byte. Temporary restoration test files were removed afterward.

Public snapshot checked: 2026-11-09T06:19:44Z (1:19 a.m. Eastern). All seven result feeds were fresh, all seven daily calendars reported success, and all five configured player-log collectors reported no errors or pending collection. NBA/NFL/NHL injury reports were current. WNBA/MLB injury timestamps were stale and the CFB endpoint did not supply usable fresh records; their coverage remains unverified. UFC has no configured injury feed. Feed freshness and injury coverage are separate checks; no fresh data is invented for an unavailable provider.
