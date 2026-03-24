import logging
import os

import click
import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from dotenv import load_dotenv
from .openai_agent import create_agent  # type: ignore[import-not-found]
from .openai_agent_executor import (
    OpenAIAgentExecutor,  # type: ignore[import-untyped]
)
from starlette.applications import Starlette


load_dotenv()

logging.basicConfig()


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=5000)
def main(host: str, port: int):
    # Verify an API key is set.
    if not os.getenv('GEMINI_API_KEY'):
        raise ValueError('GEMINI_API_KEY environment variable not set')

    skill = AgentSkill(
        id='data_pipeline_orchestration',
        name='Data Pipeline Orchestration',
        description='Orchestrates data fetching, transformation, charting, and email delivery.',
        tags=['orchestration', 'data pipeline', 'report'],
        examples=["Fetch last week's sales data, summarise it by region, generate a bar chart, and email the report to the sales team."],
    )

    # AgentCard for OpenAI-based agent
    agent_card = AgentCard(
        name='a2a-orchestration-agent',
        description='Adaptive Workflow Orchestration Agent for Data Pipeline',
        url=f'http://{host}:{port}/',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )

    # Create OpenAI agent
    agent_data = create_agent()

    agent_executor = OpenAIAgentExecutor(
        card=agent_card,
        tools=agent_data['tools'],
        api_key=os.getenv('GEMINI_API_KEY'),
        system_prompt=agent_data['system_prompt'],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor, task_store=InMemoryTaskStore()
    )

    a2a_app = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    routes = a2a_app.routes()

    app = Starlette(routes=routes)

    uvicorn.run(app, host=host, port=port)


if __name__ == '__main__':
    main()