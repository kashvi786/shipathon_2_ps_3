# Hackathon Agent Development Guide

Complete guide for building and deploying agents using the Nasiko platform and the A2A Agent Template.

## Table of Contents

1. [Getting Started](#getting-started)
   - [Prerequisites](#prerequisites)
   - [Understanding the A2A Protocol](#understanding-the-a2a-protocol)
2. [Building Your Agent](#building-your-agent)
   - [Step 1: Copy the A2A Template](#step-1-copy-the-a2a-template)
   - [Step 2: Customize Your Agent](#step-2-customize-your-agent)
   - [Step 3: Implement Your Toolset](#step-3-implement-your-toolset)
   - [Step 4: Update Dependencies (If Needed)](#step-4-update-dependencies-if-needed)
3. [Testing Your Agent](#testing-your-agent)
   - [Local Testing](#local-testing)
   - [Testing Different Scenarios](#testing-different-scenarios)
4. [Deployment Methods](#deployment-methods)
   - [Connect GitHub](#connect-github)
   - [Upload ZIP File](#upload-zip-file)
5. [Agent Card Format](#agent-card-format)
6. [Common Issues & Troubleshooting](#common-issues--troubleshooting)
7. [Best Practices](#best-practices)
8. [Sample Agent Examples](#sample-agent-examples)
9. [Support and Resources](#support-and-resources)

---

## Getting Started

### Prerequisites

- Python 3.10+
- Docker Desktop installed
- OpenAI API Key (for OpenAI-based agents)
- Git (for GitHub deployment method)
- Code editor of your choice

### Understanding the A2A Protocol

The Agent-to-Agent (A2A) protocol is a JSON-RPC 2.0 based system that allows agents to communicate with each other and with the Nasiko platform. Your agent will:

1. Receive messages via HTTP POST requests
2. Process them using your custom logic 
3. Return structured responses in A2A format

---

## Building Your Agent

### Step 1: Copy the A2A Template

The new A2A agent template provides a complete, ready-to-use foundation:

```bash
# Copy the agent template
cp -r core/agents/a2a-agent-template my-awesome-agent
cd my-awesome-agent
```

### Step 2: Customize Your AgentX

Follow the [customization checklist](CUSTOMIZE.md) to replace all placeholders:

#### Basic Information
- Replace `{{AGENT_NAME}}` with your agent name (e.g., "my-awesome-agent")
- Replace `{{AGENT_DESCRIPTION}}` with your agent description
- Replace `{{AGENT_CONTAINER_NAME}}` with your container name

#### Skills & Capabilities  
- Replace `{{AGENT_SKILL_ID}}` with unique skill ID (e.g., "data_analysis")
- Replace `{{AGENT_SKILL_NAME}}` with human-readable name (e.g., "Data Analysis")
- Replace `{{AGENT_SKILL_DESCRIPTION}}` with what your agent does
- Replace `{{AGENT_TAGS}}` with relevant tags array
- Replace `{{AGENT_EXAMPLES}}` with usage examples array

#### Toolset Configuration
- Replace `{{TOOLSET_CLASS}}` with your toolset class name (e.g., "DataAnalysisToolset")
- Replace `{{TOOLSET_MODULE}}` with module name (e.g., "data_toolset")
- Rename `src/agent_toolset.py` to your module name

#### System Prompt
- Replace `{{SYSTEM_PROMPT}}` with your agent's system prompt

**Quick Replace Example:**
```bash
# Use find/replace in your editor or sed commands
find . -name "*.py" -o -name "*.toml" -o -name "*.yml" \
    -exec sed -i 's/{{AGENT_NAME}}/my-awesome-agent/g' {} \;
```

### Step 3: Implement Your Toolset

Replace the template content in your toolset file (e.g., `src/data_toolset.py`):

```python
import asyncio
from typing import Any
from pydantic import BaseModel


class DataAnalysisRequest(BaseModel):
    """Request model for data analysis"""
    data: str
    analysis_type: str = "summary"


class DataAnalysisToolset:
    """Data analysis and processing toolset"""

    def __init__(self):
        # Initialize any required APIs, databases, etc.
        self.session = None

    async def analyze_data(
        self, 
        data: str, 
        analysis_type: str = "summary"
    ) -> str:
        """Analyze provided data and return insights
        
        Args:
            data: The data to analyze (CSV, JSON, or plain text)
            analysis_type: Type of analysis to perform (summary, trends, statistics)
            
        Returns:
            str: Analysis results and insights
        """
        try:
            if not data.strip():
                return "Error: No data provided for analysis"
            
            # Implement your analysis logic here
            # This is a mock implementation
            if analysis_type == "summary":
                result = f"Data Summary:\n- Records processed: {len(data.split('\\n'))}\n- Data type: {type(data).__name__}"
            elif analysis_type == "trends":
                result = f"Trend Analysis:\n- Pattern detected in {data[:100]}..."
            else:
                result = f"Analysis completed for: {analysis_type}"
            
            return result
            
        except Exception as e:
            return f"Analysis failed: {str(e)}"

    async def process_dataset(
        self, 
        dataset_url: str, 
        operation: str = "validate"
    ) -> str:
        """Process dataset from URL
        
        Args:
            dataset_url: URL to the dataset
            operation: Operation to perform (validate, clean, transform)
            
        Returns:
            str: Processing results
        """
        try:
            # Implement dataset processing logic
            # This is a mock implementation
            await asyncio.sleep(0.1)  # Simulate processing time
            
            result = f"Dataset processed from {dataset_url}\\nOperation: {operation}\\nStatus: Complete"
            return result
            
        except Exception as e:
            return f"Dataset processing failed: {str(e)}"

    def get_tools(self) -> dict[str, Any]:
        """Return dictionary of available tools for OpenAI function calling"""
        return {
            'analyze_data': self,
            'process_dataset': self,
        }
```

**Tool Guidelines:**
- Use clear, descriptive function names and docstrings
- The OpenAI model uses docstrings to understand when to call your tools
- Handle errors gracefully with try/catch blocks  
- Return strings (the A2A protocol expects text responses)
- Keep tools focused on single responsibilities
- Use type hints and Pydantic models for validation

### Step 4: Update Dependencies (If Needed)

If your agent requires additional dependencies, update:

**`pyproject.toml`:**
```toml
dependencies = [
    "a2a-sdk>=0.3.0",
    "click>=8.1.8",
    "openai>=1.57.0", 
    "pydantic>=2.11.4",
    # Add your custom dependencies
    "pandas>=2.0.0",
    "numpy>=1.24.0", 
    "scikit-learn>=1.3.0",
]
```

**`Dockerfile`:**
```dockerfile
RUN pip install --no-cache-dir \
    "a2a-sdk[http-server]>=0.3.0" \
    openai>=1.57.0 \
    pydantic>=2.11.4 \
    # Add your custom dependencies
    pandas>=2.0.0 \
    numpy>=1.24.0 \
    scikit-learn>=1.3.0
```

---

## Testing Your Agent

### Docker Testing

Always test your agent using Docker to ensure consistency with the deployment environment:

1. **Build the Docker container:**
   ```bash
   docker build -t my-awesome-agent .
   ```

2. **Run the agent:**
   ```bash
   export OPENAI_API_KEY=your_openai_api_key_here
   docker run -p 5000:5000 -e OPENAI_API_KEY=$OPENAI_API_KEY my-awesome-agent
   ```

3. **Test with curl:**
   ```bash
   curl -X POST http://localhost:5000/ \
   -H "Content-Type: application/json" \
   -d '{
      "jsonrpc": "2.0",
      "id": "fdaa5774acb044f38637f1d174f91ae1",
      "method": "message/send",
      "params": {
        "session_id": "fdaa5774acb044f38637f1d174f91ae1",
        "message": {
          "role": "user",
          "parts": [
            {
              "kind": "text",
              "text": "Hello, what are your capabilities?"
            }
          ],
          "messageId": "dc86b828-2f6b-48d7-b8a9-ba5bf714eecf"
        }
      }
    }'
    ```

4. **Expected response:**
   ```json
   {
      "id": "fdaa5774acb044f38637f1d174f91ae1",
      "jsonrpc": "2.0",
      "result": {
        "artifacts": [
            {
                "artifactId": "e13346a0-bb62-493e-8f48-483d7c995a83",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Hello, I am a helpful assistant. How can I help you?"
                    }
                ]
            }
        ],
        "contextId": "cd21cfc6-bc00-4fee-9b4a-5a7b6d41eb59",
        "history": [
            {
                "contextId": "cd21cfc6-bc00-4fee-9b4a-5a7b6d41eb59",
                "kind": "message",
                "messageId": "dc86b828-2f6b-48d7-b8a9-ba5bf714eecf",
                "parts": [
                    {
                        "kind": "text",
                        "text": "can you tell me for Bengaluru India?"
                    }
                ],
                "role": "user",
                "taskId": "ebfca890-8b3e-433e-9b98-da9b0515158f"
            }
        ],
        "id": "ebfca890-8b3e-433e-9b98-da9b0515158f",
        "kind": "task",
        "status": {
            "state": "completed",
            "timestamp": "2026-03-18T12:18:48.238634+00:00"
        }
      }
    }
   ```

### Testing with Docker Compose

```bash
# Test with docker-compose (alternative method)
docker-compose up -d
# Wait a moment for startup, then test
curl -X POST http://localhost:5000/ -H "Content-Type: application/json" -d '{...}'
docker-compose down
```

---

## Deployment Methods

### Connect GitHub

This is the recommended method for hackathon submissions.

#### Step 1: Create GitHub Repository

1. Create a new repository on GitHub
2. Clone it locally:
   ```bash
   git clone https://github.com/your-username/my-awesome-agent.git
   cd my-awesome-agent
   ```

#### Step 2: Prepare Your Code

1. Copy your customized agent files:
   ```bash
   cp -r /path/to/your/customized/agent/* .
   ```

2. Create/update `.gitignore`:
   ```gitignore
   __pycache__/
   *.pyc
   *.pyo
   *.pyd
   .Python
   env/
   venv/
   .env
   .vscode/
   .DS_Store
   ```

#### Step 3: Commit and Push

```bash
git add .
git commit -m "Initial agent implementation using A2A template"
git push origin main
```

#### Step 4: Deploy via Nasiko Dashboard

1. **Access the Dashboard**
   - Log into the Nasiko dashboard
   - Navigate to the "Add Agent" section

2. **Connect GitHub Repository**
   - Click on "Connect GitHub" option
   - Complete OAuth authentication
   - Select your agent repository

3. **Deployment Complete**
   - Monitor deployment status in dashboard
   - Once deployed, agent will be available in registry

#### Step 5: Making Updates

```bash
# Make changes, test locally, then push
git add .
git commit -m "Updated feature X"
git push origin main

# Re-upload via dashboard "Agent Actions" → "Re-upload Agent"
```

### Upload ZIP File

For quick prototyping without GitHub:

#### Step 1: Prepare Your Agent

Ensure your agent structure is correct:
```
my-awesome-agent/
├── src/
│   ├── __init__.py
│   ├── __main__.py          (Required)
│   ├── openai_agent.py  
│   ├── openai_agent_executor.py
│   └── your_toolset.py
├── docker-compose.yml       (Required)
├── Dockerfile              (Required)
├── pyproject.toml
├── .gitignore
└── README.md
```

**Required files for deployment:**
- `Dockerfile`
- `docker-compose.yml`
- `src/__main__.py` OR `main.py`

**Optional files:**
- `AgentCard.json` (auto-generated if missing)

#### Step 2: Create ZIP Package

```bash
# Create ZIP file excluding unnecessary files
zip -r my-awesome-agent.zip my-awesome-agent/ \
    -x "*.pyc" "*/__pycache__/*" "*/.git/*" "*/.env"
```

#### Step 3: Deploy via Dashboard

1. Navigate to "Add Agent" → "Upload ZIP"
2. Select your ZIP file
3. Monitor deployment status
4. Agent will be available in registry once deployed

---

## Agent Card Format

The A2A template automatically generates proper agent cards (`AgentCard.json`) if missing. If you want to customize the metadata, you can create an `AgentCard.json` file:

```json
{
  "protocolVersion": "0.2.9",
  "name": "My Awesome Agent",
  "description": "Detailed description of agent capabilities",
  "url": "http://localhost:5000/",
  "preferredTransport": "JSONRPC",
  "provider": {
    "organization": "Your Team Name",
    "url": "https://github.com/your-username/your-agent-repo"
  },
  "version": "1.0.0",
  "capabilities": {
    "streaming": true,
    "pushNotifications": false,
    "stateTransitionHistory": true,
    "chat_agent": true
  },
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text"],
  "skills": [
    {
      "id": "data_analysis",
      "name": "Data Analysis",
      "description": "Analyze datasets and provide insights",
      "tags": ["data", "analysis", "insights"],
      "examples": [
        "Analyze this CSV data for trends",
        "Process this dataset and summarize findings"
      ]
    }
  ]
}
```

---

## Common Issues & Troubleshooting

### Build Issues

**Problem**: Docker build fails with dependency errors
```
ERROR: Could not find a version that satisfies the requirement a2a-sdk>=0.3.0
```
**Solution**: Ensure dependencies are correctly specified in both `pyproject.toml` and `Dockerfile`

**Problem**: Import errors during runtime
```
ModuleNotFoundError: No module named 'your_toolset'
```
**Solution**: 
- Check that you renamed the toolset file correctly
- Verify imports in `openai_agent.py` match your module name
- Ensure the `get_tools()` method returns correct tool mapping

### Runtime Issues

**Problem**: Agent doesn't call tools
```
Agent responds with text but never uses defined tools
```
**Solution**:
- Improve tool descriptions in docstrings - be very specific about when to use each tool
- Test that tools are correctly registered in `get_tools()`
- Verify the OpenAI model can understand your tool descriptions

**Problem**: Environment variable errors
```
ValueError: OPENAI_API_KEY environment variable not set
```
**Solution**: 
- Set `OPENAI_API_KEY` in your environment
- For Docker: `docker run -e OPENAI_API_KEY=$OPENAI_API_KEY ...`
- For deployment: ensure environment variables are configured in dashboard

### Deployment Issues

**Problem**: Validation fails
```
Validation failed: docker-compose.yml not found
```
**Solution**: Ensure all required files are present:
- `Dockerfile` in root directory
- `docker-compose.yml` in root directory  
- `src/` directory with Python files

**Problem**: Agent crashes after deployment
```
Agent status: Crashed, Exit code: 1
```
**Solution**:
- Check deployment logs for specific error
- Test Docker container locally first
- Verify all environment variables are set
- Ensure port 5000 is correctly configured

---

## Best Practices

### Agent Design

1. **Clear Purpose**: Design agents with specific, well-defined purposes
2. **Tool Composition**: Create multiple focused tools rather than one complex tool
3. **Descriptive Documentation**: Write detailed docstrings that help the LLM understand when to use tools
4. **Error Handling**: Always handle errors gracefully and return helpful error messages

### Code Organization

1. **Modular Tools**: Keep each tool focused on a single responsibility
2. **Type Safety**: Use Pydantic models for complex input validation
3. **Async Support**: Use async functions for tools that perform I/O operations
4. **Clean Code**: Follow Python conventions and keep code readable

### Testing Strategy

1. **Local Testing**: Always test locally before deploying
2. **Tool Testing**: Test each tool independently with various inputs
3. **Integration Testing**: Test full conversation flows
4. **Edge Cases**: Test with malformed inputs and error scenarios

### Security

1. **Input Validation**: Validate all user inputs in tools
2. **API Keys**: Never hardcode API keys - use environment variables
3. **Error Messages**: Don't expose sensitive information in error messages
4. **Dependencies**: Keep dependencies updated and secure

---

## Sample Agent Examples

### Weather Agent Example

The template comes with a complete weather agent example that demonstrates:

- **Multiple Tools**: Current weather and forecast functions
- **Mock Data**: Sample data for testing without API keys
- **Error Handling**: Proper validation and error responses  
- **Documentation**: Complete setup and usage instructions

### Template Features Demonstrated

- **OpenAI Integration**: Seamless function calling
- **A2A Protocol**: Proper message handling and responses
- **Docker Support**: Ready-to-deploy containerization
- **Type Safety**: Pydantic models and type hints
- **Async Support**: Non-blocking tool execution

Use the weather agent as a reference for your own development!

---

## Support and Resources

### Getting Help
- Check the troubleshooting section above
- Review error logs in the deployment dashboard
- Test locally first to isolate issues
- Refer to the working weather agent example

### Tips for Success
1. Start with the template - don't build from scratch
2. Follow the customization checklist step by step
3. Test each tool individually before integration
4. Keep your system prompt clear and specific
5. Use the weather agent as a working reference

Good luck with your hackathon project! 🚀

The A2A template makes agent development much faster and more reliable. Focus on your unique toolset implementation while the template handles all the A2A protocol complexity.