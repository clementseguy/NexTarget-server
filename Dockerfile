# Python 3.11.16 slim-bookworm, pinned to the official multi-architecture
# manifest digest. Update the tag and digest together during dependency review.
FROM python:3.11.16-slim-bookworm@sha256:528257d48c1da0dcecc2e725d1ae34498d60c965f1241e39cd6a85a8859bdf84

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update \
    && apt-get install --yes --no-install-recommends media-types \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 nextarget \
    && useradd --uid 10001 --gid nextarget --create-home --shell /usr/sbin/nologin nextarget \
    && mkdir /data \
    && chown nextarget:nextarget /data
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=nextarget:nextarget . ./
RUN chown nextarget:nextarget /app
USER nextarget
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
