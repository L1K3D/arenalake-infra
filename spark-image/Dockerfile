FROM apache/spark:3.5.0

USER root

# 1. Instala o wget
RUN apt-get update && apt-get install -y wget

# 2. Baixa o Miniconda que JÁ É nativo no Python 3.11
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-py311_23.11.0-2-Linux-x86_64.sh -O miniconda.sh && \
    bash miniconda.sh -b -p /opt/conda && \
    rm miniconda.sh

# 3. Adiciona o Conda ao PATH do sistema
ENV PATH=/opt/conda/bin:$PATH

# 4. Instala o boto3 (O Python 3.11 já está pronto!)
RUN pip install boto3

# 5. Força o PySpark a usar o Python do Conda
ENV PYSPARK_PYTHON=/opt/conda/bin/python
ENV PYSPARK_DRIVER_PYTHON=/opt/conda/bin/python

# 6. Suporte ao S3 (CRÍTICO)
ADD https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar /opt/spark/jars/
ADD https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.262/aws-java-sdk-bundle-1.12.262.jar /opt/spark/jars/

USER 185
