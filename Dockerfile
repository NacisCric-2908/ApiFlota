FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /srv
RUN useradd --create-home --uid 10001 app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app

# Imagen de pruebas: docker compose --profile test run --rm test
FROM base AS test
COPY requirements-dev.txt pytest.ini ./
RUN pip install -r requirements-dev.txt
COPY tests ./tests
USER app
CMD ["pytest", "-q"]

# Imagen final (es la última etapa, por lo tanto la predeterminada)
FROM base AS prod
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=2).status == 200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
