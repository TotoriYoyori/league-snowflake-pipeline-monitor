from typing import Protocol


class MonitorQuery:
    mock_file_name: str = ""
    ttl: int = 60

    def build(self) -> str:
        raise NotImplementedError


# --------------- SEED (models/_infra/monitor.ipynb) ---------------
class SeedObjectInventory(MonitorQuery):
    mock_file_name = "seed_object_inventory"
    ttl = 60

    def build(self) -> str:
        return f"""
            SELECT
                TABLE_TYPE AS OBJECT_TYPE,
                TABLE_NAME AS OBJECT_NAME,
                ROW_COUNT,
                ROUND(BYTES / 1024, 0)::INTEGER AS SIZE_KB,
                CREATED,
                LAST_ALTERED,
                COMMENT
            FROM LEAGUE_RECORDS.INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'SEED'
            ORDER BY TABLE_TYPE, TABLE_NAME
        """


class SeedStages(MonitorQuery):
    mock_file_name = "seed_stages"
    ttl = 60

    def build(self) -> str:
        return f"SHOW STAGES IN SCHEMA LEAGUE_RECORDS.SEED"


class SeedProcedures(MonitorQuery):
    mock_file_name = "seed_procedures"
    ttl = 60

    def build(self) -> str:
        return f"SHOW PROCEDURES IN SCHEMA LEAGUE_RECORDS.SEED"


class SeedRowCountValidation(MonitorQuery):
    """CSV-vs-table row count reconciliation per seed dataset."""

    mock_file_name = "seed_row_count_validation"
    ttl = 60

    def build(self) -> str:
        return f"""
            WITH table_counts AS (
                SELECT 'matches_summary' AS DATASET, COUNT(*) AS TABLE_ROWS FROM SEED.SEED_MATCHES_SUMMARY
                    UNION ALL
                SELECT 'players_summary', COUNT(*) FROM SEED.SEED_PLAYERS_SUMMARY
                    UNION ALL
                SELECT 'intervals', COUNT(*) FROM SEED.SEED_MATCH_INTERVALS
                    UNION ALL
                SELECT 'items_ref', COUNT(*) FROM SEED.SEED_ITEMS_REF
                    UNION ALL
                SELECT 'champions_ref', COUNT(*) FROM SEED.SEED_CHAMPIONS_REF
            ),
            
            csv_counts AS (
                SELECT 'matches_summary' AS DATASET, COUNT(*) AS CSV_ROWS
                FROM @SEED.SEED_UPLOAD_STG (PATTERN => '.*matches_summary.*')
                    UNION ALL
                SELECT 'players_summary', COUNT(*)
                FROM @SEED.SEED_UPLOAD_STG (PATTERN => '.*players_summary.*')
                    UNION ALL
                SELECT 'intervals', COUNT(*)
                FROM @SEED.SEED_UPLOAD_STG (PATTERN => '.*intervals.*')
                    UNION ALL
                SELECT 'items_ref', COUNT(*)
                FROM @SEED.SEED_UPLOAD_STG (PATTERN => '.*items_ref.*')
                    UNION ALL
                SELECT 'champions_ref', COUNT(*)
                FROM @SEED.SEED_UPLOAD_STG (PATTERN => '.*champions_ref.*')
            )
            
            SELECT
                t.DATASET,
                t.TABLE_ROWS,
                c.CSV_ROWS,
                CASE WHEN t.TABLE_ROWS = c.CSV_ROWS THEN 'PASS' ELSE 'MISMATCH' END AS STATUS
            FROM table_counts t
            JOIN csv_counts c ON t.DATASET = c.DATASET
            ORDER BY t.DATASET
        """


class SeedStageFiles(MonitorQuery):
    mock_file_name = "seed_stage_files"
    ttl = 60

    def build(self) -> str:
        return """
            SELECT
                RELATIVE_PATH,
                ROUND(SIZE / 1024, 0)::INTEGER AS FILE_SIZE_KB,
                LAST_MODIFIED,
                FILE_URL
            FROM DIRECTORY(@SEED.SEED_UPLOAD_STG)
            ORDER BY RELATIVE_PATH
        """


class SeedLoadState(MonitorQuery):
    """Simulated daily ingestion pointer. DAYS_REMAINING = 0 means fully loaded."""

    mock_file_name = "seed_load_state"
    ttl = 60

    def build(self) -> str:
        return """
            SELECT
                CURRENT_LOAD_DATE,
                MIN_DATE,
                MAX_DATE,
                LAST_LOADED_AT,
                DATEDIFF('day', CURRENT_LOAD_DATE, MAX_DATE) AS DAYS_INGESTED,
                DATEDIFF('day', MIN_DATE, CURRENT_LOAD_DATE) AS DAYS_REMAINING
            FROM SEED.SEED_LOAD_STATE
        """


class SeedDateIndex(MonitorQuery):
    mock_file_name = "seed_date_index"
    ttl = 60

    def __init__(self, limit: int = 10):
        self.limit = limit

    def build(self) -> str:
        return f"""
            SELECT
                GAME_DATE_DAY,
                COUNT(*) AS MATCHES_ON_DATE
            FROM SEED.SEED_MATCH_DATE_INDEX
            GROUP BY GAME_DATE_DAY
            ORDER BY GAME_DATE_DAY DESC
            LIMIT {self.limit}
        """


# --------------- BRONZE (models/bronze/monitor.ipynb) ---------------
class BronzeObjectInventory(MonitorQuery):
    mock_file_name = "bronze_object_inventory"
    ttl = 60

    def build(self) -> str:
        return f"""
            SELECT
                TABLE_TYPE AS OBJECT_TYPE,
                TABLE_NAME AS OBJECT_NAME,
                ROW_COUNT,
                ROUND(BYTES / 1024, 0)::INTEGER AS SIZE_KB,
                CREATED,
                LAST_ALTERED,
                COMMENT
            FROM LEAGUE_RECORDS.INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'BRONZE'
            ORDER BY TABLE_TYPE, TABLE_NAME
        """


class BronzeStages(MonitorQuery):
    mock_file_name = "bronze_stages"
    ttl = 60

    def build(self) -> str:
        return f"SHOW STAGES IN SCHEMA LEAGUE_RECORDS.BRONZE"


class BronzePipes(MonitorQuery):
    mock_file_name = "bronze_pipes"
    ttl = 60

    def build(self) -> str:
        return f"SHOW PIPES IN SCHEMA LEAGUE_RECORDS.BRONZE"


class BronzeStreams(MonitorQuery):
    mock_file_name = "bronze_streams"
    ttl = 60

    def build(self) -> str:
        return f"SHOW STREAMS IN SCHEMA LEAGUE_RECORDS.BRONZE"


class BronzeFileFormats(MonitorQuery):
    mock_file_name = "bronze_file_formats"
    ttl = 60

    def build(self) -> str:
        return f"SHOW FILE FORMATS IN SCHEMA LEAGUE_RECORDS.BRONZE"


class BronzeRowCounts(MonitorQuery):
    mock_file_name = "bronze_row_counts"
    ttl = 60

    def build(self) -> str:
        return """
            SELECT 'MATCHES_SUMMARY_BRONZE' AS TABLE_NAME, COUNT(*) AS ROW_COUNT
            FROM BRONZE.MATCHES_SUMMARY_BRONZE
                UNION ALL
            SELECT 'PLAYERS_SUMMARY_BRONZE', COUNT(*)
            FROM BRONZE.PLAYERS_SUMMARY_BRONZE
                UNION ALL
            SELECT 'MATCH_INTERVALS_BRONZE', COUNT(*)
            FROM BRONZE.MATCH_INTERVALS_BRONZE
                UNION ALL
            SELECT 'ITEMS_REF_BRONZE', COUNT(*)
            FROM BRONZE.ITEMS_REF_BRONZE
                UNION ALL
            SELECT 'CHAMPIONS_REF_BRONZE', COUNT(*)
            FROM BRONZE.CHAMPIONS_REF_BRONZE
        """


class BronzePipeStatus(MonitorQuery):
    mock_file_name = "bronze_pipe_status"
    ttl = 30

    def build(self) -> str:
        return """
            SELECT
                PIPE_NAME,
                STATUS:executionState::VARCHAR AS EXECUTION_STATE,
                STATUS:pendingFileCount::INTEGER AS PENDING_FILE_COUNT,
                STATUS:lastIngestedFilePath::VARCHAR AS LAST_INGESTED_FILE_PATH,
                STATUS:lastIngestedTimestamp::TIMESTAMP_LTZ AS LAST_INGESTED_TIMESTAMP
            FROM (
                SELECT 'MATCHES_SUMMARY_PP' AS PIPE_NAME, PARSE_JSON(SYSTEM$PIPE_STATUS('BRONZE.MATCHES_SUMMARY_PP')) AS STATUS
                UNION ALL
                SELECT 'PLAYERS_SUMMARY_PP', PARSE_JSON(SYSTEM$PIPE_STATUS('BRONZE.PLAYERS_SUMMARY_PP'))
                UNION ALL
                SELECT 'MATCH_INTERVALS_PP', PARSE_JSON(SYSTEM$PIPE_STATUS('BRONZE.MATCH_INTERVALS_PP'))
                UNION ALL
                SELECT 'ITEMS_REF_PP', PARSE_JSON(SYSTEM$PIPE_STATUS('BRONZE.ITEMS_REF_PP'))
                UNION ALL
                SELECT 'CHAMPIONS_REF_PP', PARSE_JSON(SYSTEM$PIPE_STATUS('BRONZE.CHAMPIONS_REF_PP'))
            )
        """


class BronzeCopyHistory(MonitorQuery):
    mock_file_name = "bronze_copy_history"
    ttl = 120

    def __init__(self, lookback_hours: int = 24 * 14):
        self.lookback_hours = lookback_hours

    def build(self) -> str:
        tables = [
            "MATCHES_SUMMARY_BRONZE",
            "PLAYERS_SUMMARY_BRONZE",
            "MATCH_INTERVALS_BRONZE",
            "ITEMS_REF_BRONZE",
            "CHAMPIONS_REF_BRONZE",
        ]
        unions = "\n    UNION ALL\n".join(
            f"""
            SELECT *
            FROM TABLE(INFORMATION_SCHEMA.COPY_HISTORY(
                TABLE_NAME => 'BRONZE.{t}',
                START_TIME => DATEADD(HOUR, -{self.lookback_hours}, CURRENT_TIMESTAMP())
            ))"""
            for t in tables
        )
        return f"""
            SELECT
                TABLE_NAME,
                FILE_NAME,
                ROW_COUNT,
                ROW_PARSED,
                ERROR_COUNT,
                LAST_LOAD_TIME,
                STATUS
            FROM ({unions})
            ORDER BY TABLE_NAME ASC, LAST_LOAD_TIME DESC
        """


class BronzeStageFiles(MonitorQuery):
    mock_file_name = "bronze_stage_files"
    ttl = 60

    def build(self) -> str:
        return """
            SELECT 'MATCHES_SUMMARY_STG' AS STAGE, RELATIVE_PATH, ROUND(SIZE / 1024, 0)::INTEGER AS SIZE_KB, LAST_MODIFIED
            FROM DIRECTORY(@BRONZE.MATCHES_SUMMARY_STG)
                UNION ALL
            SELECT 'PLAYERS_SUMMARY_STG', RELATIVE_PATH, ROUND(SIZE / 1024, 0)::INTEGER, LAST_MODIFIED
            FROM DIRECTORY(@BRONZE.PLAYERS_SUMMARY_STG)
                UNION ALL
            SELECT 'MATCH_INTERVALS_STG', RELATIVE_PATH, ROUND(SIZE / 1024, 0)::INTEGER, LAST_MODIFIED
            FROM DIRECTORY(@BRONZE.MATCH_INTERVALS_STG)
                UNION ALL
            SELECT 'ITEMS_REF_STG', RELATIVE_PATH, ROUND(SIZE / 1024, 0)::INTEGER, LAST_MODIFIED
            FROM DIRECTORY(@BRONZE.ITEMS_REF_STG)
                UNION ALL
            SELECT 'CHAMPIONS_REF_STG', RELATIVE_PATH, ROUND(SIZE / 1024, 0)::INTEGER, LAST_MODIFIED
            FROM DIRECTORY(@BRONZE.CHAMPIONS_REF_STG)
            ORDER BY STAGE, RELATIVE_PATH
        """


class BronzeStreamState(MonitorQuery):
    mock_file_name = "bronze_stream_state"
    ttl = 30

    def build(self) -> str:
        return """
            SELECT 'MATCHES_SUMMARY_BRONZE_STM' AS STREAM, SYSTEM$STREAM_HAS_DATA('BRONZE.MATCHES_SUMMARY_BRONZE_STM') AS HAS_DATA
                UNION ALL
            SELECT 'PLAYERS_SUMMARY_BRONZE_STM', SYSTEM$STREAM_HAS_DATA('BRONZE.PLAYERS_SUMMARY_BRONZE_STM')
                UNION ALL
            SELECT 'MATCH_INTERVALS_BRONZE_STM', SYSTEM$STREAM_HAS_DATA('BRONZE.MATCH_INTERVALS_BRONZE_STM')
                UNION ALL
            SELECT 'ITEMS_REF_BRONZE_STM', SYSTEM$STREAM_HAS_DATA('BRONZE.ITEMS_REF_BRONZE_STM')
                UNION ALL
            SELECT 'CHAMPIONS_REF_BRONZE_STM', SYSTEM$STREAM_HAS_DATA('BRONZE.CHAMPIONS_REF_BRONZE_STM')
        """


# --------------- SILVER (models/silver/monitor.ipynb) ---------------
class SilverObjectInventory(MonitorQuery):
    """Tables, views, and tasks combined into one inventory (3 SHOW calls in
    the notebook; concatenated client-side in mock mode and live mode alike).

    Special-shaped: no single `.build()` result — handled by its own named
    loader in data.py, not the generic `load_query`.
    """

    def build_tables(self) -> str:
        return f"SHOW TABLES IN SCHEMA LEAGUE_RECORDS.SILVER"

    def build_views(self) -> str:
        return f"SHOW VIEWS IN SCHEMA LEAGUE_RECORDS.SILVER"

    def build_tasks(self) -> str:
        return f"SHOW TASKS IN SCHEMA LEAGUE_RECORDS.SILVER"


class SilverTaskHistory(MonitorQuery):
    mock_file_name = "silver_task_history"
    ttl = 60

    def __init__(self, lookback_hours: int = 24):
        self.lookback_hours = lookback_hours

    def build(self) -> str:
        return f"""
            SELECT
                NAME,
                STATE,
                SCHEDULED_TIME,
                COMPLETED_TIME,
                DATEDIFF('second', SCHEDULED_TIME, COMPLETED_TIME) AS DURATION_SEC,
                ERROR_CODE,
                ERROR_MESSAGE
            FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
                SCHEDULED_TIME_RANGE_START => DATEADD('hour', -{self.lookback_hours}, CURRENT_TIMESTAMP()),
                RESULT_LIMIT => 100
            ))
            WHERE SCHEMA_NAME = 'SILVER'
            ORDER BY NAME, SCHEDULED_TIME DESC
        """


class SilverTaskSummary(MonitorQuery):
    mock_file_name = "silver_task_summary"
    ttl = 60

    def __init__(self, lookback_hours: int = 24):
        self.lookback_hours = lookback_hours

    def build(self) -> str:
        return f"""
            SELECT
                NAME AS TASK_NAME,
                STATE,
                COUNT(*) AS RUN_COUNT,
                ROUND(AVG(DATEDIFF('second', SCHEDULED_TIME, COMPLETED_TIME)), 2) AS AVG_DURATION_SEC
            FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
                SCHEDULED_TIME_RANGE_START => DATEADD('hour', -{self.lookback_hours}, CURRENT_TIMESTAMP()),
                RESULT_LIMIT => 500
            ))
            WHERE SCHEMA_NAME = 'SILVER'
            GROUP BY NAME, STATE
            ORDER BY NAME, STATE
        """


class SilverStreamState(MonitorQuery):
    mock_file_name = "silver_stream_state"
    ttl = 30

    def build(self) -> str:
        return """
            SELECT 'MATCH_INTERVALS_BRONZE_STM' AS STREAM_NAME, SYSTEM$STREAM_HAS_DATA('BRONZE.MATCH_INTERVALS_BRONZE_STM') AS HAS_DATA
                UNION ALL
            SELECT 'MATCHES_SUMMARY_BRONZE_STM', SYSTEM$STREAM_HAS_DATA('BRONZE.MATCHES_SUMMARY_BRONZE_STM')
                UNION ALL
            SELECT 'PLAYERS_SUMMARY_BRONZE_STM', SYSTEM$STREAM_HAS_DATA('BRONZE.PLAYERS_SUMMARY_BRONZE_STM')
                UNION ALL
            SELECT 'ITEMS_REF_BRONZE_STM', SYSTEM$STREAM_HAS_DATA('BRONZE.ITEMS_REF_BRONZE_STM')
                UNION ALL
            SELECT 'CHAMPIONS_REF_BRONZE_STM', SYSTEM$STREAM_HAS_DATA('BRONZE.CHAMPIONS_REF_BRONZE_STM')
        """


class SilverRowCounts(MonitorQuery):
    """Row counts + size + LAST_ALTERED, used as a freshness proxy."""

    mock_file_name = "silver_row_counts"
    ttl = 60

    def build(self) -> str:
        return f"""
            SELECT
                TABLE_NAME,
                ROW_COUNT,
                BYTES,
                ROUND(BYTES / 1024 / 1024, 2) AS SIZE_MB,
                LAST_ALTERED
            FROM LEAGUE_RECORDS.INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'SILVER'
                AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY ROW_COUNT DESC
        """


class SilverVsGoldCounts(MonitorQuery):
    """Outgoing: row count parity between Silver and Gold for key relationships."""

    mock_file_name = "silver_vs_gold_counts"
    ttl = 60

    def build(self) -> str:
        return """
            SELECT
                'MATCHES: Silver vs Gold' AS COMPARISON,
                (SELECT COUNT(*) FROM SILVER.MATCHES_SUMMARY_SILVER) AS SILVER_ROWS,
                (SELECT COUNT(*) FROM GOLD.MATCH_TEAM_STATS_SUMMARY) AS GOLD_ROWS,
                (SELECT COUNT(*) FROM SILVER.MATCHES_SUMMARY_SILVER) -
                (SELECT COUNT(*) FROM GOLD.MATCH_TEAM_STATS_SUMMARY) AS DIFF
            UNION ALL
            SELECT
                'PLAYERS: Silver vs Gold',
                (SELECT COUNT(*) FROM SILVER.PLAYERS_SUMMARY_SILVER),
                (SELECT COUNT(*) FROM GOLD.PLAYER_STATS_SUMMARY),
                (SELECT COUNT(*) FROM SILVER.PLAYERS_SUMMARY_SILVER) -
                (SELECT COUNT(*) FROM GOLD.PLAYER_STATS_SUMMARY)
            UNION ALL
            SELECT
                'CHAMPIONS: Ref vs Overview',
                (SELECT COUNT(*) FROM SILVER.CHAMPIONS_REF_SILVER WHERE CHAMPION_ID != 0),
                (SELECT COUNT(*) FROM GOLD.CHAMPION_OVERVIEW),
                (SELECT COUNT(*) FROM SILVER.CHAMPIONS_REF_SILVER WHERE CHAMPION_ID != 0) -
                (SELECT COUNT(*) FROM GOLD.CHAMPION_OVERVIEW)
        """


# ===========================================================================
# GOLD (models/gold/monitor.ipynb)
# ===========================================================================
class GoldObjectInventory(MonitorQuery):
    mock_file_name = "gold_object_inventory"
    ttl = 60

    def build(self) -> str:
        return f"SHOW DYNAMIC TABLES IN SCHEMA LEAGUE_RECORDS.GOLD"


class GoldDtFreshness(MonitorQuery):
    """Relies on result-scanning the prior SHOW DYNAMIC TABLES call; in live
    mode this must run immediately after GoldObjectInventory in the same
    session, matching the notebook's pattern.

    Special-shaped: handled by its own named loader in data.py, not the
    generic `load_query`, since it depends on a preceding query in the same
    session.
    """

    mock_file_name = "gold_dt_freshness"
    ttl = 60

    def build(self) -> str:
        return """
            SELECT
                "name" AS DT_NAME,
                "scheduling_state" AS STATE,
                "target_lag" AS TARGET_LAG,
                "data_timestamp" AS LAST_REFRESH_AT,
                DATEDIFF('minute', "data_timestamp", CURRENT_TIMESTAMP()) AS ACTUAL_LAG_MINUTES,
                CASE
                    WHEN "scheduling_state" != 'ACTIVE' THEN '⚠ NOT ACTIVE'
                    WHEN DATEDIFF('minute', "data_timestamp", CURRENT_TIMESTAMP()) >
                         REGEXP_SUBSTR("target_lag", '\\\\d+')::INT * 2 THEN '⚠ BEHIND SCHEDULE'
                    ELSE '✓ ON TRACK'
                END AS FRESHNESS_STATUS
            FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
        """


class GoldRefreshHistory(MonitorQuery):
    mock_file_name = "gold_refresh_history"
    ttl = 60

    def __init__(self, limit: int = 30):
        self.limit = limit

    def build(self) -> str:
        return f"""
            SELECT
                NAME AS DT_NAME,
                STATE AS REFRESH_STATE,
                REFRESH_START_TIME,
                REFRESH_END_TIME,
                DATEDIFF('second', REFRESH_START_TIME, REFRESH_END_TIME) AS REFRESH_DURATION_SEC,
                STATISTICS:"numInsertedRows"::INT AS ROWS_INSERTED,
                STATISTICS:"numDeletedRows"::INT AS ROWS_DELETED,
                STATISTICS:"numCopiedRows"::INT AS ROWS_COPIED
            FROM TABLE(INFORMATION_SCHEMA.DYNAMIC_TABLE_REFRESH_HISTORY(
                NAME_PREFIX => 'LEAGUE_RECORDS.GOLD.'
            ))
            ORDER BY REFRESH_END_TIME DESC
            LIMIT {self.limit}
        """


class GoldGrainValidation(MonitorQuery):
    """Validates gold-table grain against the silver tables they're derived
    from (existence/shape check, not the excluded sample-match recompute)."""

    mock_file_name = "gold_grain_validation"
    ttl = 60

    def build(self) -> str:
        return """
            SELECT
                'PLAYER_STATS_SUMMARY grain = distinct (MATCH_ID, PARTICIPANT_POS_ID) in PLAYERS_SUMMARY_SILVER' AS CHECK,
                (SELECT COUNT(*) FROM SILVER.PLAYERS_SUMMARY_SILVER) AS EXPECTED,
                (SELECT COUNT(*) FROM GOLD.PLAYER_STATS_SUMMARY) AS ACTUAL,
                CASE WHEN (SELECT COUNT(*) FROM SILVER.PLAYERS_SUMMARY_SILVER)
                        = (SELECT COUNT(*) FROM GOLD.PLAYER_STATS_SUMMARY)
                     THEN 'PASS' ELSE 'MISMATCH' END AS STATUS
            UNION ALL
            SELECT
                'MATCH_TEAM_STATS_SUMMARY grain = distinct MATCH_ID in MATCHES_SUMMARY_SILVER',
                (SELECT COUNT(*) FROM SILVER.MATCHES_SUMMARY_SILVER),
                (SELECT COUNT(*) FROM GOLD.MATCH_TEAM_STATS_SUMMARY),
                CASE WHEN (SELECT COUNT(*) FROM SILVER.MATCHES_SUMMARY_SILVER)
                        = (SELECT COUNT(*) FROM GOLD.MATCH_TEAM_STATS_SUMMARY)
                     THEN 'PASS' ELSE 'MISMATCH' END
            UNION ALL
            SELECT
                'CHAMPION_OVERVIEW count ≈ distinct champions in CHAMPIONS_REF_SILVER (excl. ID=0)',
                (SELECT COUNT(*) FROM SILVER.CHAMPIONS_REF_SILVER WHERE CHAMPION_ID != 0),
                (SELECT COUNT(*) FROM GOLD.CHAMPION_OVERVIEW),
                CASE WHEN (SELECT COUNT(*) FROM SILVER.CHAMPIONS_REF_SILVER WHERE CHAMPION_ID != 0)
                        = (SELECT COUNT(*) FROM GOLD.CHAMPION_OVERVIEW)
                     THEN 'PASS' ELSE 'MISMATCH' END
        """