FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

RUN uv venv .venv

COPY pyproject.toml uv.lock ./

RUN uv sync --no-dev --frozen

COPY . .

EXPOSE 8080

ENV DEV_PORT=8501

ENV APP_PATH="engineer_app.py"

CMD . .venv/bin/activate && \
    if [ "$DEV_MODE" = "true" ]; then \
        streamlit run $APP_PATH --server.port=$DEV_PORT --server.address=0.0.0.0; \
    else \
        streamlit run $APP_PATH --server.port=$PORT --server.address=0.0.0.0; \
    fi 