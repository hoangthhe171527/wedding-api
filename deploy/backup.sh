#!/usr/bin/env bash
# Sao lưu production: MongoDB (mongodump, gzip) + dữ liệu ảnh (volume S3).
#   ./backup.sh                 # vào ./backups/<thời điểm>/
# Chạy hằng ngày bằng cron, và ĐẨY thư mục backups ra ngoài máy chủ (rclone / R2):
#   15 3 * * * cd /srv/wedding/deploy && ./backup.sh && rclone sync backups r2:wedding-backups
set -euo pipefail
cd "$(dirname "$0")"

PROJECT="${PROJECT:-wedding-prod}"
ENV_FILE="${ENV_FILE:-.env.prod}"
KEEP="${KEEP:-14}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="backups/${STAMP}"
COMPOSE=(docker compose -p "$PROJECT" -f docker-compose.prod.yml --env-file "$ENV_FILE")

mkdir -p "$OUT"
echo "[backup] MongoDB -> ${OUT}/mongo.archive.gz"
"${COMPOSE[@]}" exec -T mongodb sh -c \
  'mongodump -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin --oplog --archive --gzip' \
  > "${OUT}/mongo.archive.gz"

echo "[backup] ảnh (volume S3) -> ${OUT}/s3-data.tgz"
docker run --rm -v "${PROJECT}_s3_data:/data:ro" -v "$(pwd)/${OUT}:/out" alpine:3.20 \
  tar czf /out/s3-data.tgz -C /data .

# Kiểm nhanh: archive rỗng / hỏng là báo lỗi ngay, không để tới lúc cần khôi phục.
test -s "${OUT}/mongo.archive.gz" && gzip -t "${OUT}/mongo.archive.gz"
test -s "${OUT}/s3-data.tgz" && gzip -t "${OUT}/s3-data.tgz"
echo "[backup] xong: $(du -sh "$OUT" | cut -f1)"

# Giữ lại KEEP bản mới nhất.
ls -1d backups/*/ 2>/dev/null | sort | head -n "-${KEEP}" | xargs -r rm -rf
