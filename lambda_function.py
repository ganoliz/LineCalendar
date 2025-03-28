import json
import os

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.models import ImageSendMessage

import boto3
from botocore.exceptions import ClientError

from typing import Literal
from langchain_core.tools import tool

from langchain_together import ChatTogether

from langchain_core.documents import Document

from langchain_core.messages import SystemMessage, RemoveMessage, AIMessage
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
import urllib
import datetime
import requests

line_bot_api = LineBotApi(os.environ['channel_access_token'])
handler = WebhookHandler(os.environ['channel_secret'])

TOGETHER_API_KEY = os.environ['TOGETHER_API_KEY']

USE_SQS = False


class GoogleCalendarGeneratorInput(BaseModel):
    """Input for Google Calendar Generator."""
    
    dates: str = Field(..., description=f"Datetime symbol. format should be YYYYMMDDTHHMMSS/YYYYMMDDTHHMMSS. Current tims is {datetime.datetime.now()}")
    title: str = Field(..., description="Calendar Title symbol for reserving schedule.")
    description: str = Field(..., description="Calendar schedule summary with some Warnings for schedule description.")
    location: str = Field(..., description="Calendar location symbol for reservation.")

def create_calender_url(title='Test time', date='20250403T180000/20250403T220000', location='台中', description='I know'):
    base_url = "https://www.google.com/calendar/render?action=TEMPLATE"
    event_url = f"{base_url}&text={urllib.parse.quote(title)}&dates={date}&location={urllib.parse.quote(location)}&details={urllib.parse.quote(description)}"
    return event_url+"&openExternalBrowser=1"

def linebot(event):
    

    body = json.loads(event['body']) # no header  json.loads(event['body'])
    print('body=', body)
    # handler.handle(body, signature)    # I can't match body and signature now. Probably have error with headers

    replyToken = body['events'][0]['replyToken']
    type = body['events'][0]['message']['type']


    if type == 'text':
        
        msg = body['events'][0]['message']['text']

        llm = ChatTogether(
                    model='meta-llama/Llama-3.3-70B-Instruct-Turbo-Free',
                    together_api_key=TOGETHER_API_KEY)

        prompt_template = ChatPromptTemplate([('system', '''You are a helpful secretary to create a schedule for user. 
                                        Notes that if user mention before what time. Create dates from now to deadline.
                                        If there are some warnings need to mention, use description to list key points.'''),
                                     ("user", "Here is the schedule: {msgs}")]) 

        structured_llm = llm.with_structured_output(GoogleCalendarGeneratorInput)
        compose_llm = prompt_template | structured_llm 
        output = None
        idx = 0
        while output is None:
            output = compose_llm.invoke({"msgs": msg})
            idx += 1
            if idx > 10:
                return "Error: Failed to create schedule. Please try again."
        
        ai_message = create_calender_url(title=output.title, date=output.dates, description=output.description, location = output.location)
        
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


    # Need to delete message that have processed
    if USE_SQS == True:
        try:
            sqs = boto3.client('sqs')
            queue_url = 'https://sqs.ap-southeast-1.amazonaws.com/438465157691/langchain_lambda'
            receipt_handle = event['receiptHandle']
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
        except Exception as e:
            print(f"Error deleting message from queue. {str(e)}")

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

