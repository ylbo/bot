FROM python:3.8

WORKDIR /bot
ADD bot.py /bot
ADD requirements.txt /bot
RUN pip install -r requirements.txt
CMD ["python", "/bot/bot.py"]