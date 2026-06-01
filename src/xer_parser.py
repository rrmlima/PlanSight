"""
Core Primavera P6 XER parser for the Vision local app.

XER files are tab-separated text exports. Their relational blocks are usually
encoded as:

    %T\tTABLE_NAME
    %F\tfield_1\tfield_2\t...
    %R\tvalue_1\tvalue_2\t...

This module parses those blocks into pandas DataFrames and exposes the critical
Sprint 1 tables required by the EVM/DCMA engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Optional, Union

import pandas as pd

PathLike = Union[str, Path]


@dataclass
class XERParser:
    """Parse a Primavera P6 .xer file into pandas DataFrames.

    Parameters
    ----------
    file_path:
        Path to the .xer file. The parser reads locally only; no database,
        server, Docker, or external service is required.
    encoding:
        Text encoding used by the XER export. Primavera files are commonly
        UTF-8, CP1252, or Latin-1. The default keeps modern exports simple.
    keep_all_tables:
        If True, parse every table found in the file into ``self.tables``.
        Critical tables are always accessible through convenience properties.
    """

    file_path: PathLike
    encoding: str = "utf-8"
    keep_all_tables: bool = True
    tables: Dict[str, pd.DataFrame] = field(default_factory=dict, init=False)

    CRITICAL_TABLES = ("TASK", "PROJWBS", "TASKACTV", "TASKPRED")

    def parse(self) -> Dict[str, pd.DataFrame]:
        """Parse the XER file and return a dict of table name -> DataFrame."""
        path = Path(self.file_path)
        if not path.exists():
            raise FileNotFoundError(f"XER file not found: {path}")

        lines = self._read_lines_with_fallback(path)
        return self._build_tables_from_lines(lines)

    def parse_text(self, text: str) -> Dict[str, pd.DataFrame]:
        """Parse XER text already loaded in memory."""
        return self._build_tables_from_lines(text.splitlines())

    def parse_bytes(self, content: bytes) -> Dict[str, pd.DataFrame]:
        """Parse XER bytes already loaded in memory, with encoding fallback."""
        encodings = [self.encoding, "utf-8-sig", "cp1252", "latin-1"]
        seen: set[str] = set()

        for encoding in encodings:
            if encoding in seen:
                continue
            seen.add(encoding)
            try:
                text = content.decode(encoding=encoding)
                return self.parse_text(text)
            except UnicodeDecodeError:
                continue

        raise UnicodeDecodeError(
            self.encoding,
            content,
            0,
            1,
            f"Could not decode in-memory XER content with {encodings}",
        )

    def _build_tables_from_lines(self, lines: Iterable[str]) -> Dict[str, pd.DataFrame]:
        raw_tables = self._parse_blocks(lines)

        self.tables = {
            table_name: self._records_to_dataframe(fields, rows)
            for table_name, (fields, rows) in raw_tables.items()
            if self.keep_all_tables or table_name in self.CRITICAL_TABLES
        }

        # Ensure critical attributes always resolve to DataFrames, even when
        # the XER export does not contain that table.
        for table_name in self.CRITICAL_TABLES:
            self.tables.setdefault(table_name, pd.DataFrame())

        return self.tables

    def _read_lines_with_fallback(self, path: Path) -> list[str]:
        """Read text lines, retrying common XER encodings if needed."""
        encodings = [self.encoding, "utf-8-sig", "cp1252", "latin-1"]
        seen: set[str] = set()

        for encoding in encodings:
            if encoding in seen:
                continue
            seen.add(encoding)
            try:
                return path.read_text(encoding=encoding).splitlines()
            except UnicodeDecodeError:
                continue

        # latin-1 should never fail, but keep a clear defensive error.
        raise UnicodeDecodeError(
            self.encoding,
            b"",
            0,
            1,
            f"Could not decode {path} with {encodings}",
        )

    def _parse_blocks(self, lines: Iterable[str]) -> Dict[str, tuple[list[str], list[list[str]]]]:
        """Parse %T/%F/%R blocks into raw fields and rows."""
        tables: Dict[str, tuple[list[str], list[list[str]]]] = {}
        current_table: Optional[str] = None
        current_fields: list[str] = []

        for raw_line in lines:
            if not raw_line:
                continue

            parts = raw_line.rstrip("\n\r").split("\t")
            marker = parts[0]

            if marker == "%T":
                current_table = parts[1].strip() if len(parts) > 1 else None
                current_fields = []
                if current_table:
                    tables.setdefault(current_table, ([], []))

            elif marker == "%F" and current_table:
                current_fields = parts[1:]
                existing_rows = tables.get(current_table, ([], []))[1]
                tables[current_table] = (current_fields, existing_rows)

            elif marker == "%R" and current_table:
                fields, rows = tables.setdefault(current_table, (current_fields, []))
                if not fields and current_fields:
                    fields = current_fields
                rows.append(parts[1:])
                tables[current_table] = (fields, rows)

            # Ignore metadata/header/footer lines such as ERMHDR, %E, etc.

        return tables

    def _records_to_dataframe(self, fields: list[str], rows: list[list[str]]) -> pd.DataFrame:
        """Build a DataFrame, normalize row lengths, dates, and numerics."""
        if not fields:
            return pd.DataFrame()

        normalized_rows = [self._normalize_row_length(row, len(fields)) for row in rows]
        df = pd.DataFrame(normalized_rows, columns=fields)

        if df.empty:
            return df

        df = df.replace({"": pd.NA})
        df = self._convert_date_columns(df)
        df = self._convert_numeric_columns(df)
        return df

    @staticmethod
    def _normalize_row_length(row: list[str], expected_length: int) -> list[str]:
        """Pad short rows and merge overflow defensively.

        XER rows should match the field count. This keeps parsing resilient to
        imperfect exports without crashing the whole import.
        """
        if len(row) == expected_length:
            return row
        if len(row) < expected_length:
            return row + [""] * (expected_length - len(row))
        return row[: expected_length - 1] + ["\t".join(row[expected_length - 1 :])]

    @staticmethod
    def _convert_date_columns(df: pd.DataFrame) -> pd.DataFrame:
        date_tokens = ("date", "_dt", "time")
        for column in df.columns:
            col_lower = column.lower()
            if any(token in col_lower for token in date_tokens):
                parsed = pd.to_datetime(df[column], errors="coerce")
                # Avoid destroying non-date identifier columns that happen to
                # contain a token. Convert only if at least one value parsed.
                if parsed.notna().any():
                    df[column] = parsed
        return df

    @staticmethod
    def _convert_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
        for column in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[column]):
                continue

            series = df[column]
            non_null = series.dropna()
            if non_null.empty:
                continue

            numeric = pd.to_numeric(series, errors="coerce")
            if numeric.notna().sum() == len(non_null):
                df[column] = numeric
        return df

    def get_table(self, table_name: str) -> pd.DataFrame:
        """Return a parsed table by name, or an empty DataFrame if absent."""
        if not self.tables:
            self.parse()
        return self.tables.get(table_name.upper(), pd.DataFrame())

    @property
    def tasks(self) -> pd.DataFrame:
        """TASK table: Primavera activities."""
        return self.get_table("TASK")

    @property
    def wbs(self) -> pd.DataFrame:
        """PROJWBS table: WBS structure."""
        return self.get_table("PROJWBS")

    @property
    def taskactv(self) -> pd.DataFrame:
        """TASKACTV table: activity code assignments / EVM-related mapping data."""
        return self.get_table("TASKACTV")

    @property
    def taskpred(self) -> pd.DataFrame:
        """TASKPRED table: predecessor/successor relationships."""
        return self.get_table("TASKPRED")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parse a Primavera P6 .xer file.")
    parser.add_argument("xer_file", help="Path to the local .xer file")
    args = parser.parse_args()

    xer = XERParser(args.xer_file)
    xer.parse()

    print("Parsed critical table shapes:")
    print(f"TASK     : {xer.tasks.shape}")
    print(f"PROJWBS  : {xer.wbs.shape}")
    print(f"TASKACTV : {xer.taskactv.shape}")
    print(f"TASKPRED : {xer.taskpred.shape}")
