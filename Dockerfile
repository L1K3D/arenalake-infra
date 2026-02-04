FROM apache/spark:3.5.1

USER root

ENV SPARK_MODE=local
ENV SPARK_LOCAL_IP=127.0.0.1
ENV PYSPARK_PYTHON=python3

# Porta da UI do Spark
EXPOSE 4040
EXPOSE 8080

CMD ["/opt/spark/bin/spark-class", \
     "org.apache.spark.deploy.master.Master", \
     "--host", "0.0.0.0", \
     "--port", "7077", \
     "--webui-port", "8080"]