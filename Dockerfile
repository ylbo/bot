FROM 1635537446/bot-base:latest

ADD bot.py /bot
CMD ["python", "/bot/bot.py"]