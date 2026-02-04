FROM apache/spark:3.5.1

ENV PYSPARK_PYTHON=python3

WORKDIR /app

# Copia os jobs
COPY jobs/ jobs/

# Executa o job automaticamente
CMD ["/opt/spark/bin/spark-submit", "jobs/primeiro_job.py"]