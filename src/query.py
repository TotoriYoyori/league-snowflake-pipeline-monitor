import pandas as pd


# --------------- BASE MONITOR QUERY ---------------
class MonitorQuery:
    """One pipeline monitoring check: live query, mock file, and title/description."""
    mock_file_name: str = ""
    title_en: str = ""
    title_zh: str = ""
    desc_en: str = ""

    def build(self) -> str:
        raise NotImplementedError

    def status(self, df: pd.DataFrame) -> tuple[str, str] | None:
        """Optional (status_text, level) shown as a pill on this check's card.
        `level` is one of "ok" / "warn" / "fail". None = no pill."""
        return None


# --------------- SEED (models/_infra/monitor.ipynb) ---------------
class SeedObjectInventory(MonitorQuery):
    mock_file_name = "seed_object_inventory"
    title_en = "Object Inventory"
    title_zh = "对象清单"
    desc_en = "All registered objects in the SEED schema."

    def build(self) -> str:
        return """
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
    title_en = "Stages"
    title_zh = "暂存区"
    desc_en = "Stages registered under SEED."

    def build(self) -> str:
        return "SHOW STAGES IN SCHEMA LEAGUE_RECORDS.SEED"


class SeedProcedures(MonitorQuery):
    mock_file_name = "seed_procedures"
    title_en = "Procedures"
    title_zh = "存储过程"
    desc_en = "VALIDATE_SEED_UPLOAD / SIMULATE_DAILY_LOAD registration."

    def build(self) -> str:
        return "SHOW PROCEDURES IN SCHEMA LEAGUE_RECORDS.SEED"


class SeedRowCountValidation(MonitorQuery):
    mock_file_name = "seed_row_count_validation"
    title_en = "CSV vs Table Row Count Reconciliation"
    title_zh = "CSV 与表行数核对"
    desc_en = "Verifies the base COPY INTO for all 5 source datasets matched the uploaded CSVs."

    def build(self) -> str:
        return """
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

    def status(self, df: pd.DataFrame) -> tuple[str, str] | None:
        if "STATUS" not in df.columns:
            return None

        ok = int(df["STATUS"].isin(("PASS",)).sum())
        total = len(df)
        level = "ok" if ok == total and total > 0 else ("warn" if ok > 0 else "fail")
        return f"{ok}/{total} PASS", level


class SeedStageFiles(MonitorQuery):
    mock_file_name = "seed_stage_files"
    title_en = "Stage File Listing"
    title_zh = "暂存区文件列表"
    desc_en = "Files currently present in @SEED.SEED_UPLOAD_STG."

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
    mock_file_name = "seed_load_state"
    title_en = "Simulated Daily Load State"
    title_zh = "模拟每日加载状态"
    desc_en = "Tracks the simulated daily ingestion pointer. DAYS_REMAINING = 0 means fully loaded."

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
    title_en = "Matches Ingested per Date (recent)"
    title_zh = "近期每日入库比赛数"
    desc_en = "Most recent dates in the simulated source index."

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
    title_en = "Object Inventory"
    title_zh = "对象清单"
    desc_en = "Tables/views in the BRONZE schema."

    def build(self) -> str:
        return """
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
    title_en = "Stages"
    title_zh = "暂存区"
    desc_en = "Stages registered under BRONZE."

    def build(self) -> str:
        return "SHOW STAGES IN SCHEMA LEAGUE_RECORDS.BRONZE"


class BronzePipes(MonitorQuery):
    mock_file_name = "bronze_pipes"
    title_en = "Pipes"
    title_zh = "管道"
    desc_en = "Snowpipes registered under BRONZE for continuous file ingestion."

    def build(self) -> str:
        return "SHOW PIPES IN SCHEMA LEAGUE_RECORDS.BRONZE"


class BronzeStreams(MonitorQuery):
    mock_file_name = "bronze_streams"
    title_en = "Streams"
    title_zh = "数据流"
    desc_en = "Streams registered under BRONZE, tracking change data for downstream silver tasks."

    def build(self) -> str:
        return "SHOW STREAMS IN SCHEMA LEAGUE_RECORDS.BRONZE"


class BronzeFileFormats(MonitorQuery):
    mock_file_name = "bronze_file_formats"
    title_en = "File Formats"
    title_zh = "文件格式"
    desc_en = "File formats registered under BRONZE, used by pipes and COPY INTO to parse staged files."

    def build(self) -> str:
        return "SHOW FILE FORMATS IN SCHEMA LEAGUE_RECORDS.BRONZE"


class BronzeRowCounts(MonitorQuery):
    mock_file_name = "bronze_row_counts"
    title_en = "Row Counts & Health"
    title_zh = "行数与健康度"
    desc_en = "Row counts across all 5 bronze tables."

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
    title_en = "Pipe Status & Ingestion History"
    title_zh = "管道状态与入库历史"
    desc_en = "Current pipe execution state and pending file counts."

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

    def status(self, df: pd.DataFrame) -> tuple[str, str] | None:
        pending = int(df["PENDING_FILE_COUNT"].sum()) if not df.empty else 0
        return (f"{pending} pending" if pending else "0 pending"), ("ok" if pending == 0 else "warn")


class BronzeCopyHistory(MonitorQuery):
    mock_file_name = "bronze_copy_history"
    title_en = "Copy History (14 days)"
    title_zh = "拷贝历史（14天）"
    desc_en = "Recent COPY INTO executions, rows loaded/parsed, and errors."

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

    def status(self, df: pd.DataFrame) -> tuple[str, str] | None:
        errors = int(df["ERROR_COUNT"].sum()) if "ERROR_COUNT" in df.columns else 0
        return (f"{errors} errors" if errors else "0 errors"), ("ok" if errors == 0 else "fail")


class BronzeStageFiles(MonitorQuery):
    mock_file_name = "bronze_stage_files"
    title_en = "Stage File Inspection"
    title_zh = "暂存区文件检查"
    desc_en = "Files currently present in each bronze stage."

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
    title_en = "Stream State"
    title_zh = "数据流状态"
    desc_en = "Checks if any bronze streams have unconsumed data pending for silver."

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

    def status(self, df: pd.DataFrame) -> tuple[str, str] | None:
        has_pending = bool(df["HAS_DATA"].any()) if "HAS_DATA" in df.columns else False
        return ("data pending" if has_pending else "all consumed"), ("warn" if has_pending else "ok")


# --------------- SILVER (models/silver/monitor.ipynb) ---------------
class SilverObjectInventory(MonitorQuery):
    """Special-shaped: multi-query, handled by its own loader in data.py."""

    title_en = "Object Inventory"
    title_zh = "对象清单"
    desc_en = "Tables, views, and tasks in the SILVER schema."

    def build_tables(self) -> str:
        return "SHOW TABLES IN SCHEMA LEAGUE_RECORDS.SILVER"

    def build_views(self) -> str:
        return "SHOW VIEWS IN SCHEMA LEAGUE_RECORDS.SILVER"

    def build_tasks(self) -> str:
        return "SHOW TASKS IN SCHEMA LEAGUE_RECORDS.SILVER"


class SilverTaskHistory(MonitorQuery):
    mock_file_name = "silver_task_history"
    title_en = "Task History (24h)"
    title_zh = "任务执行历史（24小时）"
    desc_en = "Per-run task execution history feeding data into silver."

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

    def status(self, df: pd.DataFrame) -> tuple[str, str] | None:
        failed = int((df["STATE"] != "SUCCEEDED").sum()) if "STATE" in df.columns else 0
        return (f"{failed} non-success states" if failed else "all succeeded"), ("fail" if failed else "ok")


class SilverTaskSummary(MonitorQuery):
    mock_file_name = "silver_task_summary"
    title_en = "Task Success/Failure Summary"
    title_zh = "任务成功/失败汇总"
    desc_en = "Run counts and average duration, grouped by task and state."

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

    def status(self, df: pd.DataFrame) -> tuple[str, str] | None:
        failed = int((df["STATE"] != "SUCCEEDED").sum()) if "STATE" in df.columns else 0
        return (f"{failed} non-success states" if failed else "all succeeded"), ("fail" if failed else "ok")


class SilverStreamState(MonitorQuery):
    mock_file_name = "silver_stream_state"
    title_en = "Stream Pending Data Status"
    title_zh = "数据流待处理状态"
    desc_en = "Whether upstream bronze streams still have unconsumed data."

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

    def status(self, df: pd.DataFrame) -> tuple[str, str] | None:
        has_pending = bool(df["HAS_DATA"].any()) if "HAS_DATA" in df.columns else False
        return ("data pending" if has_pending else "all consumed"), ("warn" if has_pending else "ok")


class SilverRowCounts(MonitorQuery):
    mock_file_name = "silver_row_counts"
    title_en = "Silver Row Counts & Freshness"
    title_zh = "白银层行数与新鲜度"
    desc_en = "Row counts, size, and LAST_ALTERED per silver table."

    def build(self) -> str:
        return """
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
    mock_file_name = "silver_vs_gold_counts"
    title_en = "Silver vs Gold Row Count Comparison"
    title_zh = "白银层与黄金层行数比对"
    desc_en = "Outgoing data check: row count parity between silver and the gold tables derived from it."

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

    def status(self, df: pd.DataFrame) -> tuple[str, str] | None:
        diff_total = int(df["DIFF"].abs().sum()) if "DIFF" in df.columns else 0
        return ("parity" if diff_total == 0 else f"diff={diff_total}"), ("ok" if diff_total == 0 else "warn")


# --------------- GOLD (models/gold/monitor.ipynb) ---------------
class GoldObjectInventory(MonitorQuery):
    mock_file_name = "gold_object_inventory"
    title_en = "Object Inventory"
    title_zh = "对象清单"
    desc_en = "All 5 dynamic tables under GOLD."

    def build(self) -> str:
        return "SHOW DYNAMIC TABLES IN SCHEMA LEAGUE_RECORDS.GOLD"


class GoldDtFreshness(MonitorQuery):
    """Special-shaped: depends on a preceding query in the same session, handled by its own loader in data.py."""

    mock_file_name = "gold_dt_freshness"
    title_en = "Dynamic Table Freshness Check"
    title_zh = "动态表新鲜度检查"
    desc_en = (
        "Scheduling state, target lag, and actual lag per dynamic table. Note: in a simulated daily-load "
        "pipeline, tables will show BEHIND SCHEDULE between simulated loads because this pipeline is not real..."
    )

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

    def status(self, df: pd.DataFrame) -> tuple[str, str] | None:
        if "FRESHNESS_STATUS" not in df.columns:
            return None

        behind = int((~df["FRESHNESS_STATUS"].astype(str).str.contains("ON TRACK")).sum())
        return (f"{behind} not on track" if behind else "all on track"), ("warn" if behind else "ok")


class GoldRefreshHistory(MonitorQuery):
    mock_file_name = "gold_refresh_history"
    title_en = "Refresh History (recent)"
    title_zh = "刷新历史（近期）"
    desc_en = "Most recent dynamic table refreshes, duration, and row deltas."

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

    def status(self, df: pd.DataFrame) -> tuple[str, str] | None:
        failures = int((df["REFRESH_STATE"] != "SUCCEEDED").sum()) if "REFRESH_STATE" in df.columns else 0
        return (f"{failures} failures" if failures else "all succeeded"), ("fail" if failures else "ok")


class GoldGrainValidation(MonitorQuery):
    mock_file_name = "gold_grain_validation"
    title_en = "Silver → Gold Grain Validation"
    title_zh = "白银到黄金层粒度校验"
    desc_en = "Confirms each gold table's row count matches the expected grain derived from its silver source."

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

    def status(self, df: pd.DataFrame) -> tuple[str, str] | None:
        fails = int((df["STATUS"] != "PASS").sum()) if "STATUS" in df.columns else 0
        return (f"{fails} mismatches" if fails else "all pass"), ("fail" if fails else "ok")


# --------------- LAYER REGISTRY ---------------
# Each layer maps to (label_en, label_zh, rows), where `rows` is a list of
# rows to render top-to-bottom; a row with 2+ checks renders as that many
# side-by-side columns (matching the current UI exactly), a row with 1 check
# renders full-width.

# SilverObjectInventory and GoldDtFreshness are intentionally excluded. They have special shapes I can't refactor for now...
LAYERS = {
    "seed": ("Seed", "种子层", [
        [SeedLoadState()],
        [SeedObjectInventory()],
        [SeedStages()],
        [SeedProcedures()],
        [SeedRowCountValidation()],
        [SeedStageFiles()],
        [SeedDateIndex()],
    ]),
    "bronze": ("Bronze", "青铜层", [
        [BronzeObjectInventory()],
        [BronzeStages(), BronzePipes()],
        [BronzeStreams(), BronzeFileFormats()],
        [BronzeRowCounts()],
        [BronzePipeStatus()],
        [BronzeCopyHistory()],
        [BronzeStageFiles()],
        [BronzeStreamState()],
    ]),
    "silver": ("Silver", "白银层", [
        [SilverTaskHistory()],
        [SilverTaskSummary()],
        [SilverStreamState()],
        [SilverRowCounts()],
        [SilverVsGoldCounts()],
    ]),
    "gold": ("Gold", "黄金层", [
        [GoldObjectInventory()],
        [GoldRefreshHistory()],
        [GoldGrainValidation()],
    ]),
}
