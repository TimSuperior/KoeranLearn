# Backup and Restore

## PostgreSQL backup

Backups use `pg_dump --format custom` and write timestamped files to `BACKUP_DIR`.

```bash
docker compose --profile ops run --rm backup
```

In production, run `scripts/backup_postgres.sh` from a small cron container or host cron with:

- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `PGPASSWORD`
- `BACKUP_DIR`
- `BACKUP_RETENTION_DAYS`

Default retention is 14 days.

## Restore

Restore into a fresh or intentionally replaceable database:

```bash
PGPASSWORD=... sh scripts/restore_postgres.sh /backups/koreanlearn_YYYYMMDDTHHMMSSZ.dump
```

After restore:

```bash
cd apps/api
alembic upgrade head
pytest
```

## Content and assets

Content is stored in PostgreSQL and covered by the database backup. If uploaded lesson assets are later enabled, back up the configured asset bucket or mounted asset volume on the same cadence and verify that restored lesson asset URLs resolve.

## S3-compatible storage

For off-host copies, sync `BACKUP_DIR` to S3-compatible storage with a separate deployment secret:

```bash
aws --endpoint-url "$S3_BACKUP_ENDPOINT" s3 sync "$BACKUP_DIR" "s3://$S3_BACKUP_BUCKET/postgres/"
```
