FROM apache/spark:3.5.1

ENV SPARK_MODE=local
ENV PYSPARK_PYTHON=python3

EXPOSE 8080

CMD ["/opt/spark/bin/spark-class", \
     "org.apache.spark.deploy.master.Master", \
     "--host", "0.0.0.0", \
     "--webui-port", "8080"]