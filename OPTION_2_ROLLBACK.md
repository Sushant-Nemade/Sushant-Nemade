# Option 2 Rollback

Option 1 is preserved at `README.option-1.md` and its original assets remain under `assets/`.

To restore it locally:

```powershell
Copy-Item README.option-1.md README.md -Force
.\.venv\Scripts\python.exe -m tools.validate_readme
.\.venv\Scripts\python.exe -m pytest -q
```

Review `git diff -- README.md`, commit the restoration, and push `main`. Option 2 files may remain in the repository for later switching; they do not affect the active profile when `README.md` points only to Option 1 assets.
