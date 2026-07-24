# Portfolio Newsletter — daily pipeline container.
#
# Slim Python base keeps the image small and the daily pull fast.
# The build installs deps first (cached layer), then copies code, so code
# edits don't re-run pip every time.

FROM python:3.12-slim

# Don't buffer stdout/stderr -- we want log lines to appear in real time in
# the GitHub Actions run, not all at once at the end.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependencies first for layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Then the application code (src/) + the portfolio file. portfolio.json is
# written to the repo root at run time from a secret (see the CI workflow) and
# copied to /app here. Running `python src/main.py` puts src/ on the import
# path, so the flat module imports work, while the working directory stays
# /app so load_portfolio() finds portfolio.json.
COPY src/ ./src/
COPY portfolio.json ./

# All secrets (ANTHROPIC_API_KEY, TAVILY_API_KEY, RESEND_API_KEY,
# RECIPIENT_EMAIL) are injected at runtime as env vars -- never baked in.
CMD ["python", "src/main.py"]
