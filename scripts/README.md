# Scripts

This directory keeps helper scripts out of the project root.

```text
scripts/
  check_migrations.py       Read-only migration file/schema checker
  diagnostics/              Manual database and chart diagnostics
  run/                      Local server startup scripts
  compat/                   Legacy import shims kept for manual use
```

Database diagnostics may connect to MySQL, but they must not create tables, alter schema, or migrate data unless explicitly authorized.
