FROM python:3.11-slim

WORKDIR /app
COPY agent.py /app/

# Instala dependências do SO (pciutils para lspci) e do Python
RUN apt-get update && apt-get install -y pciutils && \
    pip install fastapi uvicorn psutil distro

EXPOSE 5000
CMD ["python", "agent.py"]