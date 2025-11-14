FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock* /app/
COPY src /app/src
RUN uv pip install --system .

COPY data /app/data

ENTRYPOINT ["alertzarr"]
CMD ["--help"]
