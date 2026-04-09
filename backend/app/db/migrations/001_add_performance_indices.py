"""
Migration: Add performance indices for Job and Review tables.

This migration adds composite indices to optimize query performance:
- Job table: (status, created_at) for polling, (app_ids) for filtering
- Review table: (app_id, domain_category, timestamp) for dashboard queries
               (app_id, sentiment, timestamp) for trend analysis
               (app_id, is_spam) for spam filtering
"""

from sqlalchemy import text


def upgrade(bind):
    """Apply indices"""
    with bind.connect() as connection:
        # Job indices
        connection.execute(text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_job_status_created "
            "ON jobs(status, created_at)"
        ))
        connection.execute(text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_job_app_ids "
            "ON jobs(app_ids)"
        ))
        connection.execute(text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_job_created_at "
            "ON jobs(created_at)"
        ))
        
        # Review indices
        connection.execute(text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_review_app_category_time "
            "ON reviews(app_id, domain_category, timestamp)"
        ))
        connection.execute(text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_review_sentiment_app "
            "ON reviews(app_id, sentiment, timestamp)"
        ))
        connection.execute(text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_review_app_spam "
            "ON reviews(app_id, is_spam)"
        ))
        connection.execute(text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_review_domain_category "
            "ON reviews(domain_category, domain_subcategory)"
        ))
        
        connection.commit()


def downgrade(bind):
    """Rollback indices"""
    with bind.connect() as connection:
        indices = [
            "ix_job_status_created",
            "ix_job_app_ids",
            "ix_job_created_at",
            "ix_review_app_category_time",
            "ix_review_sentiment_app",
            "ix_review_app_spam",
            "ix_review_domain_category",
        ]
        for idx in indices:
            connection.execute(text(f"DROP INDEX CONCURRENTLY IF EXISTS {idx}"))
        connection.commit()
