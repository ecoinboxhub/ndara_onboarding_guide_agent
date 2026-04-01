# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set working directory for the microservice
WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# Copy only the requirements specifically for this standalone agent
COPY requirements.txt .

# Install dependencies without polluting caching layers unnecessarily
RUN pip install --no-cache-dir -r requirements.txt

# Copy the specific onboarding_guide_agent source code files into the container
COPY . .

# Ndara.ai agreed on port 8008 for this specific service
EXPOSE 8008

# Start the application server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8008"]
