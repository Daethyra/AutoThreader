import os
import logging
import asyncio
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
from threadspy import ThreadsAPI
from langchain.requests import RequestHandler
from langchain.chains import TaskChain
from langchain.env import EnvManager
from langchain.docstore import DocStore
from langchain.memory import MemoryManager
from transformers import AutoTokenizer, LongT5Model
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict
import uvicorn

load_dotenv()

class GithubThreader(ThreadsAPI, RequestHandler, TaskChain, EnvManager, DocStore, MemoryManager):
    def __init__(self):
        self.app = FastAPI()
        self.api = ThreadsAPI(
            username=os.getenv("THREADS_USERNAME"),
            password=os.getenv("THREADS_PASSWORD"),
        )
        self.tokenizer = AutoTokenizer.from_pretrained("google/long-t5-local-base")
        self.model = LongT5Model.from_pretrained("google/long-t5-local-base")
        self.last_post_time = datetime.now() - timedelta(hours=1)  # Adjust `timedelta` to configure the Threading frequency | Default->initializes to an hour ago
        self.backlog = []  # backlog of events during cooldown

    # Handle Github webhook | Discord webhook integration planned
    @self.app.post("/webhook")
    async def handle_webhook(request: Request):
        signature = request.headers.get('X-Hub-Signature')
        data = await request.json()

        if not self.verify_signature(data, signature, os.getenv("WEBHOOK_SECRET")):
            logging.warning('Webhook signature verification failed. Received signature: %s', signature)
            raise HTTPException(status_code=403, detail="Forbidden")

        event_type = request.headers.get('X-GitHub-Event')
        await self.process_webhook_data(data, event_type)
        return

    async def process_webhook_data(self, data, event_type):
        try:
            if event_type == 'push':
                event_info = {
                    'repository': data['repository']['full_name'],
                    'pusher': data['pusher']['name'],
                    'commits': data['commits'],
                }
                await self.activate_event(event_info)
                logging.info(f'Successfully ingested Github webhook for {event_info["repository"]}')
            else:
                logging.info(f'Received unhandled Github event type: {event_type}')
        except Exception as e:
            logging.error(f'Error processing Github webhook data: {e}', exc_info=True)

    async def activate_event(self, event_info):
        try:
            message = f"New commits pushed to {event_info['repository']} by {event_info['pusher']}."
            summary = await self.summarize(message)
            commit_urls = [commit['url'] for commit in event_info['commits']]  # get the urls of all commits
            for url in commit_urls:
                self.backlog.append({"summary": summary, "url": url})
            await self.post_thread_from_backlog()
        except Exception as e:
            logging.error(f'Error activating event: {e}', exc_info=True)

    async def summarize(self, text):
        try:
            inputs = self.tokenizer(text, return_tensors="pt")
            outputs = self.model.generate(**inputs)
            summary = self.tokenizer.decode(outputs[0])
            logging.info(f'Successfully converted text to summary for thread post')
            return summary
        except Exception as e:
            logging.error(f'Error generating summary from text: {e}', exc_info=True)
            return text  # return original text if summarization fails

    # Define async thread poster
    async def post_thread_from_backlog(self):
        try:
            if datetime.now() - self.last_post_time > timedelta(hours=1) and self.backlog:
                # if cooldown has passed and there is something in the backlog
                if len(self.backlog) > 1:
                    # if there's more than one event's summary, summarize again
                    text = " ".join([item["summary"] for item in self.backlog])
                    summary = await self.summarize(text)
                    url = self.backlog[-1]["url"]  # use the url of the last commit
                else:
                    # if there's only one event's summary, use it as is
                    summary = self.backlog[0]["summary"]
                    url = self.backlog[0]["url"]

                # ensure the summary is within the 500 character limit
                summary = summary[:500]

                self.api.publish(caption="🤖" + summary, url=url)
                logging.info(f'Successfully posted new thread with message: {summary}')

                self.last_post_time = datetime.now()
                self.backlog = []  # clear the backlog
        except Exception as e:
            logging.error(f'Error posting new thread: {e}', exc_info=True)

    def verify_signature(self, payload, signature, secret):
        expected_signature = hmac.new(
            bytes(secret, 'utf-8'), 
            msg=payload, 
            digestmod=hashlib.sha1
        ).hexdigest()

        return hmac.compare_digest('sha1=' + expected_signature, signature)

# Initialize the GithubThreader
github_threader = GithubThreader()

# Start the GithubThreader
uvicorn.run(github_threader.app, host='0.0.0.0', port=5000)
