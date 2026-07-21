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

# Then the application code + the portfolio file.
COPY *.py ./
COPY portfolio.json ./

# All secrets (ANTHROPIC_API_KEY, TAVILY_API_KEY, RESEND_API_KEY,
# RECIPIENT_EMAIL) are injected at runtime as env vars -- never baked in.
CMD ["python", "main.py"]
