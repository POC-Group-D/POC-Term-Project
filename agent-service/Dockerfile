# recommendationservice v2 (AI agent).
# The test stage runs the unit tests; the image is only built if they pass.

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM base AS test
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY recommendation_agent ./recommendation_agent
COPY tests ./tests
RUN python -m pytest -q && touch /tmp/tests-passed

FROM base AS runtime
# Depend on the test stage so a failing test fails the build.
COPY --from=test /tmp/tests-passed /tmp/tests-passed
COPY recommendation_agent ./recommendation_agent
RUN useradd --create-home --uid 10001 agent
USER agent
ENV PORT=8080
EXPOSE 8080
ENTRYPOINT ["python", "-m", "recommendation_agent.server"]
