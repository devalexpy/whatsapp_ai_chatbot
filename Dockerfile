FROM python:3.12-slim AS builder

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copiar archivos de dependencias
COPY pyproject.toml uv.lock ./

# Instalar dependencias
RUN uv sync --frozen --no-install-project --no-dev

# Copiar el código fuente
COPY . .

# Instalar el proyecto
RUN uv sync --frozen --no-dev


FROM python:3.12-slim AS runtime

# Crear usuario no-root
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copiar el entorno virtual desde el builder
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appgroup /app .

# Configurar el PATH para usar el entorno virtual
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Cambiar al usuario no-root
USER appuser

# Railway asigna el puerto via $PORT
ENV PORT=8000
EXPOSE $PORT

CMD fastapi run main.py --host 0.0.0.0 --port $PORT

