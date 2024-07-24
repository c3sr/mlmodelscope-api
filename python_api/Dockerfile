# Use the official Python image from the Docker Hub
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY python_api/requirements.txt .

# Install the dependencies specified in the requirements.txt file
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY python_api/ .

# Expose the port that the FastAPI app runs on
EXPOSE 8000

# Command to run the FastAPI application with --reload for development
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
