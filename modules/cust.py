import telegram
from http import HTTPStatus
import requests
from .user import insert_user
from models import User, CustLatestSemester, CustStudent, CustScore
import json
from peewee import DoesNotExist

APISUCKS_SCORE_URL_FORMAT = 'https://api.vimsucks.com:8000/cust/student/%s/score'


def check_score_update(bot: telegram.Bot, student):
    resp = requests.post(APISUCKS_SCORE_URL_FORMAT % student.sid, {
        'password': student.password,
    })
    if resp.status_code != HTTPStatus.OK:
        return
    semester = json.loads(resp.text)[-1]['Semesters'][-1]
    try:
        latest_semester = CustLatestSemester.get(student=student)
        # 新学期
        if latest_semester.name != semester['Name']:
            latest_semester.name = semester['Name']
            CustScore.delete().where(CustScore.student == student)
            latest_semester.save()
    except DoesNotExist:
        latest_semester = CustLatestSemester.create(student=student, name=semester['Name'])
    scores = CustScore.select().where(CustScore.student == student)
    scores_map = {}
    for score in scores:
        scores_map[score.name] = score
    new_scores = []
    for score in semester['Scores']:
        new_scores.append(CustScore(
            student=student,
            name=score['Name'],
            classification=score['Type'],
            credit=score['Credit'],
            period=score['Period'],
            score=score['Score'],
            review=score['Review'],
            exam_type=score['ExamType'],
        ))
    updated_scores = []
    for score in new_scores:
        try:
            old_score = scores_map[score.name]
            if old_score != score:
                old_score.score = score.score
                old_score.review = score.review
                updated_scores.append(score)
                old_score.save()
        except KeyError:
            updated_scores.append(score)
            score.save()
            pass
    text = ""
    if len(updated_scores) != 0:
        for score in updated_scores:
            text += "%s  %s %s\n" % (score.name, score.score, score.review)
        bot.send_message(student.user.id, text)


def command_login(bot: telegram.Bot, update: telegram.Update, args):
    sid, password = args[1], args[2]
    resp = requests.post(APISUCKS_SCORE_URL_FORMAT % sid, {
        'password': password,
    })
    if resp.status_code == HTTPStatus.OK:
        user = User.select().where(User.id == update.message.from_user.id).first()
        student, created = CustStudent.get_or_create(user=user, sid=sid, password=password)
        if not created:
            bot.send_message(user.id, '您已绑定学号 %s，无需重新绑定' % sid)
            return
        bot.send_message(user.id, '您已绑定学号 %s' % sid)
        check_score_update(bot, student)


def command_logout(bot: telegram.Bot, update: telegram.Update, args):
    try:
        user = User.select().where(User.id == update.message.from_user.id).first()
        student = CustStudent.get(user=user)
        CustLatestSemester.delete().where(CustLatestSemester.student == student)
        CustScore.delete().where(CustScore.student == student)
        bot.send_message(user.id, "您已取消绑定学号 %s", student.sid)
    except Exception:
        pass


def command_score(bot: telegram.Bot, update: telegram.Update, args):
    user = User.select().where(User.id == update.message.from_user.id).first()
    student = None
    try:
        student = CustStudent.get(user=user)
    except DoesNotExist:
        bot.send_message(user.id, '请先绑定教务管理系统账户：/cust login 学号 密码')
        return
    check_score_update(bot, update, student)


def handle(bot: telegram.Bot, update: telegram.Update, args):
    insert_user(update.message.from_user)
    sub_command = args[0]
    if sub_command == "login":
        command_login(bot, update, args)
    elif sub_command == "logout":
        command_logout(bot, update, args)
    elif sub_command == 'score':
        command_score(bot, update, args)


def callback_check_score(bot, job):
    students = CustStudent.select()
    for student in students:
        check_score_update(bot, student)
