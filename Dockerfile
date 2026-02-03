FROM bitnami/spark:3.4.2

USER root

ENV SPARK_MODE=master

EXPOSE 7077

CMD ["/opt/bitnami/spark/bin/spark-class", \
     "org.apache.spark.deploy.master.Master", \
     "--host", "0.0.0.0", \
     "--port", "7077", \
     "--webui-port", "$PORT"]