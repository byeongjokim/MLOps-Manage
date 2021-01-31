from flask import Flask
from flask import request, jsonify

from slack_sdk.webhook import WebhookClient

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import os
import glob
import json

app = Flask(__name__)
url = "https://hooks.slack.com/services/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"
webhook = WebhookClient(url)
scheduler = BackgroundScheduler()

jobs = []

# global for data
DATA_INTERVAL = 100
TRAIN_DATA_PATH = "/data/mnist/train"
FAISS_TRAIN_DATA_PATH = "/data/faiss/train"
pre_num_data = [0, 0]

def send_slack(text):
    p = {
            "text": text,
            "attachments": [
            {
                    "text": "Would you like to train models?",
                    "fallback": "abcd",
                    "callback_id": "confirm",
                    "color": "#3AA3E3",
                    "attachment_type": "default",
                    "actions": [
                    {
                            "name": "answer",
                            "type": "button",
                            "text": "Train!",
                            "value": "train",
                            "confirm": {
                                    "title": "Are you sure?",
                                    "text": "Do Train?",
                                    "ok_text": "Yes",
                                    "dismiss_text": "No"
                            }
                    },
                    {
                            "name": "answer",
                            "type": "button",
                            "text": "Nope!",
                            "value": "nope"
                    }
                    ]
            }
            ]
    }
    webhook.send(text=p["text"], response_type="in_channel", attachments=p["attachments"])

def seek_data(train_data_path, faiss_train_data_path):
    train_data = glob.glob(os.path.join(train_data_path, "**/*.png"))
    faiss_train_data = glob.glob(os.path.join(faiss_train_data_path, "**/*.png"))

    return [len(train_data), len(faiss_train_data)]

def exec_data():
    global pre_num_data

    num_data = seek_data(TRAIN_DATA_PATH, FAISS_TRAIN_DATA_PATH)

    if num_data[0] > pre_num_data[0] + DATA_INTERVAL or num_data[1] > pre_num_data[1] + DATA_INTERVAL:
        send_slack("{} new data for embedding and {} new data for faiss is detected".format(str(num_data[0] - pre_num_data[0]), str(num_data[1] - pre_num_data[1])))
        pre_num_data = num_data

@app.route("/start")
def start():
    global jobs

    if scheduler.running:
        scheduler.resume()
    else:
        # job_id = scheduler.add_job(exec_data, 'cron', hour=0, minute=0, second=0, id="data")
        job_id = scheduler.add_job(exec_data, 'interval', seconds=30, id="data")
        jobs.append(job_id)
        
        scheduler.start()

    return {"jobs": "{} jobs are starting".format(len(jobs))}

@app.route("/stop")
def stop():
    scheduler.pause()
    return {"jobs": "{} jobs are paused".format(len(jobs))}

@app.route("/actions", methods=["POST"])
def action():
    data = request.form["payload"]
    data = json.loads(data)
    answer = data["actions"][0]["value"]

    app.logger.info(answer)
    
    # if answer == "train":
    
    return {"answer": answer}

if __name__ == "__main__":
    app.run(host='0.0.0.0', port='8088', debug=True)