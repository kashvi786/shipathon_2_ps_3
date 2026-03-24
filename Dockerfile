FROM python:3.11-slim

WORKDIR /app

# Copy package into /app/src so it can be run as a module
COPY src/ /app/src/
COPY sales_data.csv /app/sales_data.csv

RUN pip install --no-cache-dir \
    "a2a-sdk[http-server]>=0.3.0" \
    "click>=8.1.8" \
    "httpx>=0.28.1" \
    "openai>=1.57.0" \
    "pydantic>=2.11.4" \
    "python-dotenv>=1.1.0" \
    "uvicorn>=0.34.2"
    # Add your custom dependencies here
    # requests>=2.31.0 \
    # beautifulsoup4>=4.12.0

ENV PYTHONUNBUFFERED=1
ENV SIMULATE_TRANSIENT_FAILURES=false
ENV DATA_SOURCE_CSV=/app/sales_data.csv

# Run the package as a module so relative imports work
CMD ["python", "-m", "src", "--host", "0.0.0.0", "--port", "5000"]