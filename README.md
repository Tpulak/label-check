# LabelCheck

LabelCheck compares an alcohol-label photo with the fields from an application. It is a standalone prototype. It does not connect to COLA, and it does not save photos.

You can check one label, or a spreadsheet of labels with matching photos. Each field comes back as **Match**, **Mismatch**, or **Needs review**.

## Setup

You need Python 3.12, Node.js 20, and the Tesseract OCR program. On Windows, Tesseract is expected at `C:\Program Files\Tesseract-OCR\tesseract.exe`. If it is installed somewhere else, set the `TESSERACT_CMD` environment variable to that `tesseract.exe` path before starting the backend.

From the project folder, set up the backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Then set up the frontend, from the project folder:

```powershell
cd frontend
npm install
```

## Run

Use two terminals and leave both running.

Backend, from the `backend` folder:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Frontend, from the `frontend` folder:

```powershell
npm run dev
```

Open http://localhost:5173/. The page talks to the backend at http://127.0.0.1:8000.

If the backend says it cannot use port 8000, one copy is already running. Use that one instead of starting a second.

Optional checks, from the `backend` folder:

```powershell
.\.venv\Scripts\python -m pytest
```

Sample labels and a matching spreadsheet are in `test-data`. The warning headings on those samples are regular type, not bold, so the government-warning field is a mismatch.

## Approach

The page collects a label photo and five typed application fields: brand name, class/type, alcohol content, net contents, and producer name and address. Those typed fields stand in for a COLA application.

The backend reads the photo with Tesseract, picks out the same fields plus the government warning, and compares them. A weak or unreadable field becomes **Needs review** instead of a firm match or mismatch. Photos are not stored.

A batch is a spreadsheet with one row per label, plus the photo files. The filename column must match the photo file name. The page checks one label at a time and can be stopped after the current label. A missing photo is marked "could not check," and the rest of the batch continues.

## Tools

- Frontend: React, TypeScript, and Vite
- Backend: Python, FastAPI, and Uvicorn
- Reading labels: Tesseract OCR, Pillow, pytesseract, and OpenCV
- Text comparison: RapidFuzz
- Tests: pytest

## Assumptions

- There is no login, no database, and no connection to COLA. The person types the application fields.
- Brand, class, and producer ignore capitalization and punctuation. `Stone's Throw` and `STONE'S THROW` match.
- Alcohol and net contents are compared as numbers. `45%` matches `45% Alc./Vol. (90 Proof)`, and `750 mL` matches `750ml`. A difference such as 40% versus 45% is a mismatch.
- A reading with confidence below 0.8 is **Needs review**, even when the words look right. The app does not invent text it could not read.
- The government warning is required on every alcohol label and is not typed in. It must match the official Surgeon General wording, the heading must be `GOVERNMENT WARNING` in all capitals, and that heading must be bold. If the photo does not show whether the heading is bold, the field needs review.
- Alcohol-content exceptions for some wine and beer labels are not modeled. Country of origin is out of scope.
- Local OCR is used so a label can be checked in about a few seconds without calling a cloud service. Clear printed labels read reliably. Poor photos, glare, and unusual layouts often do not, and those results should be treated as uncertain.

## Deploy

The `Dockerfile` builds the website and the label reader together, including Tesseract. [Render](https://render.com) can run that file.

1. Push this project to GitHub.
2. In Render, choose **New** → **Web Service** and connect the repository.
3. Leave the environment as **Docker**. Set the health check path to `/health`.
4. Deploy. Render prints a public URL. The free service sleeps when it is idle, so the first open after that can take about a minute.
