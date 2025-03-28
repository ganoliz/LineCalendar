# Linebot Auto Generate Google Calendar Event

Use AWS APIGateway + Lambda, Langchain and **Llama-3.3-70B** to develop this tool. Here is my [Linebot](https://lin.ee/67zlLA8)


![images](https://github.com/ganoliz/LineCalendar/blob/main/images/flowchart.jpg)

## Demo:

![images](https://github.com/ganoliz/LineCalendar/blob/main/images/demo.jpg)

```
User: Sentry is Crashing Google Cloud Next 2025
April 9 - 11, 2025 | Las Vegas, NV

We’re heading to Google Cloud Next 2025, and if you’ve landed on this page, you probably are too. Or maybe you just clicked the wrong link. Either way, if your app is riddled with errors, performance issues, or just an existential crisis, swing by booth #1711.
```
```
Linebot:  https://www.google.com/calendar/render?action=TEMPLATE&text=Sentry%20is%20Crashing%20Google%20Cloud%20Next%202025&dates=20250409T000000/20250411T235959&location=Las%20Vegas%2C%20NV&details=Join%20us%20at%20booth%20%231711%20to%20discuss%20error%20and%20performance%20issues%20with%20your%20app.%20Key%20points%20to%20discuss%3A%20error%20resolution%2C%20performance%20optimization%2C%20and%20existential%20crisis%20resolution.&openExternalBrowser=1
```
[Link](https://www.google.com/calendar/render?action=TEMPLATE&text=Sentry%20is%20Crashing%20Google%20Cloud%20Next%202025&dates=20250409T000000/20250411T235959&location=Las%20Vegas%2C%20NV&details=Join%20us%20at%20booth%20%231711%20to%20discuss%20error%20and%20performance%20issues%20with%20your%20app.%20Key%20points%20to%20discuss%3A%20error%20resolution%2C%20performance%20optimization%2C%20and%20existential%20crisis%20resolution.&openExternalBrowser=1)
## How to implement

When using langchain, we can use structure output  ```.with_structured_output()``` and here is my define pydantic class:

```python 
class GoogleCalendarGeneratorInput(BaseModel):
    """Input for Google Calendar Generator."""
    
    dates: str = Field(..., description=f"Datetime symbol. format should be YYYYMMDDTHHMMSS/YYYYMMDDTHHMMSS. Current tims is {datetime.datetime.now()}")
    title: str = Field(..., description="Calendar Title symbol for reserving schedule.")
    description: str = Field(..., description="Calendar schedule summary with some Warnings for schedule description.")
    location: str = Field(..., description="Calendar location symbol for reservation.")

structured_llm = llm.with_structured_output(GoogleCalendarGeneratorInput)
compose_llm = prompt_template | structured_llm 
output = compose_llm.invoke({"msgs": msg})

```
**Note that only some model providers provide native APIs for structuring outputs which .with_structured_output() implements from.** 

System prompt:
```python
sysprompt = '''You are a helpful secretary to create a schedule for user. 
				Notes that if user mention before what time. Create dates from now to deadline.
				If there are some warnings need to mention, use description to list key points.'''
``` 







**Reference**: 

[新米到上手 LangChain: 藉由 Function Agent 在 LINE Bot 上處理 Calendar 資訊！](https://nijialin.com/2023/08/18/first-time-langchain-line-bot/)

[LangChain](https://python.langchain.com/docs/introduction/)

[Google Calendar API](https://developers.google.com/calendar/api/guides/overview)

[AWS APIGateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html)

[AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)