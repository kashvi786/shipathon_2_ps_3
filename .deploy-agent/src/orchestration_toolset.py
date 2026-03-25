import json
import logging
import os
import csv
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from pydantic import BaseModel
import asyncio

logger = logging.getLogger(__name__)

# Request Models
class DataFetchRequest(BaseModel):
    source: str
    retry_count: int = 0

class DataTransformRequest(BaseModel):
    data_id: str
    region: str = "all"
    retry_count: int = 0

class ChartGenerateRequest(BaseModel):
    transformed_data_id: str
    chart_type: str = "bar"
    retry_count: int = 0

class ReportComposeRequest(BaseModel):
    chart_id: str
    summary_text: str
    retry_count: int = 0

class EmailDispatchRequest(BaseModel):
    report_id: str
    recipient: str
    retry_count: int = 0


class ChartReadRequest(BaseModel):
    chart_id: str


class ReportReadRequest(BaseModel):
    report_id: str

class OrchestrationToolset:
    """Data Pipeline tools including fetch, transform, chart, and email"""

    def __init__(self):
        self.simulate_transient_failures = (
            os.getenv('SIMULATE_TRANSIENT_FAILURES', 'false').lower() == 'true'
        )
        default_csv_path = Path(__file__).resolve().parents[1] / 'sales_data.csv'
        default_output_dir = Path(__file__).resolve().parents[1] / 'output'
        self.csv_path = Path(os.getenv('DATA_SOURCE_CSV', str(default_csv_path))).expanduser()
        self.output_dir = Path(
            os.getenv('ORCHESTRATION_OUTPUT_DIR', str(default_output_dir))
        ).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw_data_store: dict[str, list[dict[str, Any]]] = {}
        self.transformed_data_store: dict[str, dict[str, Any]] = {}
        self.chart_store: dict[str, dict[str, Any]] = {}
        self.report_store: dict[str, dict[str, Any]] = {}

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:10]}"

    def _build_ascii_chart(self, region_totals: dict[str, float], chart_type: str) -> str:
        if not region_totals:
            return '(no chart data)'

        max_value = max(region_totals.values()) if region_totals else 0.0
        scale = 30 / max_value if max_value > 0 else 1
        chart_lines = [f'{chart_type.upper()} CHART (ASCII)']

        for region, value in sorted(region_totals.items()):
            bar_len = max(1, int(value * scale)) if value > 0 else 0
            bar = '█' * bar_len
            chart_lines.append(f'{region:>12} | {bar} {value:.2f}')

        return '\n'.join(chart_lines)

    def _resolve_chart_id(self, chart_id: str) -> tuple[str | None, str | None]:
        normalized = (chart_id or '').strip()
        if normalized in self.chart_store:
            return normalized, None

        placeholder_values = {'CHART_ID', 'chart_id', 'latest', ''}
        if normalized in placeholder_values:
            if not self.chart_store:
                return None, 'No charts available yet. Generate a chart first using chart_generator.'
            latest_chart_id = next(reversed(self.chart_store))
            return latest_chart_id, None

        available = ', '.join(self.chart_store.keys()) if self.chart_store else '(none)'
        return None, f'Unknown chart_id: {chart_id}. Available chart IDs: {available}'

    def _resolve_report_id(self, report_id: str) -> tuple[str | None, str | None]:
        normalized = (report_id or '').strip()
        if normalized in self.report_store:
            return normalized, None

        placeholder_values = {'REPORT_ID', 'report_id', 'latest', ''}
        if normalized in placeholder_values:
            if not self.report_store:
                return None, 'No reports available yet. Generate a report first using report_composer.'
            latest_report_id = next(reversed(self.report_store))
            return latest_report_id, None

        available = ', '.join(self.report_store.keys()) if self.report_store else '(none)'
        return None, f'Unknown report_id: {report_id}. Available report IDs: {available}'

    def _load_sales_rows(self) -> list[dict[str, Any]]:
        if not self.csv_path.exists():
            raise FileNotFoundError(f'CSV data source not found: {self.csv_path}')

        rows: list[dict[str, Any]] = []
        with self.csv_path.open('r', encoding='utf-8', newline='') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                region = (row.get('region') or '').strip()
                sales_value = row.get('sales')
                try:
                    sales = float(sales_value) if sales_value is not None else 0.0
                except ValueError:
                    sales = 0.0
                rows.append({'region': region, 'sales': sales})
        return rows

    async def data_fetcher(self, source: str, retry_count: int = 0) -> str:
        """Fetches data from a specified source (mock API).
        
        Args:
            source: The data source (e.g., 'sales_api')
            retry_count: Keep track of retries, use 0 for first attempt, 1 for second, etc.
        """
        await asyncio.sleep(0.5)
        # Optional simulation of transient rate-limit error on first attempt
        if self.simulate_transient_failures and retry_count == 0:
            return json.dumps({"status": "error", "message": "429 rate limit error"})

        source_lower = (source or '').lower()
        if source_lower in ('sales_api', 'sales', 'sales_data', 'sales_data.csv'):
            source_label = 'sales_data.csv'
        else:
            source_label = source or 'sales_data.csv'

        rows = self._load_sales_rows()
        data_id = self._new_id('raw_data')
        self.raw_data_store[data_id] = rows
        return json.dumps(
            {
                "status": "success",
                "data_id": data_id,
                "source": source_label,
                "row_count": len(rows),
            }
        )

    async def data_transformer(self, data_id: str, region: str = "all", retry_count: int = 0) -> str:
        """Cleans and transforms fetched data by region.
        
        Args:
            data_id: ID of the raw data to transform
            region: The region to summarise by
            retry_count: Keep track of retries.
        """
        await asyncio.sleep(0.5)
        if data_id not in self.raw_data_store:
            return json.dumps({"status": "error", "message": f"Unknown data_id: {data_id}"})

        rows = self.raw_data_store[data_id]
        requested_region = (region or 'all').strip().lower()

        if requested_region != 'all':
            filtered_rows = [
                row for row in rows if row['region'].strip().lower() == requested_region
            ]
        else:
            filtered_rows = rows

        if not filtered_rows:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"No data rows found for region '{region}'",
                }
            )

        region_totals: dict[str, float] = {}
        for row in filtered_rows:
            region_name = row['region']
            region_totals[region_name] = region_totals.get(region_name, 0.0) + float(
                row['sales']
            )

        transformed_data_id = self._new_id('tx_data')
        transformed_payload = {
            'region_totals': region_totals,
            'row_count': len(filtered_rows),
            'region': requested_region,
        }
        self.transformed_data_store[transformed_data_id] = transformed_payload

        return json.dumps(
            {
                "status": "success",
                "transformed_data_id": transformed_data_id,
                "row_count": len(filtered_rows),
            }
        )

    async def chart_generator(self, transformed_data_id: str, chart_type: str = "bar", retry_count: int = 0) -> str:
        """Generates a summary chart from transformed data.
        
        Args:
            transformed_data_id: ID of the transformed data
            chart_type: Type of chart (e.g., 'bar', 'pie')
            retry_count: Keep track of retries.
        """
        await asyncio.sleep(0.5)
        # Optional simulation of malformed data error on first attempt
        if self.simulate_transient_failures and retry_count == 0:
            return json.dumps({"status": "error", "message": "malformed data"})

        if transformed_data_id not in self.transformed_data_store:
            return json.dumps(
                {
                    "status": "error",
                    "message": f"Unknown transformed_data_id: {transformed_data_id}",
                }
            )

        transformed_payload = self.transformed_data_store[transformed_data_id]
        chart_id = self._new_id('chart')
        chart_preview = self._build_ascii_chart(
            transformed_payload['region_totals'], chart_type
        )
        chart_file_path = self.output_dir / f'{chart_id}.txt'
        chart_file_path.write_text(chart_preview, encoding='utf-8')

        chart_payload = {
            'chart_type': chart_type,
            'series': transformed_payload['region_totals'],
            'source_transformed_data_id': transformed_data_id,
            'chart_preview': chart_preview,
            'chart_file_path': str(chart_file_path),
            'generated_at': datetime.utcnow().isoformat() + 'Z',
        }
        self.chart_store[chart_id] = chart_payload

        return json.dumps(
            {
                "status": "success",
                "chart_id": chart_id,
                "chart_type": chart_type,
                "chart_file_path": str(chart_file_path),
            }
        )

    async def report_composer(self, chart_id: str, summary_text: str, retry_count: int = 0) -> str:
        """Composes a formatted report incorporating data and charts.
        
        Args:
            chart_id: The ID of the generated chart
            summary_text: A summary text for the report
            retry_count: Keep track of retries.
        """
        await asyncio.sleep(0.5)
        if chart_id not in self.chart_store:
            return json.dumps({"status": "error", "message": f"Unknown chart_id: {chart_id}"})

        report_id = self._new_id('report')
        chart_payload = self.chart_store[chart_id]
        report_markdown = (
            f'# Sales Report\n\n'
            f'Generated at: {datetime.utcnow().isoformat()}Z\n\n'
            f'## Summary\n{summary_text}\n\n'
            f'## Chart Type\n{chart_payload["chart_type"]}\n\n'
            f'## Chart Preview\n\n```\n{chart_payload["chart_preview"]}\n```\n\n'
            f'## Raw Series\n\n```json\n{json.dumps(chart_payload["series"], indent=2)}\n```\n'
        )
        report_file_path = self.output_dir / f'{report_id}.md'
        report_file_path.write_text(report_markdown, encoding='utf-8')

        report_payload = {
            'chart_id': chart_id,
            'summary_text': summary_text,
            'chart': chart_payload,
            'report_markdown': report_markdown,
            'report_file_path': str(report_file_path),
            'generated_at': datetime.utcnow().isoformat() + 'Z',
        }
        self.report_store[report_id] = report_payload

        return json.dumps(
            {
                "status": "success",
                "report_id": report_id,
                "report_file_path": str(report_file_path),
            }
        )

    async def get_chart(self, chart_id: str, retry_count: int = 0) -> str:
        """Returns chart metadata and preview by chart_id.

        Args:
            chart_id: The chart ID returned by chart_generator
        """
        await asyncio.sleep(0.1)
        resolved_chart_id, error = self._resolve_chart_id(chart_id)
        if error:
            return json.dumps({"status": "error", "message": error})

        chart = self.chart_store[resolved_chart_id]

        return json.dumps(
            {
                "status": "success",
                "chart_id": resolved_chart_id,
                "chart": chart,
            }
        )

    async def get_report(self, report_id: str, retry_count: int = 0) -> str:
        """Returns report metadata and markdown content by report_id.

        Args:
            report_id: The report ID returned by report_composer
        """
        await asyncio.sleep(0.1)
        resolved_report_id, error = self._resolve_report_id(report_id)
        if error:
            return json.dumps({"status": "error", "message": error})

        report = self.report_store[resolved_report_id]

        return json.dumps(
            {
                "status": "success",
                "report_id": resolved_report_id,
                "report": report,
            }
        )

    async def email_dispatcher(self, report_id: str, recipient: str, retry_count: int = 0) -> str:
        """Dispatches the report to a specified recipient.
        
        Args:
            report_id: The ID of the report to send
            recipient: The email address of the recipient
            retry_count: Keep track of retries.
        """
        await asyncio.sleep(0.5)
        if report_id not in self.report_store:
            return json.dumps({"status": "error", "message": f"Unknown report_id: {report_id}"})

        return json.dumps({"status": "success", "message": f"Email dispatched to {recipient}"})

    def get_tools(self) -> dict[str, Any]:
        """Return dictionary of available tools for OpenAI function calling"""
        return {
            'data_fetcher': self,
            'data_transformer': self,
            'chart_generator': self,
            'report_composer': self,
            'email_dispatcher': self,
            'get_chart': self,
            'get_report': self,
        }