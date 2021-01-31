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
kf_url = "http://220.116.228.93:8089"

webhook = WebhookClient(url)
scheduler = BackgroundScheduler()

# global for data
DATA_INTERVAL = 100
TRAIN_DATA_PATH = "/data/mnist/train"
FAISS_TRAIN_DATA_PATH = "/data/faiss/train"

NUM_TRAINED_DATA = [0, 0]
NUM_SEEKED_DATA = [0, 0]

def send_interactive_slack(text):
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

def send_notice_slack(text, text2):
    p = {
            "text": text,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": text
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": text2
                    }
                }
            ]
    }
    webhook.send(text=p["text"], blocks=p["blocks"])

def seek_data(train_data_path, faiss_train_data_path):
    train_data = glob.glob(os.path.join(train_data_path, "**/*.png"))
    faiss_train_data = glob.glob(os.path.join(faiss_train_data_path, "**/*.png"))

    return [len(train_data), len(faiss_train_data)]

def exec_data():
    global NUM_SEEKED_DATA, NUM_TRAINED_DATA

    NUM_SEEKED_DATA = seek_data(TRAIN_DATA_PATH, FAISS_TRAIN_DATA_PATH)
    
    text = "{} new data for embedding and {} new data for faiss is detected".format(str(NUM_SEEKED_DATA[0] - NUM_TRAINED_DATA[0]), str(NUM_SEEKED_DATA[1] - NUM_TRAINED_DATA[1]))
    app.logger.info(text)

    if NUM_SEEKED_DATA[0] > NUM_TRAINED_DATA[0] + DATA_INTERVAL or NUM_SEEKED_DATA[1] > NUM_TRAINED_DATA[1] + DATA_INTERVAL:
        send_interactive_slack(text)    
    else:
        send_notice_slack(text, "No Need to Train!!!")

def get_jobs():
    list_jobs = scheduler.get_jobs()
    return [str(job) + " Pending" if job.pending else str(job) + " Running" for job in list_jobs]

@app.route("/start")
def start():
    if scheduler.running:
        scheduler.resume()
    else:
        # job_id = scheduler.add_job(exec_data, 'cron', hour=0, minute=0, second=0, id="data")
        job_id = scheduler.add_job(exec_data, 'interval', seconds=60, id="data")
        scheduler.start()
    
    return {"jobs": get_jobs()}

@app.route("/status")
def status():
    return {"jobs": get_jobs()}

@app.route("/stop")
def stop():
    scheduler.pause()

    return {"jobs": get_jobs()}

@app.route("/actions", methods=["POST"])
def action():
    data = request.form["payload"]
    data = json.loads(data)
    answer = data["actions"][0]["value"]
    app.logger.info(answer)

    status = ""
    if answer == "train":
        global NUM_SEEKED_DATA, NUM_TRAINED_DATA
        NUM_TRAINED_DATA[0] = NUM_SEEKED_DATA[0]
        NUM_TRAINED_DATA[1] = NUM_SEEKED_DATA[1]

        send_notice_slack("Here is Kubeflow URL", "Kubeflow URL: {}".format(kf_url))

    return '', 204

@app.route("/send", methods=["POST"])
def send():
    text = request.form["text"]
    text2 = request.form["text2"]

    status = ""

    try:
        send_notice_slack(text, text2)
        status = 1
    except:
        status = 0

    return {"status": status}

if __name__ == "__main__":
    app.run(host='0.0.0.0', port='8088', debug=True)