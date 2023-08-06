# AutoThreader
###### WIP on hiatus

## Brief Description
AutoThreader is a project that listens for GitHub webhook events, summarizes the event details using Hugging Face's LongT5 transformer model, and posts the summary to Threads using the threads-py package. The project is containerized using Docker for easy setup and deployment.

## Summary
This project is a great example of how to integrate various technologies like GitHub webhooks, Hugging Face transformers, and Threads. It's also a demonstration of how to use Docker to simplify the setup and deployment process. The most important part of setting up this project is the configuration of environment variables, which are used to authenticate with Threads and verify the GitHub webhook signature.

## Setup

### Environment Variables
You need to set up the following environment variables in a `.env` file in the project root:

- `THREADS_USERNAME`: Your Threads username.
- `THREADS_PASSWORD`: Your Threads password.
- `THREADS_TOKEN`: Your Threads token (optional if you're already authenticated).
- `WEBHOOK_SECRET`: The secret you set in GitHub when setting up the webhook.

### Docker
1. Install Docker and Docker Compose on your machine.
2. Navigate to the project root directory in your terminal.
3. Run `docker-compose up -d` to build the Docker image and start the container.

## Usage
Once the Docker container is running, your application is live and listening for GitHub webhook events. You can access your application via the ngrok URL that is printed in the terminal when you start the container.

When a webhook event is received, the application summarizes the event details and posts the summary to Threads. You can view the posts on Threads using your Threads account.

## Conclusion
AutoThreader is a powerful tool for automating the process of summarizing GitHub events and posting them to Threads. With Docker, the setup process is simplified, making it easy for anyone to use this project.
