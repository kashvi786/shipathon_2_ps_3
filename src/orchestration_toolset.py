import json
import logging
import os
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

class OrchestrationToolset:
    """Data Pipeline tools including fetch, transform, chart, and email"""

    def __init__(self):
        self.simulate_transient_failures = (
            os.getenv('SIMULATE_TRANSIENT_FAILURES', 'false').lower() == 'true'
        )

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
        
        return json.dumps({"status": "success", "data_id": f"raw_data_{source}_123"})

    async def data_transformer(self, data_id: str, region: str = "all", retry_count: int = 0) -> str:
        """Cleans and transforms fetched data by region.
        
        Args:
            data_id: ID of the raw data to transform
            region: The region to summarise by
            retry_count: Keep track of retries.
        """
        await asyncio.sleep(0.5)
        return json.dumps({"status": "success", "transformed_data_id": f"tx_{data_id}_{region}"})

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
            
        return json.dumps({"status": "success", "chart_id": f"chart_{chart_type}_from_{transformed_data_id}"})

    async def report_composer(self, chart_id: str, summary_text: str, retry_count: int = 0) -> str:
        """Composes a formatted report incorporating data and charts.
        
        Args:
            chart_id: The ID of the generated chart
            summary_text: A summary text for the report
            retry_count: Keep track of retries.
        """
        await asyncio.sleep(0.5)
        return json.dumps({"status": "success", "report_id": f"report_with_{chart_id}"})

    async def email_dispatcher(self, report_id: str, recipient: str, retry_count: int = 0) -> str:
        """Dispatches the report to a specified recipient.
        
        Args:
            report_id: The ID of the report to send
            recipient: The email address of the recipient
            retry_count: Keep track of retries.
        """
        await asyncio.sleep(0.5)
        return json.dumps({"status": "success", "message": f"Email dispatched to {recipient}"})

    def get_tools(self) -> dict[str, Any]:
        """Return dictionary of available tools for OpenAI function calling"""
        return {
            'data_fetcher': self,
            'data_transformer': self,
            'chart_generator': self,
            'report_composer': self,
            'email_dispatcher': self,
        }