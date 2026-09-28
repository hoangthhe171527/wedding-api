#!/usr/bin/env bash
# Khôi phục từ một bản sao lưu. GHI ĐÈ dữ liệu hiện tại.
#   ./restore.sh backups/20261001-031500
set -euo pipefail
cd "$(dirname "$0")"

SRC="${1:?Cách dùng: ./restore.sh backups/<thời điểm>}"
PROJECT="${PROJECT:-wedding-prod}"
ENV_FILE="${ENV_FILE:-.env.prod}"
COMPOSE=(docker compose -p "$PROJECT" -f docker-compose.prod.yml --env-file "$ENV_FILE")

test -s "${SRC}/mongo.archive.gz" || { echo "Thiếu ${SRC}/mongo.archive.gz"; exit 1; }
test -s "${SRC}/s3-data.tgz" || { echo "Thiếu ${SRC}/s3-data.tgz"; exit 1; }
if [ "${CONFIRM:-}" != "yes" ]; then
  read -r -p "Ghi đè dữ liệu của ${PROJECT} bằng ${SRC}? Gõ 'yes': " answer
  [ "$answer" = "yes" ] || { echo "Huỷ."; exit 1; }
fi

echo "[restore] dừng api để không ai ghi trong lúc khôi phục"
"${COMPOSE[@]}" stop api

echo "[restore] MongoDB"
"${COMPOSE[@]}" exec -T mongodb sh -c \
  'mongorestore -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --drop --oplogReplay --archive --gzip' \
  < "${SRC}/mongo.archive.gz"

echo "[restore] ảnh (volume S3)"
"${COMPOSE[@]}" stop s3
docker run --rm -v "${PROJECT}_s3_data:/data" -v "$(pwd)/${SRC}:/in:ro" alpine:3.20 \
  sh -c 'rm -rf /data/* /data/.[!.]* 2>/dev/null; tar xzf /in/s3-data.tgz -C /data'
"${COMPOSE[@]}" start s3

"${COMPOSE[@]}" start api
echo "[restore] xong."
