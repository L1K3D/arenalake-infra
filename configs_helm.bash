# Install Mini.IO with less memory to local testing
helm install arenalake-minio minio/minio \
--namespace data \
--set rootUser=admin \
--set rootPassword=arenalake123 \
--set persistence.enabled=false \
--set resources.requests.memory=512Mi \
--set resources.limits.memory=1Gi \
--set mode=standalone

#---###---#