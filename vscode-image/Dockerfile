FROM codercom/code-server:latest

USER root

# 1. Instala o Java Padrão do Debian e dependências
RUN apt-get update && apt-get install -y \
    default-jdk \
    python3-pip \
    python3-dev \
    build-essential \
    git \
    curl \
    && apt-get clean

# 2. Configura as variáveis de ambiente do Java
ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH=$JAVA_HOME/bin:$PATH

# 3. Libera o PIP globalmente (Adeus erro do PEP 668!)
ENV PIP_BREAK_SYSTEM_PACKAGES=1

USER coder

# 4. Instala os motores do Jupyter e do Spark direto no Python da máquina
RUN pip install jupyter ipykernel pyspark

# 5. Pré-instala as extensões essenciais na UI do VS Code de fábrica
# Agora com o Jupyter nativo garantido!
RUN code-server --install-extension ms-python.python && \
    code-server --install-extension ms-toolsai.jupyter

# Define o workspace padrão limpo
WORKDIR /home/coder/project
