import json
import peewee
import requests
import telegram
from telegram.ext import CommandHandler

from models import *
from modules.user import insert_user
from .handler import Handler
from .job import RepeatingJob


class RepoNotFoundException(Exception):
    def __init__(self, message):
        super().__init__(message)


class GithubHandler(Handler):
    API_REPO_URL = 'https://api.github.com/repos/%s'
    API_RELEASES_URL = 'https://api.github.com/repos/%s/releases'

    def __init__(self):
        super().__init__("gh_release", pass_args=True)

    def get_repo_api_url(self, repo):
        return GithubHandler.API_REPO_URL % repo

    def get_release_api_url(self, repo):
        return GithubHandler.API_RELEASES_URL % repo

    # 调用 API，获取 repo 信息
    def get_repo(self, repo):
        resp = requests.get(self.get_repo_api_url(repo))
        if resp.status_code == 404:
            raise RepoNotFoundException("Repo %s not found" % repo)
        return json.loads(resp.text)

    def insert_repo(self, repo_name: str):
        repo_query = Repo.select().where(Repo.name == repo_name)
        if not repo_query.exists():
            repo_json = self.get_repo(repo_name)
            Repo.create(id=repo_json['id'],
                        name=repo_name)

    def check_release(self, repo, user, bot):
        releases = self.get_releases(repo.name)
        # GitHub API 返回的 release 数据是根据时间由新->旧排序的
        for release in releases:
            release_query = Release.select().where(Release.id == release['id'])
            # 检查数据库中是否存在该 repo，如果不存在，则插入
            if not release_query.exists():
                Release.create(id=release['id'],
                               repo_id=repo.id,
                               api_url=release['url'],
                               url=release['html_url'],
                               name=release['name'],
                               author_id=release['author']['id'],
                               created_at=release['created_at'],
                               published_at=release['published_at'])
            # 如果存在，则 break
            else:
                break

            author = release['author']
            author_query = Author.select().where(Author.id == author['id'])
            if not author_query.exists():
                Author.create(id=author['id'],
                              username=author['login'],
                              api_url=author['url'],
                              url=author['html_url'])
        latest_release = Release.select().where(Release.repo_id == repo.id).order_by(
            Release.published_at.desc()).first()
        if latest_release is None:
            bot.send_message(user.id, text='it seems that %s does not have any release' % repo.name)
            return
        latest_release_repo = LatestReleaseRepo.select().where(LatestReleaseRepo.repo_id == repo.id).first()
        if latest_release_repo is None:
            LatestReleaseRepo.create(release=latest_release, repo=repo)
            bot.send_message(user.id,
                             text='%s new release %s: %s' % (repo.name, latest_release.name, latest_release.url))
        elif latest_release_repo.release.id != latest_release.id:
            latest_release_repo.release = latest_release
            latest_release_repo.save()
            bot.send_message(user.id,
                             text='%s new release %s: %s' % (repo.name, latest_release.name, latest_release.url))

    def get_releases(self, repo):
        release_url = self.get_release_api_url(repo)
        resp = requests.get(release_url)
        if resp.status_code == 404:
            raise RepoNotFoundException("Repo %s not found" % repo)
        return json.loads(resp.text)

    def commandWatch(self, bot: telegram.Bot, update: telegram.Update, args):
        repo_name = args[1]
        self.insert_repo(repo_name)
        repo = Repo.get(name=repo_name)
        user = User.get(id=update.message.from_user.id)
        self.check_release(repo, user, bot)
        RepoWatchUser.create(user=user, repo_id=repo)
        bot.send_message(chat_id=update.message.chat_id, text='Now you are watching repo %s' % repo_name)

    def commandUnwatch(self, bot: telegram.Bot, update: telegram.Update, args):
        repo_name = args[1]
        repo = Repo.get(name=repo_name)
        user = User.get(id=update.message.from_user.id)
        RepoWatchUser.delete().where(user == user, repo == repo)
        bot.send_message(chat_id=update.message.chat_id, text='Now you are no longer watching repo %s' % repo_name)

    def handle(self, bot: telegram.Bot, update: telegram.Update, args):
        insert_user(update.message.from_user)
        try:
            sub_command = args[0]
            if sub_command == 'watch':
                self.commandWatch(bot, update, args)
            elif sub_command == 'unwatch':
                self.commandUnwatch(bot, update, args)
        except IndexError:
            bot.send_message(chat_id=update.message.chat_id, text='Error! /gh_release (un)watch owner/repo')
        except peewee.IntegrityError as e:
            bot.send_message(chat_id=update.message.chat_id, text='Error! you are already watching repo %s' % args[1])
        except Exception as e:
            bot.send_message(chat_id=update.message.chat_id, text=str(e))


class GithubJob(RepeatingJob):
    def __init__(self):
        super().__init__(interval=60 * 30, first=0)

    def callback(self, bot, callback):
        handler = GithubHandler()
        repo_watch_users = RepoWatchUser.select()
        # TODO: 使用线程池
        for repo_watch_user in repo_watch_users:
            handler.check_release(repo_watch_user.repo, repo_watch_user.user, bot)
