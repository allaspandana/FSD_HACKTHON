# BugDiary — Your Personal Coding Mistake Intelligence

BugDiary is a local-first coding-mistake journal for students. Record errors and corrected solutions, search your library, schedule revisions, and use transparent rule-based analytics to identify topics worth practising.

## Features

- Dashboard cards for total mistakes, pending revisions, due revisions, and topics to practise.
- Create, view, edit, and delete coding mistakes.
- Search by title, error message, language, topic, difficulty, and tags.
- Save incorrect/corrected code, explanation, root cause, and tags.
- Revision scheduling, review completion, and review history.
- Rule-based repeated-error and weak-topic analysis using stored records.
- Optional sample data button and a separate action to remove sample records.
- Responsive HTML/CSS/vanilla JavaScript frontend served by FastAPI.
- SQLite database created automatically on first startup; records persist between restarts.

Analytics are heuristics based only on records entered into this local app. They are not an assessment of a person's overall programming ability.

## Requirements

- Windows 10/11
- Python 3.10 or newer
- VS Code (recommended)

## Run on Windows / VS Code

1. Extract the ZIP.
2. Open the extracted `BugDiary` folder in VS Code.
3. Open **Terminal → New Terminal** and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

If PowerShell blocks activation, run this for the current terminal only, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

If `py` is not recognised, use `python` instead.

4. Open **http://127.0.0.1:8000** in your browser.
5. API documentation is available at **http://127.0.0.1:8000/docs**.

The app creates `backend/bugdiary.db` automatically. Do not delete this file if you want to keep your records.

## How to use

- Use **Add mistake** to record an error and its solution.
- Open any item from the library to view details, edit it, or delete it.
- Use the search field and filters to narrow the library.
- From the detail panel, schedule a revision or mark the mistake reviewed.
- Open **Analytics** to inspect repeated categories and weak topics.
- Select **Load demo data** for a quick presentation. Demo records are labelled as sample data and can be removed using **Remove demo data**.

## Tests

Run:

```powershell
python -m unittest discover -s tests -v
```

The tests use a temporary SQLite database and cover creation, retrieval, filtering, updates, deletion, and analytics endpoint behaviour. They do not alter your main database.

## Common issues

- **`uvicorn` is not recognised:** activate `.venv` and run `python -m uvicorn backend.main:app --reload`.
- **Port 8000 is busy:** run `python -m uvicorn backend.main:app --reload --port 8001` and open `http://127.0.0.1:8001`.
- **Missing dependency:** confirm the virtual environment is active and run `pip install -r requirements.txt`.
- **Browser shows an error:** keep the terminal open, inspect its traceback, and refresh the page.
- **PowerShell activation is blocked:** use the temporary execution-policy command above.

## Folder structure

```text
BugDiary/
├── backend/
│   ├── __init__.py
│   ├── main.py
│   └── database.py
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   └── js/app.js
├── tests/
│   └── test_api.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```
