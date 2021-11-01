import re
import requests
import random
from login.Utils import Utils
from urllib3.exceptions import InsecureRequestWarning
from login.casLogin import casLogin
from login.iapLogin import iapLogin

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class wiseLoginService:
    # 初始化本地登录类
    def __init__(self, userInfo):
        if None == userInfo['username'] or '' == userInfo[
                'username'] or None == userInfo['password'] or '' == userInfo[
                    'password'] or None == userInfo[
                        'schoolName'] or '' == userInfo['schoolName']:
            raise Exception('初始化类失败，请键入完整的参数（用户名，密码，学校名称）')
        self.username = userInfo['username']
        self.password = userInfo['password']
        self.schoolName = userInfo['schoolName']
        self.session = requests.session()
        headers = {'User-Agent': random.choice(Utils.getUserAgents())}
         # 关闭多余的连接
        self.session.keep_alive = False
        # 增加重试次数
        self.session.adapters.DEFAULT_RETRIES = 5
        self.session.headers = headers
        self.login_url = ''
        self.campus_host = ''
        self.login_host = ''
        self.loginEntity = None
        self.login_type = ''
         # 如果设置了用户的代理，那么该用户将走代理的方式进行访问
        if 'proxy' in userInfo and userInfo['proxy'] is not None:
            print(f'{Utils.getAsiaTime()} 检测到代理ip配置，正在使用代理')
            self.session.proxies = {'http': userInfo['proxy'], 'https': userInfo['proxy']}
        # 添加hooks进行拦截判断该请求是否被418拦截
        self.session.hooks['response'].append(Utils.checkStatus)

    # 通过学校名称借助api获取学校的登陆url
    def getLoginUrlBySchoolName(self):
        schools = self.session.get(
            'https://mobile.campushoy.com/v6/config/guest/tenant/list',
            verify=False).json()['data']
        flag = False
        for item in schools:
            if item['name'] == self.schoolName:
                flag = True
                if item['joinType'] == 'NONE':
                    raise Exception(self.schoolName + '未加入今日校园，请检查...')
                params = {'ids': item['id']}
                data = self.session.get(
                    'https://mobile.campushoy.com/v6/config/guest/tenant/info',
                    params=params,
                    verify=False,
                ).json()['data'][0]
                joinType = data['joinType']
                ampUrl = data['ampUrl']
                ampUrl2 = data['ampUrl2']
                if 'campusphere' in ampUrl:
                    clientUrl = ampUrl
                elif 'campusphere' in ampUrl2:
                    clientUrl = ampUrl2
                else:
                    raise Exception('未找到客户端登录地址')
                res = self.session.get(clientUrl, verify=False)
                self.campus_host = re.findall('\w{4,5}\:\/\/.*?\/',
                                              clientUrl)[0]
                self.login_url = res.url
                self.login_host = re.findall('\w{4,5}\:\/\/.*?\/', res.url)[0]
                self.login_type = joinType
                break
        if flag == False:
            raise Exception(self.schoolName + '不存在或未加入今日校园')

    # 通过登陆url判断采用哪种登陆方式
    def checkLogin(self):
        if self.login_type == 'CLOUD':
            self.loginEntity = iapLogin(self.username, self.password,
                                        self.login_url, self.login_host,
                                        self.session)
            self.session.cookies = self.loginEntity.login()
        else:
            self.loginEntity = casLogin(self.username, self.password,
                                        self.login_url, self.login_host,
                                        self.session)
            self.session.cookies = self.loginEntity.login()

    # 本地化登陆
    def login(self):
        # 获取学校登陆地址
        self.getLoginUrlBySchoolName()
        self.checkLogin()
