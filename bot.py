#!/usr/bin/env python
# pylint: disable=C0116
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to send timed Telegram messages.
This Bot uses the Updater class to handle the bot and the JobQueue to send
timed messages.
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Basic Alarm Bot example, sends a message after a set time.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
from datetime import time

import akshare as ak
import yaml
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

fund_map = {}
name_map = {}
global token


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update: Update, _: CallbackContext) -> None:
    update.message.reply_text('使用/help查看 使用说明\n'
                              '/set hour minute 设定定时任务 每天早上9点推送\n'
                              '/unset 取消定时任务\n'
                              '/status 查看定时任务状态\n'
                              '/add ids 添加基金id 多个id用空格隔开\n'
                              '/del ids 删除基金id 多个id用空格隔开\n'
                              '/query 当前添加的基金id')


def get_config():
    with open("config.yml", encoding="utf8") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
        global token
        token = config["token"]


def get_name():
    fund_em_fund_name_df = ak.fund_em_fund_name()
    fund_em_fund_name_df.index = fund_em_fund_name_df["基金代码"]
    name_map.update(fund_em_fund_name_df["基金简称"].to_dict())


def get_value(fund_id):
    fund_em_info_df = ak.fund_em_open_fund_info(fund=fund_id, indicator="单位净值走势")
    return fund_em_info_df.iloc[-1, 1]


def get_rank_rate(fund_id):
    rank_rate = ak.fund_em_open_fund_info(fund=fund_id, indicator="同类排名百分比")
    return rank_rate.iloc[-1, 1]


def alarm(context: CallbackContext) -> None:
    """Send the alarm message."""
    job = context.job
    chat_id = job.name
    template = "名称：{}, 基金代码：{}, 最新单位净值：{}, 排名百分比：{}%\n\n"
    text = ""
    for i in list(fund_map.get(chat_id)):
        text = text + template.format(name_map.get(i), i, get_value(i), get_rank_rate(i))
    context.bot.send_message(job.context, text)


def add_fund(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.message.chat_id)
    if fund_map.get(chat_id) is None:
        fund_map[chat_id] = set()
    tmp: set = fund_map[chat_id]
    logger.info(context.args)
    for i in context.args:
        tmp.add(i)
    update.message.reply_text("添加成功")


def query_fund(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.message.chat_id)
    if fund_map.get(chat_id) is None or len(fund_map.get(chat_id)) == 0:
        update.message.reply_text("没有信息")
    else:
        text = ""
        template = "名称：{}, 基金代码：{}\n"
        for i in list(fund_map.get(chat_id)):
            text = text + template.format(name_map.get(i), i)
        update.message.reply_text(text)


def del_fund(update: Update, context: CallbackContext) -> None:
    chat_id = str(update.message.chat_id)
    try:
        if fund_map.get(chat_id) is None:
            return
        else:
            tmp: set = fund_map.get(chat_id)
            for i in context.args:
                tmp.remove(i)
            update.message.reply_text("删除成功")
    except (IndexError, ValueError):
        update.message.reply_text('参数输入错误')


def job_status(update: Update, context: CallbackContext) -> None:
    current_jobs = context.job_queue.get_jobs_by_name(str(update.message.chat_id))
    if not current_jobs:
        msg = "任务未注册"
    else:
        msg = "任务进行中"
    update.message.reply_text(text=msg)


def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def set_timer(update: Update, context: CallbackContext) -> None:
    """Add a job to the queue."""
    chat_id = update.message.chat_id
    try:
        hour = 9
        minute = 0
        if len(context.args) == 1:
            hour = context.args[0]
        elif len(context.args) == 2:
            hour = context.args[0]
            minute = context.args[1]

        job_removed = remove_job_if_exists(str(chat_id), context)
        # context.job_queue.run_once(alarm, due, context=chat_id, name=str(chat_id))
        # context.job_queue.run_repeating(alarm, 5, context=chat_id, name=str(chat_id))
        context.job_queue.run_daily(alarm, time=time(hour - 8, minute, second=0),
                                    days=(1, 2, 3, 4, 5),
                                    context=chat_id, name=str(chat_id))

        text = '定时任务设置成功!'
        if job_removed:
            text += ' 旧的定时任务移除.'
        update.message.reply_text(text)

    except (IndexError, ValueError):
        update.message.reply_text("设定定时任务出错")


def unset(update: Update, context: CallbackContext) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = '定时任务取消成功!' if job_removed else '目前没有在进行的定时任务.'
    update.message.reply_text(text)


def main() -> None:
    """Run bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", start))
    dispatcher.add_handler(CommandHandler("set", set_timer))
    dispatcher.add_handler(CommandHandler("unset", unset))
    dispatcher.add_handler(CommandHandler("status", job_status))
    dispatcher.add_handler(CommandHandler("add", add_fund))
    dispatcher.add_handler(CommandHandler("query", query_fund))
    dispatcher.add_handler(CommandHandler("del", del_fund))

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    get_name()
    get_config()
    main()
