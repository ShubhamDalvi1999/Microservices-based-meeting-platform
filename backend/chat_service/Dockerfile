# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable for Flask app (though we run with socketio.run directly)
ENV FLASK_APP app.py 

# Run app.py when the container launches using python directly to ensure eventlet is used by SocketIO
CMD ["python", "app.py"] 