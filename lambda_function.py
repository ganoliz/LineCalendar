import json
import os
import urllib
import datetime
import requests

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.models import ImageSendMessage

from typing import Literal
from langchain_core.tools import tool
from langchain_together import ChatTogether
from langchain_core.documents import Document
from langchain_core.messages import SystemMessage, RemoveMessage, AIMessage
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

import boto3
from botocore.exceptions import ClientError

line_bot_api = LineBotApi(os.environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['CHANNEL_SECRET'])
TOGETHER_API_KEY = os.environ['TOGETHER_API_KEY']
SQS_QUEUE_URL = os.environ['SQS_QUEUE_URL']
USE_SQS = False
time_now = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
class GoogleCalendarGeneratorInput(BaseModel):
    """Input for Google Calendar's Event Generator."""
    
    datetime: str = Field(..., description=f"Calendar datetime symbol of the schedule. format MUST be YYYYMMDDTHHMMSS/YYYYMMDDTHHMMSS. Current time is  {time_now}.")
    title: str = Field(..., description="Calendar Title symbol for reserving schedule.")
    description: str = Field(..., description="Calendar schedule summary needed to mentioned.")
    location: str = Field(..., description="Calendar location symbol for reservation.")

def create_calender_url(title='Test time', date='20250403T180000/20250403T220000', location='台中', description='I know'):
    base_url = "https://www.google.com/calendar/render?action=TEMPLATE"
    event_url = f"{base_url}&text={urllib.parse.quote(title)}&dates={date}&location={urllib.parse.quote(location)}&details={urllib.parse.quote(description)}"
    return event_url+"&openExternalBrowser=1"

def linebot(event):
    
    body = json.loads(event['body']) 
    # print('body=', body)

    replyToken = body['events'][0]['replyToken']
    type = body['events'][0]['message']['type']

    if type == 'text':
        
        msg = body['events'][0]['message']['text']
        llm = ChatTogether(
                    model='meta-llama/Llama-3.3-70B-Instruct-Turbo-Free',
                    together_api_key=TOGETHER_API_KEY)
        prompt_template = ChatPromptTemplate([('system', '''You are a helpful secretary for scheduling meeting, interview, event, activities. 
                                        Here are some suggestions: 
                                            - If there are some warnings or informations need to mention, use description to list some key points, 1. 2. 3. ...etc each line.
                                            - If the schedule provide a start time (e.g., "Meeting at 3 PM") and don't provide a end time. You should estimate a end time (meeting would be 1 hour long and interview 2 hours).
                                               '''),
                                     ("user", "{msgs}")]) 

        structured_llm = llm.with_structured_output(GoogleCalendarGeneratorInput)
        compose_llm = prompt_template | structured_llm 
        output = None
        idx = 0
        while output is None:
            output = compose_llm.invoke({"msgs": msg})
            idx += 1
            if idx > 10:
                return "Error: Failed to create schedule. Please try again."
        
        # Generate calender url from auto-generated schedule
        ai_message = create_calender_url(title=output.title, date=output.datetime, description=output.description, location = output.location)
        
        # message length check
        if len(ai_message) >=5000:
            ai_message = ai_message[:4986]
            line_bot_api.reply_message(replyToken, TextSendMessage(ai_message+' <超過Line字數上限!>'))
        else:
            line_bot_api.reply_message(replyToken, TextSendMessage(ai_message))

    return 'Default Return'

# Entrypoint of AWS Lambda
def handler(event, context):

    print("the event is :", event, '\n')

    if USE_SQS == True:
        event = event['Records'][0]   # We use  standard SQS and have a default Records key at outer scope

    message_result = linebot(event)
    print('Message result:', message_result)

    # Need to delete message that have processed in SQS
    if USE_SQS == True:
        try:
            sqs = boto3.client('sqs')
            queue_url = SQS_QUEUE_URL
            receipt_handle = event['receiptHandle']
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
        except Exception as e:
            print(f"Error deleting message from queue. {str(e)}")

    return {
        'statusCode': 200,
        'body': json.dumps('Response success from Lambda!')
    }

