# Option 3 Switching and Rollback

Available profile layouts:

- `README.option-1.md` - Living Terminal
- `README.option-2.md` - Applied AI Dossier
- `README.option-3.md` - Systems Console

To activate one locally, copy the chosen file to `README.md`, run validation, review the diff, and publish:

```powershell
Copy-Item README.option-2.md README.md -Force
.\.venv\Scripts\python.exe -m tools.validate_readme
.\.venv\Scripts\python.exe -m pytest -q
```

Replace `README.option-2.md` with the desired option. Option assets live in separate directories, so switching the active README does not alter either implementation.
