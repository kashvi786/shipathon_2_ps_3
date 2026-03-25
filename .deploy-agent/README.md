# A2A Agent Template

This is a reusable template for creating A2A (Agent2Agent) agents. It provides a complete structure that can be customized for any type of agent by replacing placeholders with your specific implementation.

## Quick Start

1. **Copy the template:**
   ```bash
   cp -r a2a-agent-template your-agent-name
   cd your-agent-name
   ```

2. **Replace all placeholders** (see Customization Guide below)

3. **Implement your toolset** in `src/agent_toolset.py`

4. **Install and run:**
   ```bash
   pip install -e .
   python -m src --host localhost --port 5000
   ```

## Template Structure

```
a2a-agent-template/
├── src/
│   ├── __init__.py              # Package initialization
│   ├── __main__.py              # Main entry point with placeholders
│   ├── openai_agent.py          # Agent configuration
│   ├── openai_agent_executor.py # OpenAI executor (ready to use)
│   └── agent_toolset.py         # Your custom toolset implementation
├── .gitignore                   # Python gitignore
├── pyproject.toml               # Project configuration with placeholders
├── Dockerfile                   # Docker configuration
├── docker-compose.yml           # Docker Compose with placeholders
└── README.md                    # This file
```

## Customization Guide

### Required Placeholders to Replace

Replace these placeholders throughout the template files:

#### Basic Agent Information
- `{{AGENT_NAME}}` - Your agent's name (e.g., "a2a-weather-agent")
- `{{AGENT_DESCRIPTION}}` - Brief description of your agent
- `{{AGENT_CONTAINER_NAME}}` - Docker container name
- `{{AGENT_PORT}}` - Default port (e.g., 5000)
- `{{AGENT_DEFAULT_PORT}}` - Default port as integer (e.g., 5000)

#### Agent Skills & Capabilities
- `{{AGENT_SKILL_ID}}` - Unique skill identifier (e.g., 'weather_agent')
- `{{AGENT_SKILL_NAME}}` - Human-readable skill name (e.g., 'Weather Agent')
- `{{AGENT_SKILL_DESCRIPTION}}` - What your agent does
- `{{AGENT_TAGS}}` - List of tags (e.g., ['weather', 'forecast', 'temperature'])
- `{{AGENT_EXAMPLES}}` - List of usage examples

#### Toolset Configuration
- `{{TOOLSET_MODULE}}` - Your toolset module name (e.g., "weather_toolset")
- `{{TOOLSET_CLASS}}` - Your toolset class name (e.g., "WeatherToolset")
- `{{TOOLSET_DESCRIPTION}}` - Brief description of your toolset

#### System Prompt
- `{{SYSTEM_PROMPT}}` - The full system prompt for your agent

### Step-by-Step Customization

1. **Find and Replace Placeholders:**
   ```bash
   # Use your editor's find/replace or sed commands
   find . -name "*.py" -o -name "*.toml" -o -name "*.yml" -o -name "*.md" | xargs sed -i 's/{{AGENT_NAME}}/my-cool-agent/g'
   ```

2. **Update pyproject.toml:**
   - Add your specific dependencies
   - Update name, description, and version

3. **Implement agent_toolset.py:**
   - Replace the sample functions with your actual tools
   - Add required imports and dependencies
   - Implement your business logic

4. **Update the system prompt:**
   - Define what your agent does
   - Specify how it should behave
   - List available functions and their purposes

### Example Customization

Here's how to create a weather agent:

```python
# In src/agent_toolset.py
class WeatherToolset:
    """Weather information and forecasting toolset"""

    def __init__(self):
        self.api_key = os.getenv('WEATHER_API_KEY')

    async def get_weather(self, location: str, units: str = "metric") -> str:
        """Get current weather for a location"""
        # Your weather API implementation
        pass

    async def get_forecast(self, location: str, days: int = 5) -> str:
        """Get weather forecast for a location"""
        # Your forecast implementation
        pass

    def get_tools(self) -> dict[str, Any]:
        return {
            'get_weather': self,
            'get_forecast': self,
        }
```

## Environment Variables

The template requires these environment variables:

- `OPENAI_API_KEY` - Required for OpenAI integration
- Add your custom environment variables as needed

## Docker Support

The template includes Docker support:

```bash
# Build and run with Docker
docker-compose up

# Or build manually
docker build -t your-agent-name .
docker run -p 5000:5000 -e OPENAI_API_KEY=your-key your-agent-name
```

## Dependencies

Core dependencies (already included):
- `a2a-sdk>=0.3.0` - A2A framework
- `openai>=1.57.0` - OpenAI integration
- `pydantic>=2.11.4` - Data validation
- `click>=8.1.8` - CLI interface
- `uvicorn>=0.34.2` - ASGI server

Add your specific dependencies to `pyproject.toml` and `Dockerfile`.

## Testing Your Agent

1. **Start the agent:**
   ```bash
   python -m src --host localhost --port 5000
   ```

2. **Test with curl:**
   ```bash
   curl -X POST http://localhost:5000/agent/message \\
        -H "Content-Type: application/json" \\
        -d '{"message": "Test message"}'
   ```

3. **Integration with A2A network:**
   - Register your agent with the A2A network
   - Test agent-to-agent communication

## Advanced Customization

### Custom Response Models

Define Pydantic models for structured responses:

```python
class WeatherResponse(BaseModel):
    location: str
    temperature: float
    humidity: int
    description: str
```

### Multiple Tools

Add multiple functions to your toolset:

```python
def get_tools(self) -> dict[str, Any]:
    return {
        'function1': self,
        'function2': self,
        'function3': self,
    }
```

### Custom Error Handling

Implement proper error handling in your toolset methods:

```python
async def your_function(self, param: str) -> str:
    try:
        # Your logic here
        return result
    except SpecificError as e:
        return f"Specific error: {str(e)}"
    except Exception as e:
        return f"General error: {str(e)}"
```

## Troubleshooting

- **Import errors:** Check that all placeholders are replaced correctly
- **Missing dependencies:** Update pyproject.toml and Dockerfile
- **Port conflicts:** Change the port in docker-compose.yml and __main__.py
- **OpenAI errors:** Verify OPENAI_API_KEY is set correctly

## Contributing

This template is based on the a2a-translator agent structure. Improvements and suggestions are welcome!