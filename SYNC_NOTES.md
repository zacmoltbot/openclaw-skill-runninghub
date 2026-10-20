# Official upstream sync — 2026-10-20

- Source: https://github.com/HM-RunningHub/OpenClaw_RH_Skills
- Official commit: `21ade9836e1e68bdb45fac9956b919f50901b8d4` (2026-08-18).
- Imported catalog and builder verbatim; updated image/video curated references and README content, adapting install links and API links for this international fork.
- Catalog: 420 entries (image 102, video 230, audio 20, 3D 16, text 52). It is not a guarantee of international API availability.
- Preserved fork scripts: `.ai` API hosts, account/billing before/after and coins, video ffprobe/retry/source-URL failure, v2 AI-app submit plus legacy fallback and exact upload fileName handling.
- Preserved live-only `RUNNINGHUB_MAX_POLL_SECONDS` override. The older live AI-app submit was replaced by the newer tracked fork version.
- Corrected preflight billing output timing: emitted before submission (previously only at final billing report).
- No paid generation, no Gateway restart. Run `python3 -m unittest discover -s tests -v` for offline regression checks.
