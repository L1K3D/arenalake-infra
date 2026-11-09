FROM python:3.11-slim

WORKDIR /app
COPY agent.py /app/
COPY requirements.txt /app/requirements.txt

# Instala dependências do SO e do Python.
RUN apt-get update && apt-get install -y pciutils && \
    pip install --no-cache-dir -r requirements.txt

EXPOSE 5000
CMD ["python", "agent.py"]