# NPI Tracker (Power Apps solution builds)

- **`HANDOFF.md`**: start here. Import order, risks, spec coverage, what couldn't be verified.
- **`SETUP_CHECKLIST.md`**: SharePoint lists and columns each release needs, cumulative.
- **`INCREMENT6_CONFIG_CONTROL.md`**: config change control (R20/R21) and an end-to-end revision test run.
- **`history/<version>/`**: importable zip, `NOTES.md` (prerequisites and tests) and generated YAML, for each version.
  1.2.0.0–1.2.0.2 are earlier deliveries. 1.2.0.3 → 1.6.0.0 are the overnight slices. `uploadtest/` is the 2b test solution.
- **`base/`**: the tenant export that builds start from (source of truth).
- **Sources:** `src/` (screens), `schema.yaml` (SharePoint schema by release), `flows/` (new flows), `releases/` (per-version config).
- **Build:** `python3 -I build.py releases/<version>.yaml` and `python3 -I build_uploadtest.py`.
  The build validates YAML safety, formula brackets, control types and properties, data source names, and column names
  used in Patch / varRow / varProject / varQ, then repackages the base export.
