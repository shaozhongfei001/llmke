#!/usr/bin/env python3
"""SQLite metadata catalog schema + helpers."""
from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQLITE_PATH = ROOT / "data" / "metadata" / "oracle_metadata_catalog.sqlite"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS db_snapshot (
  snapshot_id TEXT PRIMARY KEY,
  scan_started_at TEXT,
  scan_completed_at TEXT,
  database_name TEXT,
  service_name TEXT,
  oracle_version TEXT,
  current_user TEXT,
  current_schema TEXT,
  collector_version TEXT,
  code_commit TEXT,
  database_fingerprint TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS accessible_schema (
  snapshot_id TEXT,
  owner TEXT,
  object_count INTEGER,
  analysis_depth TEXT,
  PRIMARY KEY (snapshot_id, owner)
);

CREATE TABLE IF NOT EXISTS db_object (
  snapshot_id TEXT,
  database_name TEXT,
  owner TEXT,
  object_name TEXT,
  object_type TEXT,
  subobject_name TEXT,
  status TEXT,
  created TEXT,
  last_ddl_time TEXT,
  temporary TEXT,
  generated TEXT,
  secondary TEXT,
  edition_name TEXT,
  object_id INTEGER,
  data_object_id INTEGER,
  analysis_depth TEXT,
  PRIMARY KEY (snapshot_id, owner, object_type, object_name, COALESCE(subobject_name,''))
);

CREATE TABLE IF NOT EXISTS table_metadata (
  snapshot_id TEXT,
  owner TEXT,
  table_name TEXT,
  table_comment TEXT,
  tablespace_name TEXT,
  partitioned TEXT,
  temporary TEXT,
  num_rows INTEGER,
  blocks INTEGER,
  last_analyzed TEXT,
  row_count_source TEXT,
  PRIMARY KEY (snapshot_id, owner, table_name)
);

CREATE TABLE IF NOT EXISTS column_metadata (
  snapshot_id TEXT,
  owner TEXT,
  table_name TEXT,
  column_id INTEGER,
  column_name TEXT,
  data_type TEXT,
  data_length INTEGER,
  data_precision INTEGER,
  data_scale INTEGER,
  nullable TEXT,
  default_value TEXT,
  char_used TEXT,
  char_length INTEGER,
  column_comment TEXT,
  num_distinct INTEGER,
  num_nulls INTEGER,
  low_value TEXT,
  high_value TEXT,
  last_analyzed TEXT,
  PRIMARY KEY (snapshot_id, owner, table_name, column_name)
);

CREATE TABLE IF NOT EXISTS constraint_metadata (
  snapshot_id TEXT,
  owner TEXT,
  constraint_name TEXT,
  constraint_type TEXT,
  table_name TEXT,
  status TEXT,
  search_condition TEXT,
  r_owner TEXT,
  r_constraint_name TEXT,
  columns_csv TEXT,
  PRIMARY KEY (snapshot_id, owner, constraint_name)
);

CREATE TABLE IF NOT EXISTS index_metadata (
  snapshot_id TEXT,
  owner TEXT,
  index_name TEXT,
  table_name TEXT,
  uniqueness TEXT,
  status TEXT,
  columns_csv TEXT,
  PRIMARY KEY (snapshot_id, owner, index_name)
);

CREATE TABLE IF NOT EXISTS object_dependency (
  snapshot_id TEXT,
  owner TEXT,
  name TEXT,
  type TEXT,
  referenced_owner TEXT,
  referenced_name TEXT,
  referenced_type TEXT,
  dependency_type TEXT,
  PRIMARY KEY (snapshot_id, owner, name, type, referenced_owner, referenced_name, referenced_type)
);

CREATE TABLE IF NOT EXISTS program_unit (
  snapshot_id TEXT,
  owner TEXT,
  object_name TEXT,
  object_type TEXT,
  status TEXT,
  source_hash TEXT,
  source_length INTEGER,
  source_status TEXT,
  created TEXT,
  last_ddl_time TEXT,
  PRIMARY KEY (snapshot_id, owner, object_name, object_type)
);

CREATE TABLE IF NOT EXISTS program_argument (
  snapshot_id TEXT,
  owner TEXT,
  package_name TEXT,
  object_name TEXT,
  overload INTEGER,
  subprogram_id INTEGER,
  argument_name TEXT,
  position INTEGER,
  sequence INTEGER,
  data_level INTEGER,
  data_type TEXT,
  in_out TEXT,
  defaulted TEXT,
  type_owner TEXT,
  type_name TEXT,
  PRIMARY KEY (snapshot_id, owner, object_name, COALESCE(package_name,''), COALESCE(argument_name,''), position, COALESCE(overload,0), data_level)
);

CREATE TABLE IF NOT EXISTS source_code (
  snapshot_id TEXT,
  owner TEXT,
  object_name TEXT,
  object_type TEXT,
  source_line INTEGER,
  source_text TEXT,
  source_hash TEXT,
  PRIMARY KEY (snapshot_id, owner, object_name, object_type, source_line)
);

CREATE TABLE IF NOT EXISTS sql_statement (
  snapshot_id TEXT,
  statement_id TEXT PRIMARY KEY,
  owner TEXT,
  object_name TEXT,
  object_type TEXT,
  subprogram TEXT,
  statement_kind TEXT,
  dynamic_class TEXT,
  start_line INTEGER,
  end_line INTEGER,
  sql_text TEXT,
  parse_status TEXT,
  target_owner TEXT,
  target_object TEXT
);

CREATE TABLE IF NOT EXISTS object_lineage (
  snapshot_id TEXT,
  lineage_id TEXT PRIMARY KEY,
  source_owner TEXT,
  source_object TEXT,
  producer_owner TEXT,
  producer_object TEXT,
  producer_type TEXT,
  target_owner TEXT,
  target_object TEXT,
  evidence_statement_id TEXT,
  confidence TEXT
);

CREATE TABLE IF NOT EXISTS field_lineage (
  snapshot_id TEXT,
  lineage_id TEXT PRIMARY KEY,
  source_owner TEXT,
  source_object TEXT,
  source_column TEXT,
  transformation_type TEXT,
  transformation_expression TEXT,
  filters TEXT,
  group_by TEXT,
  partition_by TEXT,
  target_owner TEXT,
  target_object TEXT,
  target_column TEXT,
  producer_owner TEXT,
  producer_object TEXT,
  evidence_statement_id TEXT,
  code_start_line INTEGER,
  code_end_line INTEGER,
  source_hash TEXT,
  confidence TEXT
);

CREATE TABLE IF NOT EXISTS metric_definition (
  snapshot_id TEXT,
  metric_id TEXT,
  metric_name_cn TEXT,
  metric_name_en TEXT,
  metric_status TEXT,
  confidence_level TEXT,
  business_definition TEXT,
  formula_expression TEXT,
  numerator_definition TEXT,
  denominator_definition TEXT,
  statistical_grain TEXT,
  unit TEXT,
  source_tables TEXT,
  source_columns TEXT,
  target_schema TEXT,
  target_table TEXT,
  target_column TEXT,
  producer_object_owner TEXT,
  producer_object_name TEXT,
  producer_object_type TEXT,
  code_start_line INTEGER,
  code_end_line INTEGER,
  source_hash TEXT,
  owner_decision_ids TEXT,
  existing_metric_mapping TEXT,
  business_confirmation_required INTEGER,
  PRIMARY KEY (snapshot_id, metric_id)
);

CREATE TABLE IF NOT EXISTS derived_field (
  snapshot_id TEXT,
  derived_field_id TEXT PRIMARY KEY,
  target_owner TEXT,
  target_object TEXT,
  target_column TEXT,
  target_comment TEXT,
  business_name_cn TEXT,
  business_description_cn TEXT,
  field_category TEXT,
  source_fields TEXT,
  transformation_expression TEXT,
  transformation_type TEXT,
  producer_program TEXT,
  code_line_range TEXT,
  source_hash TEXT,
  confidence_level TEXT,
  ambiguities TEXT
);

CREATE TABLE IF NOT EXISTS business_description (
  snapshot_id TEXT,
  owner TEXT,
  object_name TEXT,
  object_type TEXT,
  subprogram TEXT,
  description_path TEXT,
  source_hash TEXT,
  PRIMARY KEY (snapshot_id, owner, object_name, object_type, COALESCE(subprogram,''))
);

CREATE TABLE IF NOT EXISTS analysis_issue (
  snapshot_id TEXT,
  issue_id TEXT PRIMARY KEY,
  severity TEXT,
  category TEXT,
  object_ref TEXT,
  message TEXT,
  status TEXT
);

CREATE TABLE IF NOT EXISTS evidence_artifact (
  snapshot_id TEXT,
  path TEXT PRIMARY KEY,
  kind TEXT,
  sha256 TEXT,
  notes TEXT
);
"""


def connect_db(path: Path | None = None, reset: bool = False) -> sqlite3.Connection:
    p = path or SQLITE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    if reset and p.exists():
        p.unlink()
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    # SQLite doesn't like COALESCE in PK — use simplified DDL via executescript carefully
    # Recreate with workable PKs
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS db_snapshot (
          snapshot_id TEXT PRIMARY KEY,
          scan_started_at TEXT,
          scan_completed_at TEXT,
          database_name TEXT,
          service_name TEXT,
          oracle_version TEXT,
          current_user TEXT,
          current_schema TEXT,
          collector_version TEXT,
          code_commit TEXT,
          database_fingerprint TEXT,
          notes TEXT
        );
        CREATE TABLE IF NOT EXISTS accessible_schema (
          snapshot_id TEXT, owner TEXT, object_count INTEGER, analysis_depth TEXT,
          PRIMARY KEY (snapshot_id, owner)
        );
        CREATE TABLE IF NOT EXISTS db_object (
          snapshot_id TEXT, database_name TEXT, owner TEXT, object_name TEXT,
          object_type TEXT, subobject_name TEXT, status TEXT, created TEXT,
          last_ddl_time TEXT, temporary TEXT, generated TEXT, secondary TEXT,
          edition_name TEXT, object_id INTEGER, data_object_id INTEGER,
          analysis_depth TEXT,
          PRIMARY KEY (snapshot_id, owner, object_type, object_name, subobject_name)
        );
        CREATE TABLE IF NOT EXISTS table_metadata (
          snapshot_id TEXT, owner TEXT, table_name TEXT, table_comment TEXT,
          tablespace_name TEXT, partitioned TEXT, temporary TEXT, num_rows INTEGER,
          blocks INTEGER, last_analyzed TEXT, row_count_source TEXT,
          PRIMARY KEY (snapshot_id, owner, table_name)
        );
        CREATE TABLE IF NOT EXISTS column_metadata (
          snapshot_id TEXT, owner TEXT, table_name TEXT, column_id INTEGER,
          column_name TEXT, data_type TEXT, data_length INTEGER, data_precision INTEGER,
          data_scale INTEGER, nullable TEXT, default_value TEXT, char_used TEXT,
          char_length INTEGER, column_comment TEXT, num_distinct INTEGER,
          num_nulls INTEGER, low_value BLOB, high_value BLOB, last_analyzed TEXT,
          PRIMARY KEY (snapshot_id, owner, table_name, column_name)
        );
        CREATE TABLE IF NOT EXISTS constraint_metadata (
          snapshot_id TEXT, owner TEXT, constraint_name TEXT, constraint_type TEXT,
          table_name TEXT, status TEXT, search_condition TEXT, r_owner TEXT,
          r_constraint_name TEXT, columns_csv TEXT,
          PRIMARY KEY (snapshot_id, owner, constraint_name)
        );
        CREATE TABLE IF NOT EXISTS index_metadata (
          snapshot_id TEXT, owner TEXT, index_name TEXT, table_name TEXT,
          uniqueness TEXT, status TEXT, columns_csv TEXT,
          PRIMARY KEY (snapshot_id, owner, index_name)
        );
        CREATE TABLE IF NOT EXISTS object_dependency (
          snapshot_id TEXT, owner TEXT, name TEXT, type TEXT,
          referenced_owner TEXT, referenced_name TEXT, referenced_type TEXT,
          dependency_type TEXT,
          PRIMARY KEY (snapshot_id, owner, name, type, referenced_owner, referenced_name, referenced_type)
        );
        CREATE TABLE IF NOT EXISTS program_unit (
          snapshot_id TEXT, owner TEXT, object_name TEXT, object_type TEXT,
          status TEXT, source_hash TEXT, source_length INTEGER, source_status TEXT,
          created TEXT, last_ddl_time TEXT,
          PRIMARY KEY (snapshot_id, owner, object_name, object_type)
        );
        CREATE TABLE IF NOT EXISTS program_argument (
          snapshot_id TEXT, owner TEXT, package_name TEXT, object_name TEXT,
          overload INTEGER, subprogram_id INTEGER, argument_name TEXT,
          position INTEGER, sequence_no INTEGER, data_level INTEGER, data_type TEXT,
          in_out TEXT, defaulted TEXT, type_owner TEXT, type_name TEXT,
          PRIMARY KEY (snapshot_id, owner, object_name, package_name, argument_name, position, overload, data_level)
        );
        CREATE TABLE IF NOT EXISTS source_code (
          snapshot_id TEXT, owner TEXT, object_name TEXT, object_type TEXT,
          source_line INTEGER, source_text TEXT, source_hash TEXT,
          PRIMARY KEY (snapshot_id, owner, object_name, object_type, source_line)
        );
        CREATE TABLE IF NOT EXISTS sql_statement (
          snapshot_id TEXT, statement_id TEXT PRIMARY KEY, owner TEXT, object_name TEXT,
          object_type TEXT, subprogram TEXT, statement_kind TEXT, dynamic_class TEXT,
          start_line INTEGER, end_line INTEGER, sql_text TEXT, parse_status TEXT,
          target_owner TEXT, target_object TEXT
        );
        CREATE TABLE IF NOT EXISTS object_lineage (
          snapshot_id TEXT, lineage_id TEXT PRIMARY KEY, source_owner TEXT,
          source_object TEXT, producer_owner TEXT, producer_object TEXT,
          producer_type TEXT, target_owner TEXT, target_object TEXT,
          evidence_statement_id TEXT, confidence TEXT
        );
        CREATE TABLE IF NOT EXISTS field_lineage (
          snapshot_id TEXT, lineage_id TEXT PRIMARY KEY, source_owner TEXT,
          source_object TEXT, source_column TEXT, transformation_type TEXT,
          transformation_expression TEXT, filters TEXT, group_by TEXT,
          partition_by TEXT, target_owner TEXT, target_object TEXT,
          target_column TEXT, producer_owner TEXT, producer_object TEXT,
          evidence_statement_id TEXT, code_start_line INTEGER, code_end_line INTEGER,
          source_hash TEXT, confidence TEXT
        );
        CREATE TABLE IF NOT EXISTS metric_definition (
          snapshot_id TEXT, metric_id TEXT, metric_name_cn TEXT, metric_name_en TEXT,
          metric_status TEXT, confidence_level TEXT, confidence_source TEXT DEFAULT '',
          business_definition TEXT,
          formula_expression TEXT, numerator_definition TEXT, denominator_definition TEXT,
          statistical_grain TEXT, unit TEXT, source_tables TEXT, source_columns TEXT,
          target_schema TEXT, target_table TEXT, target_column TEXT,
          producer_object_owner TEXT, producer_object_name TEXT, producer_object_type TEXT,
          code_start_line INTEGER, code_end_line INTEGER, source_hash TEXT,
          owner_decision_ids TEXT, existing_metric_mapping TEXT,
          business_confirmation_required INTEGER,
          PRIMARY KEY (snapshot_id, metric_id)
        );
        CREATE TABLE IF NOT EXISTS derived_field (
          snapshot_id TEXT, derived_field_id TEXT PRIMARY KEY, target_owner TEXT,
          target_object TEXT, target_column TEXT, target_comment TEXT,
          business_name_cn TEXT, business_description_cn TEXT, field_category TEXT,
          source_fields TEXT, transformation_expression TEXT, transformation_type TEXT,
          producer_program TEXT, code_line_range TEXT, source_hash TEXT,
          confidence_level TEXT, ambiguities TEXT
        );
        CREATE TABLE IF NOT EXISTS business_description (
          snapshot_id TEXT, owner TEXT, object_name TEXT, object_type TEXT,
          subprogram TEXT, description_path TEXT, source_hash TEXT,
          PRIMARY KEY (snapshot_id, owner, object_name, object_type, subprogram)
        );
        CREATE TABLE IF NOT EXISTS analysis_issue (
          snapshot_id TEXT, issue_id TEXT PRIMARY KEY, severity TEXT, category TEXT,
          object_ref TEXT, message TEXT, status TEXT
        );
        CREATE TABLE IF NOT EXISTS evidence_artifact (
          snapshot_id TEXT, path TEXT PRIMARY KEY, kind TEXT, sha256 TEXT, notes TEXT
        );
        """
    )
    # additive migrations
    cols = {r[1] for r in conn.execute("PRAGMA table_info(metric_definition)")}
    if cols and "confidence_source" not in cols:
        conn.execute(
            "ALTER TABLE metric_definition ADD COLUMN confidence_source TEXT DEFAULT ''"
        )
    return conn
