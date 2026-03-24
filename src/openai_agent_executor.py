import json
import logging
import inspect
import os
import re

from typing import Any

from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    AgentCard,
    TaskState,
    TextPart,
    UnsupportedOperationError,
)
from a2a.utils.errors import ServerError
from openai import AsyncOpenAI


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class OpenAIAgentExecutor(AgentExecutor):
    """An AgentExecutor that runs an OpenAI-based Agent."""

    def __init__(
        self,
        card: AgentCard,
        tools: dict[str, Any],
        api_key: str,
        system_prompt: str,
    ):
        self._card = card
        self.tools = tools
        self.client = None
        if api_key:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url='https://generativelanguage.googleapis.com/v1beta/openai/',
            )
        self.model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
        self.max_tokens = int(os.getenv('GEMINI_MAX_TOKENS', '256'))
        self.max_iterations = int(os.getenv('AGENT_MAX_ITERATIONS', '8'))
        fallback_models = os.getenv(
            'GEMINI_MODEL_FALLBACKS',
            'gemini-2.5-flash',
        )
        self.fallback_models = [
            model.strip() for model in fallback_models.split(',') if model.strip()
        ]
        self.system_prompt = system_prompt

    def _parse_tool_result(self, raw_result: Any) -> dict[str, Any]:
        if isinstance(raw_result, dict):
            return raw_result
        if isinstance(raw_result, str):
            try:
                parsed = json.loads(raw_result)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                return {'status': 'error', 'message': f'Non-JSON tool output: {raw_result}'}
        if hasattr(raw_result, 'model_dump'):
            return raw_result.model_dump()
        return {'status': 'error', 'message': f'Unsupported tool output type: {type(raw_result).__name__}'}

    def _build_execution_log(self, message_text: str) -> dict[str, Any]:
        return {
            'workflow_domain': 'adaptive_data_pipeline_orchestration',
            'input_instruction': message_text,
            'plan': [],
            'steps': [],
            'overall_status': 'in_progress',
        }

    def _extract_json_block(self, content: str) -> str:
        if not content:
            return '{}'
        fenced_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
        if fenced_match:
            return fenced_match.group(1)

        object_match = re.search(r'(\{.*\})', content, re.DOTALL)
        if object_match:
            return object_match.group(1)
        return '{}'

    async def _generate_plan(self, message_text: str) -> list[dict[str, Any]]:
        planner_prompt = (
            'You are a workflow planner for a data pipeline agent. '
            'Create an ordered execution plan using ONLY the available tools. '
            'You may choose a subset of tools based on the user request. '
            f'Available tools: {", ".join(self.tools.keys())}. '
            'Return JSON only in this format: '
            '{"plan": [{"step": 1, "tool": "data_fetcher", "reason": "..."}]}'
        )

        planning_messages = [
            {'role': 'system', 'content': planner_prompt},
            {'role': 'user', 'content': message_text},
        ]

        try:
            planning_response = await self._chat_completion_with_fallback(
                messages=planning_messages,
                openai_tools=[],
            )
            content = planning_response.choices[0].message.content or '{}'
            parsed = json.loads(self._extract_json_block(content))
            plan = parsed.get('plan', []) if isinstance(parsed, dict) else []
            if not isinstance(plan, list):
                return []

            normalized_plan: list[dict[str, Any]] = []
            for index, step in enumerate(plan, start=1):
                if not isinstance(step, dict):
                    continue
                tool_name = step.get('tool')
                if tool_name not in self.tools:
                    continue
                normalized_plan.append(
                    {
                        'step': step.get('step', index),
                        'tool': tool_name,
                        'reason': step.get('reason', ''),
                    }
                )
            return normalized_plan
        except Exception as error:
            logger.warning(f'Planning phase failed, continuing without explicit plan: {error}')
            return []

    def _validate_step_result(self, step_name: str, payload: dict[str, Any]) -> tuple[bool, str]:
        if payload.get('status') != 'success':
            return False, payload.get('message', 'Tool returned non-success status')

        required_fields = {
            'data_fetcher': ['data_id'],
            'data_transformer': ['transformed_data_id'],
            'chart_generator': ['chart_id'],
            'report_composer': ['report_id'],
            'email_dispatcher': ['message'],
        }
        missing = [field for field in required_fields.get(step_name, []) if field not in payload]
        if missing:
            return False, f'Missing expected field(s): {", ".join(missing)}'
        return True, ''

    async def _call_tool_step(
        self,
        step_name: str,
        args: dict[str, Any],
        max_retries: int = 2,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if step_name not in self.tools:
            failure = {
                'status': 'failed',
                'step': step_name,
                'attempts': [],
                'final_error': f'Tool not registered: {step_name}',
            }
            return {}, failure

        tool_instance = self.tools[step_name]
        if not hasattr(tool_instance, step_name):
            failure = {
                'status': 'failed',
                'step': step_name,
                'attempts': [],
                'final_error': f'Method not found on tool instance: {step_name}',
            }
            return {}, failure

        method = getattr(tool_instance, step_name)
        attempts = []

        for retry_count in range(max_retries + 1):
            call_args = {**args, 'retry_count': retry_count}

            if step_name == 'data_fetcher' and retry_count > 0:
                call_args['source'] = call_args.get('source', 'sales_api')
            if step_name == 'data_transformer' and retry_count > 0:
                call_args['region'] = call_args.get('region', 'all') or 'all'
            if step_name == 'chart_generator' and retry_count > 0:
                call_args['chart_type'] = call_args.get('chart_type', 'bar') or 'bar'

            try:
                result = method(**call_args)
                if inspect.iscoroutine(result):
                    result = await result

                payload = self._parse_tool_result(result)
                is_valid, error_message = self._validate_step_result(step_name, payload)

                attempts.append(
                    {
                        'retry_count': retry_count,
                        'input': call_args,
                        'result': payload,
                        'status': 'success' if is_valid else 'failed',
                        'error': '' if is_valid else error_message,
                    }
                )

                if is_valid:
                    return payload, {
                        'status': 'success',
                        'step': step_name,
                        'attempts': attempts,
                    }
            except Exception as error:
                attempts.append(
                    {
                        'retry_count': retry_count,
                        'input': call_args,
                        'result': {},
                        'status': 'failed',
                        'error': str(error),
                    }
                )

        final_error = attempts[-1]['error'] if attempts else 'Unknown failure'
        return {}, {
            'status': 'failed',
            'step': step_name,
            'attempts': attempts,
            'final_error': final_error,
        }

    async def _execute_llm_tool_call(
        self,
        function_name: str,
        function_args: dict[str, Any],
        execution_log: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        if function_name not in self.tools:
            failure = {
                'status': 'failed',
                'step': function_name,
                'attempts': [
                    {
                        'retry_count': 0,
                        'input': function_args,
                        'result': {},
                        'status': 'failed',
                        'error': f'Function {function_name} not found',
                    }
                ],
                'final_error': f'Function {function_name} not found',
            }
            execution_log['steps'].append(failure)
            execution_log['overall_status'] = 'escalated'
            execution_log['escalation_reason'] = failure['final_error']
            return {'status': 'error', 'message': failure['final_error']}, True

        payload, step_log = await self._call_tool_step(function_name, function_args)
        execution_log['steps'].append(step_log)
        if step_log['status'] != 'success':
            execution_log['overall_status'] = 'escalated'
            execution_log['escalation_reason'] = step_log.get(
                'final_error', f'{function_name} failed after retries'
            )
            return {
                'status': 'error',
                'message': execution_log['escalation_reason'],
            }, True
        return payload, False

    async def _process_request(
        self,
        message_text: str,
        context: RequestContext,
        task_updater: TaskUpdater,
    ) -> None:
        execution_log = self._build_execution_log(message_text)

        if not self.client:
            await task_updater.add_artifact(
                [
                    TextPart(
                        text='GEMINI_API_KEY is required.'
                    )
                ]
            )
            await task_updater.complete()
            return

        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': message_text},
        ]

        plan = await self._generate_plan(message_text)
        execution_log['plan'] = plan
        if plan:
            messages.append(
                {
                    'role': 'system',
                    'content': (
                        'Execution plan generated before running tools. '
                        f'Follow this ordered plan while executing: {json.dumps(plan)}'
                    ),
                }
            )

        # Convert tools to OpenAI format
        openai_tools = []
        for tool_name, tool_instance in self.tools.items():
            if hasattr(tool_instance, tool_name):
                func = getattr(tool_instance, tool_name)
                # Extract function schema from the method
                schema = self._extract_function_schema(func)
                openai_tools.append({'type': 'function', 'function': schema})

        max_iterations = self.max_iterations
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            try:
                response = await self._chat_completion_with_fallback(
                    messages=messages,
                    openai_tools=openai_tools,
                )

                message = response.choices[0].message

                # Add assistant's response to messages
                messages.append(
                    {
                        'role': 'assistant',
                        'content': message.content,
                        'tool_calls': message.tool_calls,
                    }
                )

                # Check if there are tool calls to execute
                if message.tool_calls:
                    # Execute tool calls
                    for tool_call in message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)

                        logger.debug(
                            f'Calling function: {function_name} with args: {function_args}'
                        )

                        result, escalated = await self._execute_llm_tool_call(
                            function_name=function_name,
                            function_args=function_args,
                            execution_log=execution_log,
                        )
                        result_json = json.dumps(result)

                        # Add tool result to messages
                        messages.append(
                            {
                                'role': 'tool',
                                'tool_call_id': tool_call.id,
                                'content': result_json,
                            }
                        )

                        if escalated:
                            final_log = json.dumps(execution_log, indent=2)
                            await task_updater.add_artifact([TextPart(text=final_log)])
                            await task_updater.complete()
                            return

                    # Send update to show we're processing
                    await task_updater.update_status(
                        TaskState.working,
                        message=task_updater.new_agent_message(
                            [TextPart(text='Processing tool calls...')]
                        ),
                    )

                    # Continue the loop to get the final response
                    continue
                # No more tool calls, this is the final response
                if message.content:
                    if execution_log['steps'] and execution_log['overall_status'] == 'in_progress':
                        execution_log['overall_status'] = 'success'

                    final_response = message.content
                    if execution_log['steps']:
                        final_response = (
                            f'{message.content}\n\nExecution Log:\n'
                            f'{json.dumps(execution_log, indent=2)}'
                        )

                    parts = [TextPart(text=final_response)]
                    logger.debug(f'Yielding final response: {parts}')
                    await task_updater.add_artifact(parts)
                    await task_updater.complete()
                break

            except Exception as e:
                logger.error(f'Error in OpenAI API call: {e}')
                if execution_log['overall_status'] == 'in_progress':
                    execution_log['overall_status'] = 'failed'
                    execution_log['failure_reason'] = str(e)
                error_parts = [
                    TextPart(
                        text=(
                            'Sorry, an error occurred while processing the request: '
                            f'{e!s}\n\nExecution Log:\n{json.dumps(execution_log, indent=2)}'
                        )
                    )
                ]
                await task_updater.add_artifact(error_parts)
                await task_updater.complete()
                break

        if iteration >= max_iterations:
            error_parts = [
                TextPart(
                    text='Sorry, the request has exceeded the maximum number of iterations.'
                )
            ]
            await task_updater.add_artifact(error_parts)
            await task_updater.complete()

    async def _chat_completion_with_fallback(self, messages, openai_tools):
        models_to_try = [self.model] + [
            model for model in self.fallback_models if model != self.model
        ]
        last_error = None

        for model_name in models_to_try:
            try:
                logger.debug(f'Trying model: {model_name}')
                return await self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    tools=openai_tools if openai_tools else None,
                    tool_choice='auto' if openai_tools else None,
                    temperature=0.0,
                    max_tokens=self.max_tokens,
                )
            except Exception as error:
                last_error = error
                error_text = str(error)
                retryable_quota_error = (
                    '429' in error_text
                    or 'RESOURCE_EXHAUSTED' in error_text
                    or 'quota' in error_text.lower()
                )
                if retryable_quota_error:
                    logger.warning(
                        f'Model {model_name} unavailable due to quota/rate limit. Trying next fallback.'
                    )
                    continue
                raise

        if last_error:
            raise last_error
        raise RuntimeError('No Gemini model available for completion.')

    def _extract_function_schema(self, func):
        """Extract OpenAI function schema from a Python function"""
        import inspect

        # Get function signature
        sig = inspect.signature(func)

        # Get docstring
        docstring = inspect.getdoc(func) or ''

        # Extract description and parameter info from docstring
        lines = docstring.split('\n')
        description = lines[0] if lines else func.__name__

        # Build parameters schema
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            param_type = 'string'  # Default type
            param_description = f'Parameter {param_name}'

            # Try to infer type from annotation
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = 'integer'
                elif param.annotation == float:
                    param_type = 'number'
                elif param.annotation == bool:
                    param_type = 'boolean'
                elif param.annotation == list:
                    param_type = 'array'
                elif param.annotation == dict:
                    param_type = 'object'

            # Check if parameter has default value
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

            properties[param_name] = {
                'type': param_type,
                'description': param_description,
            }

        return {
            'name': func.__name__,
            'description': description,
            'parameters': {
                'type': 'object',
                'properties': properties,
                'required': required,
            },
        }

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ):
        # Run the agent until complete
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        # Immediately notify that the task is submitted.
        if not context.current_task:
            await updater.submit()
        await updater.start_work()

        # Extract text from message parts
        message_text = ''
        for part in context.message.parts:
            if isinstance(part.root, TextPart):
                message_text += part.root.text

        await self._process_request(message_text, context, updater)
        logger.debug('[a2a-orchestration-agent] execute exiting')

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        # Ideally: kill any ongoing tasks.
        raise ServerError(error=UnsupportedOperationError())