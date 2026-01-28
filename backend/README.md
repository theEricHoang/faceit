# FaceIT Backend

This is the backend service for FaceIT.

## Structure

- `app/` - Main application code
  - `main.py` - FastAPI entrypoint
  - `api/` - API route definitions
  - `core/` - Core configuration
  - `db/` - Supabase integrations
  - `models/` - ORM and data models
  - `schemas/` - Pydantic schemas
  - `services/` - Business logic and services
  - `utils/` - Utility functions
- `tests/` - Unit and integration tests
- `requirements.txt` - Python dependencies
- `.gitignore` - Git ignore rules

## Getting Started

1. Install pyenv [here](https://github.com/pyenv/pyenv?tab=readme-ov-file#b-set-up-your-shell-environment-for-pyenv)


2. Create a new Python virtual environment and activate it:

   **On macOS/Linux:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   **On Windows (PowerShell):**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Notes
- This is the initial project scaffold.
