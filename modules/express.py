import base64
import hashlib
import json
import peewee
import requests
import telegram
from fuzzywuzzy import fuzz, process

from models import User, ExpressPackage, ExpressPackageWatchUser, ExpressCompany
from config import KDNIAO_APP_KEY, KDNIAO_USER_ID
from .user import insert_user
from ._express_company import *
from .handler import Handler
from .job import RepeatingJob


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


class ExpressHandler(Handler):
    API_URL = 'http://api.kdniao.cc/Ebusiness/EbusinessOrderHandle.aspx'

    STATE_NOT_EXISTS = 0
    STATE_ON_THE_WAY = 2
    STATE_SIGNED = 3
    STATE_PROBLEM = 4

    def __init__(self):
        super().__init__("express", pass_args=True)

    # 数据内容签名：把(请求内容(未编码)+AppKey)进行MD5加密，然后Base64编码，最后 进行URL(utf-8)编码。
    def encrypt(self, data, app_key):
        m = hashlib.md5()
        m.update((data + app_key).encode('utf-8'))
        return base64.b64encode(m.hexdigest().encode(encoding='utf-8'))

    # 根据物流单号得到快递公司编码
    def get_company(self, logistic_code):
        request_data = json.dumps({'LogisticCode': logistic_code})
        post_data = {
            'RequestData': request_data,
            'EBusinessID': KDNIAO_USER_ID,
            'RequestType': '2002',
            'DataType': '2',
            'DataSign': self.encrypt(request_data, KDNIAO_APP_KEY).decode()
        }
        json_data = json.loads(requests.post(ExpressHandler.API_URL, post_data).text)
        if json_data['Success'] == False:
            raise CompanyNotFoundException('Company not found for %s' % logistic_code)
        code = json_data['Shippers'][0]['ShipperCode']
        name = json_data['Shippers'][0]['ShipperName']
        company, created = ExpressCompany.get_or_create(code=code, name=name)
        return company

    # 获取快递运输追踪数据
    def get_trace_detail(self, logistic_code, company_code):
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
            'DataSign': self.encrypt(request_data, KDNIAO_APP_KEY).decode()
        }
        return json.loads(requests.post(ExpressHandler.API_URL, post_data).text)

    def is_express_updated(self, package: ExpressPackage):
        trace_detail = self.get_trace_detail(package.logistic_code, package.company.code)
        if trace_detail['State'] == ExpressHandler.STATE_NOT_EXISTS and trace_detail['Success'] == True:
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

    def send_update(self, user: User, package: ExpressPackage, bot: telegram.Bot):
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

    def commandWatch(self, bot: telegram.Bot, update: telegram.Update, args):
        user = User.select().where(User.id == update.message.from_user.id).first()
        logistic_code = args[1]
        company = None
        try:
            if len(args) >= 3:
                company_code = args[2]
                company = ExpressCompany.get(code=company_code)
            if company is None:
                company = self.get_company(logistic_code)
            package, _ = ExpressPackage.get_or_create(logistic_code=logistic_code, company=company)
            self.is_express_updated(package)
            self.send_update(update.message.from_user, package, bot)
            _, created = ExpressPackageWatchUser.get_or_create(user=user, package=package)
            if not created:
                return bot.send_message(chat_id=update.message.chat_id, text='您已经追踪 %s 包裹 %s' % (
                    package.company.name, logistic_code))
            bot.send_message(chat_id=update.message.chat_id,
                             text='Now you are watching express package %s %s' % (
                                 package.company.name, logistic_code))
        except peewee.DoesNotExist:
            return bot.send_message(chat_id=update.message.chat_id,
                                    text='您输入的公司代号 %s 有误，请输入 /express company 来查看支持的公司' % (
                                        company_code))
        except CompanyNotFoundException:
            return bot.send_message(chat_id=update.message.chat_id, text='快递 %s 的承运公司不存在，请检查您的单号' % (
                logistic_code))
        except PackageTraceNotFoundException:
            return bot.send_message(chat_id=update.message.chat_id, text='没有查到快递 %s 的轨迹信息' % (
                logistic_code))
        except KdniaoApiException:
            return bot.send_message(chat_id=update.message.chat_id, text='快递鸟 API 调用时发生错误，请稍后再试')

    def commandUnwatch(self, bot: telegram.Bot, update: telegram.Update, args):
        user = User.select().where(User.id == update.message.from_user.id).first()
        logistic_code = args[1]
        try:
            package = ExpressPackage.get(ExpressPackage.logistic_code == logistic_code)
            ExpressPackageWatchUser.get(ExpressPackageWatchUser.user == user,
                                        ExpressPackageWatchUser.package == package).delete_instance()
        except peewee.DoesNotExist:
            bot.send_message(chat_id=update.message.chat_id,
                             text='快递 %s 不存在' % logistic_code)
        bot.send_message(chat_id=update.message.chat_id,
                         text='Now you are no longer watching express package %s' % logistic_code)

    def commandCompany(self, bot: telegram.Bot, update: telegram.Update, args):
        if len(args) >= 2:
            text = ''
            company_name = args[1]
            results = process.extractBests(company_name, express_company_names)
            for name, ration in results:
                text += '%s -- %s\n' % (name, express_company_name_to_code[name])
            bot.send_message(chat_id=update.message.chat_id,
                             text=text)

    def handle(self, bot: telegram.Bot, update: telegram.Update, args):
        insert_user(update.message.from_user)
        sub_command = args[0]
        # 【开始监控】子命令： /express watch 快递单号 [描述]
        if sub_command == 'watch':
            self.commandWatch(bot, update, args)
        # 【停止监控】子命令： /express unwatch 快递单号
        elif sub_command == 'unwatch':
            self.commandUnwatch(bot, update, args)
        elif sub_command == 'company':
            self.commandCompany(bot, update, args)


class ExpressJob(RepeatingJob):
    def __init__(self):
        super().__init__(interval=60 * 30, first=0)

    def callback(self, bot, callback):
        # TODO: 使用线程池
        handler = ExpressHandler()
        query = ExpressPackageWatchUser.select(ExpressPackageWatchUser.package).distinct()
        for entry in query:
            package = entry.package
            if handler.is_express_updated(package):
                for watch_user in ExpressPackageWatchUser.select().where(ExpressPackageWatchUser.package == package):
                    handler.send_update(watch_user.user,
                                        watch_user.package,
                                        bot)
            if package.state == ExpressHandler.STATE_SIGNED:
                for watch_user in ExpressPackageWatchUser.select().where(ExpressPackageWatchUser.package == package):
                    bot.send_message(watch_user.user.id,
                                     "您的【%s】快递 %s 已签收，将停止跟踪" % (package.company.name, package.logistic_code))
                    watch_user.delete_instance()
