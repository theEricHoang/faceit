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

1. Install [pyenv](https://github.com/pyenv/pyenv?tab=readme-ov-file#b-set-up-your-shell-environment-for-pyenv) and [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv)
   ⚠️ NOTE!! do the optional step with pyenv-virtualenv that activates virtual environments automatically


2. Create a new Python virtual environment version 3.12.2:

   **On macOS/Linux/Windows Powershell:**
   ```bash
   pyenv install 3.12.2
   pyenv virtualenv 3.12.2 backend
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
