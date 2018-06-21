import base64
import hashlib
import json
import peewee
import requests
import telegram

from models import User, ExpressPackage, ExpressPackageWatchUser, ExpressCompany
from config import KDNIAO_APP_KEY,KDNIAO_USER_ID
from .user import insert_user

API_URL = 'http://api.kdniao.cc/Ebusiness/EbusinessOrderHandle.aspx'

STATE_NOT_EXISTS = 0
STATE_ON_THE_WAY = 2
STATE_SIGNED = 3
STATE_PROBLEM = 4


class CompanyNotFoundException(Exception):
    def __init__(self, message):
        super().__init__(message)


class PackageNotFoundException(Exception):
    def __init__(self, message):
        super().__init__(message)


class PackageTraceNotFoundException(Exception):
    def __init__(self, message):
        super().__init__(message)


class KdniaoApiException(Exception):
    def __init__(self, message):
        super().__init__(message)


# 数据内容签名：把(请求内容(未编码)+AppKey)进行MD5加密，然后Base64编码，最后 进行URL(utf-8)编码。
def encrypt(data, app_key):
    m = hashlib.md5()
    m.update((data + app_key).encode('utf-8'))
    return base64.b64encode(m.hexdigest().encode(encoding='utf-8'))


# 根据物流单号得到快递公司编码
def get_company(logistic_code):
    request_data = json.dumps({'LogisticCode': logistic_code})
    post_data = {
        'RequestData': request_data,
        'EBusinessID': KDNIAO_USER_ID,
        'RequestType': '2002',
        'DataType': '2',
        'DataSign': encrypt(request_data, KDNIAO_APP_KEY).decode()
    }
    json_data = json.loads(requests.post(API_URL, post_data).text)
    if json_data['Success'] == False:
        raise CompanyNotFoundException('Company not found for %s' % logistic_code)
    code = json_data['Shippers'][0]['ShipperCode']
    name = json_data['Shippers'][0]['ShipperName']
    company, created = ExpressCompany.get_or_create(code=code, name=name)
    return company


# 获取快递运输追踪数据
def get_trace_detail(logistic_code, company_code):
    request_data = json.dumps({
        'OrderCode': '',
        'ShipperCode': company_code,
        'LogisticCode': logistic_code
    })
    post_data = {
        'RequestData': request_data,
        'EBusinessID': KDNIAO_USER_ID,
        'RequestType': '1002',
        'DataType': '2',
        'DataSign': encrypt(request_data, KDNIAO_APP_KEY).decode()
    }
    return json.loads(requests.post(API_URL, post_data).text)


def is_express_updated(package: ExpressPackage):
    trace_detail = get_trace_detail(package.logistic_code, package.company.code)
    if trace_detail['State'] == STATE_NOT_EXISTS and trace_detail['Success'] == True:
        raise PackageTraceNotFoundException("Package 【%s】 %s trace not found")
    if trace_detail['Success'] == False:
        raise KdniaoApiException(trace_detail['Reason'])
    if len(trace_detail['Traces']) == 0:
        return False
    last_trace = trace_detail['Traces'][-1]
    if package.update_time is None or str(package.update_time) < last_trace['AcceptTime']:
        package.update_time = last_trace['AcceptTime']
        package.update_station = last_trace['AcceptStation']
        package.state = trace_detail['State']
        package.save()
        return True
    return False


def send_update(user: User, package: ExpressPackage, bot: telegram.Bot):
    if package.description is not None:
        return bot.send_message(user.id,
                                text='%s %s快递 【%s】 %s 已更新： %s' % (package.update_time,
                                                                  package.company.name,
                                                                  package.description,
                                                                  package.logistic_code,
                                                                  package.update_station))
    bot.send_message(user.id,
                     text='%s %s快递 %s 已更新： %s' % (package.update_time,
                                                  package.company.name,
                                                  package.logistic_code,
                                                  package.update_station))


def callback_check_express(bot, job):
    # TODO: 使用线程池
    query = ExpressPackageWatchUser.select(ExpressPackageWatchUser.package).distinct()
    for entry in query:
        package = entry.package
        if is_express_updated(package):
            for watch_user in ExpressPackageWatchUser.select().where(ExpressPackageWatchUser.package == package):
                send_update(watch_user.user,
                            watch_user.package,
                            bot)
        if package.state == STATE_SIGNED:
            for watch_user in ExpressPackageWatchUser.select().where(ExpressPackageWatchUser.package == package):
                bot.send_message(watch_user.user.id,
                                 "您的【%s】快递 %s 已签收，将停止跟踪" % (package.company.name, package.logistic_code))
                watch_user.delete_instance()


def handle(bot: telegram.Bot, update: telegram.Update):
    insert_user(update.message.from_user)
    commands: str = update.message.text.split()
    user = User.select().where(User.id == update.message.from_user.id).first()
    sub_command = commands[1]
    logistic_code = commands[2]

    # 【开始监控】子命令： /express watch 快递单号 [描述]
    if sub_command == 'watch':
        description = None
        company = None
        if len(commands) >= 4:
            company_code = commands[3]
            company, _ = ExpressCompany.get_or_create(code=company_code, name=company_code)
        try:
            if company is None:
                company = get_company(logistic_code)
            package, created = ExpressPackage.get_or_create(logistic_code=logistic_code, company=company)
            if not created:
                return bot.send_message(chat_id=update.message.chat_id, text='您已经追踪 %s 包裹 %s' % (
                    package.company.name, logistic_code))
        except CompanyNotFoundException:
            return bot.send_message(chat_id=update.message.chat_id, text='快递 %s 的承运公司不存在，请检查您的单号' % (
                logistic_code))
        try:
            is_express_updated(package)
            send_update(update.message.from_user, package, bot)
        except PackageTraceNotFoundException:
            return bot.send_message(chat_id=update.message.chat_id, text='没有查到快递 %s 的轨迹信息' % (
                logistic_code))
        except KdniaoApiException:
            return bot.send_message(chat_id=update.message.chat_id, text='快递鸟 API 调用时发生错误，请稍后再试')
        ExpressPackageWatchUser.get_or_create(user=user, package=package)
        bot.send_message(chat_id=update.message.chat_id,
                         text='Now you are watching express package %s %s' % (
                             package.company.name, logistic_code))

    # 【停止监控】子命令： /express unwatch 快递单号
    elif sub_command == 'unwatch':
        try:
            package = ExpressPackage.get(ExpressPackage.logistic_code == logistic_code)
            ExpressPackageWatchUser.get(ExpressPackageWatchUser.user == user,
                                        ExpressPackageWatchUser.package == package).delete_instance()
        except peewee.DoesNotExist:
            bot.send_message(chat_id=update.message.chat_id,
                             text='快递 %s 不存在' % logistic_code)
        bot.send_message(chat_id=update.message.chat_id,
                         text='Now you are no longer watching express package %s' % logistic_code)
