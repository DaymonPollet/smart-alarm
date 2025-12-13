FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Train the model during build or ensure it's present. 
# Ideally, training should be a separate step, but for simplicity in this setup:
# We will assume the model is trained and copied, OR we run training here.
# Let's run training here to ensure the model exists in the image.
# Note: This requires the data to be available during build, which might not be ideal.
# For now, let's assume the user will run the training script locally or in CI before building, 
# OR we copy the data into the image (bad practice for large data).
# 
# Better approach for this specific request:
# The user said "The GitHub Actions Runner on the Pi must execute the CI/CD pipeline: Build Image -> Push to Registry".
# So the model should probably be trained in the CI pipeline or committed.
# Since I am "coding myself through the plan", I will add a step to run training if model is missing, 
# but I need the data.
# 
# Let's just expose the port and run app.py.
# The user can mount the model or build it in.

EXPOSE 5000

CMD ["python", "app.py"]
