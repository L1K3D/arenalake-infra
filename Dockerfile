FROM apache/spark:3.5.1

USER root

EXPOSE 7077

CMD /bin/bash -c "/opt/spark/bin/spark-class org.apache.spark.deploy.master.Master \
  --host 0.0.0.0 \
  --port 7077 \
  --webui-port ${PORT}"