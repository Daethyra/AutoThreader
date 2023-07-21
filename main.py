import os
import logging
from flask import Flask, request, abort
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

load_dotenv()

class GithubThreader(ThreadsAPI, RequestHandler, TaskChain, EnvManager, DocStore, MemoryManager):
    def __init__(self):
        self.app = Flask(__name__)
        self.api = ThreadsAPI(
            username=os.getenv("THREADS_USERNAME"),
            password=os.getenv("THREADS_PASSWORD"),
        #    token=os.getenv("THREADS_TOKEN")  # optional (if you're already authenticated)
        )
        self.tokenizer = AutoTokenizer.from_pretrained("google/long-t5-local-base")
        self.model = LongT5Model.from_pretrained("google/long-t5-local-base")

    def listen_for_webhooks(self):
        @self.app.route('/webhook', methods=['POST'])
        def handle_webhook():
            signature = request.headers.get('X-Hub-Signature')
            data = request.data

            if not self.verify_signature(data, signature, os.getenv("WEBHOOK_SECRET")):
                logging.warning('Webhook signature verification failed')
                abort(403)  # Forbidden

            data = request.get_json()
            event_type = request.headers.get('X-GitHub-Event')
            self.process_webhook_data(data, event_type)
            return '', 200

    def process_webhook_data(self, data, event_type):
        try:
            if event_type == 'push':
                event_info = {
                    'repository': data['repository']['full_name'],
                    'pusher': data['pusher']['name'],
                    'commits': data['commits'],
                }
                self.activate_event(event_info)
                logging.info(f'Successfully ingested Github webhook for {event_info["repository"]}')
            else:
                logging.info(f'Received unhandled Github event type: {event_type}')
        except Exception as e:
            logging.error(f'Error processing Github webhook data: {e}')

    def activate_event(self, event_info):
        message = f"New commits pushed to {event_info['repository']} by {event_info['pusher']}."
        summary = self.summarize(message)
        self.post_thread(summary)

    def summarize(self, text):
        try:
            inputs = self.tokenizer(text, return_tensors="pt")
            outputs = self.model.generate(**inputs)
            summary = self.tokenizer.decode(outputs[0])
            logging.info(f'Successfully converted text to summary for thread post')
            return summary
        except Exception as e:
            logging.error(f'Error generating summary from text: {e}')
            return text  # return original text if summarization fails

    def post_thread(self, message):
        try:
            self.api.publish(caption=f"🤖{message}")
            logging.info(f'Successfully posted new thread with message: {message}')
        except Exception as e:
            logging.error(f'Error posting new thread: {e}')

    def verify_signature(self, payload, signature, secret):
        expected_signature = hmac.new(
            bytes(secret, 'utf-8'), 
            msg=payload, 
            digestmod=hashlib.sha1
        ).hexdigest()

        return hmac.compare_digest('sha1=' + expected_signature, signature)

    def run(self):
        self.listen_for_webhooks()
        self.app.route('/health', methods=['GET'])(self.health_check)
        self.app.run(host='0.0.0.0', port=5000)

    def health_check(self):
        return 'OK', 200

# Initialize the GithubThreader
github_threader = GithubThreader()

# Start the GithubThreader
github_threader.run()
