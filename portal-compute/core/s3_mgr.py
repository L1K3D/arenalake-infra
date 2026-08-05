import boto3

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url='http://minio:9000',
        aws_access_key_id='arenalake',
        aws_secret_access_key='arenalake123',
        region_name='us-east-1'
    )

def fetch_catalog_data():
    s3_client = get_s3_client()
    buckets_response = s3_client.list_buckets()
    buckets = [bucket['Name'] for bucket in buckets_response.get('Buckets', [])]

    catalog_data = {}
    for bucket in buckets:
        objects_response = s3_client.list_objects_v2(Bucket=bucket)
        files = [obj['Key'] for obj in objects_response.get('Contents', [])]
        catalog_data[bucket] = files

    return catalog_data
