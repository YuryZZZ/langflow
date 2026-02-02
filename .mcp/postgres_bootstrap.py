#!/usr/bin/env python3
"""postgres_bootstrap.py - PostgreSQL TaskBus Schema Bootstrap

This module ensures the PostgreSQL database and schema are ready for TaskBus.
It creates all required tables, indexes, and functions idempotently.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Database configuration from environment
DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")
DB_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
DB_NAME = os.environ.get("POSTGRES_DB", "opencode_taskbus")
DB_USER = os.environ.get("POSTGRES_USER", "postgres")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")


def get_psycopg2():
    """Import psycopg2 with proper error handling."""
    try:
        import psycopg2
        return psycopg2
    except ImportError:
        sys.stderr.write("[Bootstrap] psycopg2 not installed. Installing...\n")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "psycopg2-binary"], check=True)
        import psycopg2
        return psycopg2


def create_database_if_missing():
    """Create the TaskBus database if it doesn't exist."""
    pg = get_psycopg2()

    try:
        # Try connecting to target DB first
        conn = pg.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=3
        )
        conn.close()
        return True  # DB exists
    except:
        pass

    # Create database
    try:
        conn = pg.connect(
            host=DB_HOST,
            port=DB_PORT,
            database="postgres",
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=5
        )
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        if not cur.fetchone():
            from psycopg2 import sql
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
            sys.stderr.write(f"[Bootstrap] Created database: {DB_NAME}\n")

        cur.close()
        conn.close()
        return True
    except Exception as e:
        sys.stderr.write(f"[Bootstrap] Database creation failed: {e}\n")
        return False


def create_schema():
    """Create all TaskBus tables and indexes."""
    pg = get_psycopg2()

    conn = pg.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=10
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Core TaskBus tables
    tables_sql = """
    -- Projects table
    CREATE TABLE IF NOT EXISTS projects (
        id SERIAL PRIMARY KEY,
        project_id VARCHAR(64) UNIQUE NOT NULL,
        project_path TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Runs table
    CREATE TABLE IF NOT EXISTS runs (
        id SERIAL PRIMARY KEY,
        run_id TEXT UNIQUE NOT NULL,
        project_id VARCHAR(64) NOT NULL,
        cts_hash VARCHAR(128),
        status VARCHAR(32) DEFAULT 'active',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_id);
    CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);

    -- Tasks table
    CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        task_id TEXT UNIQUE NOT NULL,
        run_id TEXT,
        project_id VARCHAR(64) NOT NULL,
        gate VARCHAR(16) DEFAULT 'A',
        task_type VARCHAR(64),
        role VARCHAR(64),
        agent VARCHAR(64),
        status VARCHAR(32) DEFAULT 'QUEUED',
        priority INT DEFAULT 5,
        complexity VARCHAR(16),
        deps JSONB,
        artifact_writes JSONB,
        timeout_ms INT DEFAULT 300000,
        attempts INT DEFAULT 0,
        max_attempts INT DEFAULT 3,
        last_error TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
    CREATE INDEX IF NOT EXISTS idx_tasks_run ON tasks(run_id);
    CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
    CREATE INDEX IF NOT EXISTS idx_tasks_gate ON tasks(gate);
    CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority DESC);

    -- Gates table
    CREATE TABLE IF NOT EXISTS gates (
        id SERIAL PRIMARY KEY,
        project_id VARCHAR(64) NOT NULL,
        run_id TEXT,
        current_gate VARCHAR(16) DEFAULT 'A',
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(project_id, run_id)
    );

    -- Artifacts table
    CREATE TABLE IF NOT EXISTS artifacts (
        id SERIAL PRIMARY KEY,
        artifact_id VARCHAR(64) UNIQUE NOT NULL,
        task_id TEXT,
        run_id TEXT,
        project_id VARCHAR(64) NOT NULL,
        artifact_type VARCHAR(32),
        content TEXT,
        metadata JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_artifacts_task ON artifacts(task_id);
    CREATE INDEX IF NOT EXISTS idx_artifacts_run ON artifacts(run_id);

    -- Events table
    CREATE TABLE IF NOT EXISTS events (
        id SERIAL PRIMARY KEY,
        event_id VARCHAR(64) UNIQUE NOT NULL,
        project_id VARCHAR(64) NOT NULL,
        run_id TEXT,
        task_id TEXT,
        event_type VARCHAR(64),
        payload JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_events_project ON events(project_id);
    CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id);

    -- Locks table (for distributed locking)
    CREATE TABLE IF NOT EXISTS locks (
        id SERIAL PRIMARY KEY,
        lock_key VARCHAR(128) UNIQUE NOT NULL,
        holder VARCHAR(128),
        acquired_at TIMESTAMPTZ DEFAULT NOW(),
        expires_at TIMESTAMPTZ
    );

    -- Blocked table (for tracking blocked tasks)
    CREATE TABLE IF NOT EXISTS blocked (
        id SERIAL PRIMARY KEY,
        task_id TEXT NOT NULL,
        blocker_task_id TEXT,
        reason TEXT,
        blocked_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_blocked_task ON blocked(task_id);

    -- Cost tracking table
    CREATE TABLE IF NOT EXISTS cost_tracking (
        id SERIAL PRIMARY KEY,
        run_id TEXT,
        task_id TEXT,
        model VARCHAR(128),
        input_tokens INT,
        output_tokens INT,
        cost_usd DECIMAL(10, 6),
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_cost_run ON cost_tracking(run_id);

    -- Conversation history
    CREATE TABLE IF NOT EXISTS conversation_history (
        id SERIAL PRIMARY KEY,
        run_id TEXT NOT NULL,
        role VARCHAR(32),
        content TEXT,
        model VARCHAR(128),
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_conv_run ON conversation_history(run_id);

    -- Conversation summaries
    CREATE TABLE IF NOT EXISTS conversation_summaries (
        id SERIAL PRIMARY KEY,
        run_id TEXT NOT NULL,
        summary TEXT,
        token_count INT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_summary_run ON conversation_summaries(run_id);

    -- Schema migrations tracking
    CREATE TABLE IF NOT EXISTS schema_migrations (
        id SERIAL PRIMARY KEY,
        version VARCHAR(32) UNIQUE NOT NULL,
        applied_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Task tree (for hierarchical tasks)
    CREATE TABLE IF NOT EXISTS task_tree (
        id SERIAL PRIMARY KEY,
        parent_task_id TEXT,
        child_task_id TEXT NOT NULL,
        depth INT DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_tree_parent ON task_tree(parent_task_id);
    CREATE INDEX IF NOT EXISTS idx_tree_child ON task_tree(child_task_id);

    -- Task validations
    CREATE TABLE IF NOT EXISTS task_validations (
        id SERIAL PRIMARY KEY,
        task_id TEXT NOT NULL,
        validation_type VARCHAR(64),
        result VARCHAR(32),
        details JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_validation_task ON task_validations(task_id);
    """

    # PARL tables
    parl_sql = """
    -- Critical Steps Tracking (PARL latency metric)
    CREATE TABLE IF NOT EXISTS critical_steps (
        id SERIAL PRIMARY KEY,
        run_id TEXT NOT NULL,
        orchestrator_steps INT DEFAULT 0,
        max_subagent_steps INT DEFAULT 0,
        critical_step_total INT GENERATED ALWAYS AS (orchestrator_steps + max_subagent_steps) STORED,
        timestamp TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_critical_steps_run ON critical_steps(run_id);

    -- Subagent Sessions (PARL session isolation)
    CREATE TABLE IF NOT EXISTS subagent_sessions (
        id SERIAL PRIMARY KEY,
        run_id TEXT NOT NULL,
        subagent_id VARCHAR(64) NOT NULL,
        parent_session_id INT,
        model VARCHAR(128),
        profile VARCHAR(64),
        spawned_at TIMESTAMPTZ DEFAULT NOW(),
        completed_at TIMESTAMPTZ,
        status VARCHAR(32) DEFAULT 'active',
        context_tokens INT DEFAULT 0,
        steps_executed INT DEFAULT 0,
        result JSONB,
        error_message TEXT,
        UNIQUE(run_id, subagent_id)
    );
    CREATE INDEX IF NOT EXISTS idx_subagent_run ON subagent_sessions(run_id);
    CREATE INDEX IF NOT EXISTS idx_subagent_status ON subagent_sessions(status);

    -- Parallel Execution Graph (DAG of task dependencies)
    CREATE TABLE IF NOT EXISTS execution_graph (
        id SERIAL PRIMARY KEY,
        run_id TEXT NOT NULL,
        parent_task_id TEXT,
        child_task_id TEXT NOT NULL,
        dependency_type VARCHAR(32),
        condition JSONB,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_graph_run ON execution_graph(run_id);
    CREATE INDEX IF NOT EXISTS idx_graph_parent ON execution_graph(parent_task_id);
    CREATE INDEX IF NOT EXISTS idx_graph_child ON execution_graph(child_task_id);

    -- PARL Reward Tracking
    CREATE TABLE IF NOT EXISTS parl_rewards (
        id SERIAL PRIMARY KEY,
        run_id TEXT NOT NULL,
        training_step INT DEFAULT 0,
        reward DECIMAL(10, 6),
        lambda_aux DECIMAL(10, 6),
        r_parallel DECIMAL(10, 6),
        success_indicator DECIMAL(10, 6),
        q_tau DECIMAL(10, 6),
        num_subagents INT,
        critical_steps INT,
        computed_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_rewards_run ON parl_rewards(run_id);

    -- Task Decomposition Cache
    CREATE TABLE IF NOT EXISTS decomposition_cache (
        id SERIAL PRIMARY KEY,
        task_hash VARCHAR(64) UNIQUE NOT NULL,
        task_description TEXT,
        decomposition JSONB NOT NULL,
        success_rate DECIMAL(5, 4) DEFAULT 0.0,
        usage_count INT DEFAULT 1,
        avg_critical_steps DECIMAL(10, 2),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        last_used_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_decomp_hash ON decomposition_cache(task_hash);
    CREATE INDEX IF NOT EXISTS idx_decomp_success ON decomposition_cache(success_rate DESC);
    """

    # Views and functions
    views_sql = """
    -- PARL Run Summary View
    CREATE OR REPLACE VIEW parl_run_summary AS
    SELECT
        r.run_id,
        r.status,
        r.created_at,
        r.updated_at,
        COUNT(DISTINCT ss.id) AS total_subagents,
        COUNT(DISTINCT ss.id) FILTER (WHERE ss.status = 'completed') AS completed_subagents,
        MAX(cs.critical_step_total) AS max_critical_steps,
        AVG(cs.critical_step_total) AS avg_critical_steps,
        SUM(ss.steps_executed) AS total_steps_executed,
        MAX(pr.reward) AS final_reward
    FROM runs r
    LEFT JOIN subagent_sessions ss ON r.run_id = ss.run_id
    LEFT JOIN critical_steps cs ON r.run_id = cs.run_id
    LEFT JOIN parl_rewards pr ON r.run_id = pr.run_id
    GROUP BY r.run_id, r.status, r.created_at, r.updated_at;

    -- Function: Calculate critical path length
    CREATE OR REPLACE FUNCTION calculate_critical_path(p_run_id TEXT)
    RETURNS INT AS $$
    DECLARE
        v_critical_path INT;
    BEGIN
        WITH RECURSIVE path AS (
            SELECT
                eg.child_task_id,
                1 AS depth,
                ARRAY[eg.child_task_id] AS path
            FROM execution_graph eg
            WHERE eg.run_id = p_run_id
              AND eg.parent_task_id IS NULL

            UNION ALL

            SELECT
                eg.child_task_id,
                p.depth + 1,
                p.path || eg.child_task_id
            FROM execution_graph eg
            JOIN path p ON eg.parent_task_id = p.child_task_id
            WHERE eg.run_id = p_run_id
              AND NOT eg.child_task_id = ANY(p.path)
        )
        SELECT MAX(depth) INTO v_critical_path FROM path;

        RETURN COALESCE(v_critical_path, 0);
    END;
    $$ LANGUAGE plpgsql;

    -- Function: Get cached decomposition
    CREATE OR REPLACE FUNCTION get_cached_decomposition(p_task_description TEXT)
    RETURNS JSONB AS $$
    DECLARE
        v_hash VARCHAR(64);
        v_decomposition JSONB;
    BEGIN
        v_hash := md5(lower(trim(p_task_description)));

        SELECT decomposition INTO v_decomposition
        FROM decomposition_cache
        WHERE task_hash = v_hash
          AND success_rate > 0.7
        ORDER BY success_rate DESC, usage_count DESC
        LIMIT 1;

        IF v_decomposition IS NOT NULL THEN
            UPDATE decomposition_cache
            SET usage_count = usage_count + 1,
                last_used_at = NOW()
            WHERE task_hash = v_hash;
        END IF;

        RETURN v_decomposition;
    END;
    $$ LANGUAGE plpgsql;
    """

    try:
        # Execute all SQL
        cur.execute(tables_sql)
        sys.stderr.write("[Bootstrap] Core tables created\n")

        cur.execute(parl_sql)
        sys.stderr.write("[Bootstrap] PARL tables created\n")

        cur.execute(views_sql)
        sys.stderr.write("[Bootstrap] Views and functions created\n")

        # Record migration
        cur.execute("""
            INSERT INTO schema_migrations (version)
            VALUES ('parl_v1.0')
            ON CONFLICT (version) DO NOTHING
        """)

    except Exception as e:
        sys.stderr.write(f"[Bootstrap] Schema creation warning: {e}\n")
    finally:
        cur.close()
        conn.close()


def bootstrap_taskbus():
    """Main bootstrap function - creates database and schema."""
    sys.stderr.write("[Bootstrap] Starting TaskBus bootstrap...\n")

    if create_database_if_missing():
        create_schema()
        sys.stderr.write("[Bootstrap] TaskBus bootstrap complete\n")
    else:
        sys.stderr.write("[Bootstrap] Could not connect to PostgreSQL\n")


if __name__ == "__main__":
    bootstrap_taskbus()
