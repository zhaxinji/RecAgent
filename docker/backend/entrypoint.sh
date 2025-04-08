#!/bin/bash
set -e

# 等待PostgreSQL启动
echo "Waiting for PostgreSQL to start..."
while ! nc -z postgres 5432; do
  sleep 0.1
done
echo "PostgreSQL started"

# 等待Redis启动
echo "Waiting for Redis to start..."
while ! nc -z redis 6379; do
  sleep 0.1
done
echo "Redis started"

# 等待Elasticsearch启动
echo "Waiting for Elasticsearch to start..."
while ! nc -z elasticsearch 9200; do
  sleep 0.1
done
echo "Elasticsearch started"

# 等待MinIO启动
echo "Waiting for MinIO to start..."
while ! nc -z minio 9000; do
  sleep 0.1
done
echo "MinIO started"

# 执行数据库迁移
echo "Running database migrations..."
cd /app
python -m alembic upgrade head

# 创建MinIO桶（如果不存在）
echo "Initializing MinIO..."
python -c "
import boto3
from botocore.exceptions import ClientError
from src.core.config import settings

s3_client = boto3.client(
    's3',
    endpoint_url=f'http://{settings.MINIO_HOST}:{settings.MINIO_PORT}',
    aws_access_key_id=settings.MINIO_ACCESS_KEY,
    aws_secret_access_key=settings.MINIO_SECRET_KEY,
    config=boto3.session.Config(signature_version='s3v4'),
    region_name='us-east-1',
)

# 创建默认桶
try:
    s3_client.head_bucket(Bucket=settings.MINIO_BUCKET)
    print(f'Bucket {settings.MINIO_BUCKET} already exists')
except ClientError:
    print(f'Creating bucket {settings.MINIO_BUCKET}')
    s3_client.create_bucket(Bucket=settings.MINIO_BUCKET)
"

# 初始化数据库
echo "Initializing database..."
python -c "
from src.db.init_db import main
main()
"

echo "Initialization completed"

exec "$@" 