FROM python:3.12-slim
WORKDIR /workspace/sportsMLmodel
COPY requirements.txt .
COPY wheelhouse /opt/wheels
ARG PIP_NO_INDEX=0
RUN python -m venv /workspace/.sportsml-venv && PIP_NO_INDEX=${PIP_NO_INDEX} /workspace/.sportsml-venv/bin/pip install --no-cache-dir --find-links=/opt/wheels -r requirements.txt
COPY --chown=1000:1000 . .
RUN useradd --uid 1000 --create-home sportslab && mkdir /data && chown sportslab:sportslab /data
USER sportslab
ENV SPORTSLAB_HOME=/data SPORTSLAB_BIND=0.0.0.0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
EXPOSE 8765
CMD ["bash", "scripts/start.sh"]
