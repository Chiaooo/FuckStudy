import base64
import json
import re
import uuid
import pyaes
import hashlib
from pyDes import des, CBC, PAD_PKCS5
from login.Utils import Utils
from login.wiseLoginService import wiseLoginService
from Crypto.Cipher import AES

class AutoSign:
    # 初始化签到类
    def __init__(self, wiseLoginService: wiseLoginService, userInfo):
        self.session = wiseLoginService.session
        self.host = wiseLoginService.campus_host
        self.userInfo = userInfo
        self.taskInfo = None
        self.task = None
        self.form = {}
        self.fileName = None

    # 获取未签到的任务
    def getUnSignTask(self):
        headers = self.session.headers
        headers['Content-Type'] = 'application/json'
        # 第一次请求接口获取cookies（MOD_AUTH_CAS）
        url = f'{self.host}wec-counselor-sign-apps/stu/sign/getStuSignInfosInOneDay'
        self.session.post(url,
                          headers=headers,
                          data=json.dumps({}),
                          verify=False)
        # 第二次请求接口，真正的拿到具体任务
        res = self.session.post(url,
                                headers=headers,
                                data=json.dumps({}),
                                verify=False).json()
        if len(res['datas']['unSignedTasks']) < 1:
            if len(res['datas']['leaveTasks']) < 1:
                raise Exception('当前暂时没有未签到的任务哦！')
            latestTask = res['datas']['leaveTasks'][0]
        else:
            latestTask = res['datas']['unSignedTasks'][0]
        self.taskInfo = {
            'signInstanceWid': latestTask['signInstanceWid'],
            'signWid': latestTask['signWid']
        }

    # 获取具体的签到任务详情
    def getDetailTask(self):
        url = f'{self.host}wec-counselor-sign-apps/stu/sign/detailSignInstance'
        headers = self.session.headers
        headers['Content-Type'] = 'application/json'
        res = self.session.post(url,
                                headers=headers,
                                data=json.dumps(self.taskInfo),
                                verify=False).json()
        self.task = res['datas']

    # 填充表单
    def fillForm(self):
        # 判断签到是否需要照片
        if self.task['isPhoto'] == 1:
            Utils.uploadPicture(self, 'sign', self.userInfo['photo'])
            self.form['signPhotoUrl'] = Utils.getPictureUrl(self, 'sign')
        else:
            self.form['signPhotoUrl'] = ''
        self.form['isNeedExtra'] = self.task['isNeedExtra']
        if self.task['isNeedExtra'] == 1:
            extraFields = self.task['extraField']
            userItems = self.userInfo['forms']
            extraFieldItemValues = []
            for i in range(len(extraFields)):
                userItem = userItems[i]['form']
                extraField = extraFields[i]
                if self.userInfo['checkTitle'] == 1:
                    if userItem['title'] != extraField['title']:
                        raise Exception(
                            f'\r\n第{i + 1}个配置出错了\r\n您的标题为：[{userItem["title"]}]\r\n系统的标题为：[{extraField["title"]}]'
                        )
                extraFieldItems = extraField['extraFieldItems']
                flag = False
                data = 'NULL'
                for extraFieldItem in extraFieldItems:
                    if extraFieldItem['isSelected']:
                        data = extraFieldItem['content']
                    # print(extraFieldItem)
                    if extraFieldItem['content'] == userItem['value']:
                        if extraFieldItem['isOtherItems'] == 1:
                            if 'extra' in userItem:
                                flag = True
                                extraFieldItemValue = {
                                    'extraFieldItemValue': userItem['extra'],
                                    'extraFieldItemWid': extraFieldItem['wid']
                                }
                                extraFieldItemValues.append(
                                    extraFieldItemValue)
                            else:
                                raise Exception(
                                    f'\r\n第{ i + 1 }个配置出错了\r\n表单未找到你设置的值：[{userItem["value"]}],\r\n该选项需要extra字段'
                                )
                        else:
                            flag = True
                            extraFieldItemValue = {
                                'extraFieldItemValue': userItem['value'],
                                'extraFieldItemWid': extraFieldItem['wid']
                            }
                            extraFieldItemValues.append(extraFieldItemValue)
                if not flag:
                    raise Exception(
                        f'\r\n第{ i + 1 }个配置出错了\r\n表单未找到你设置的值：[{userItem["value"]}],\r\n你上次系统选的值为：[{data}]'
                    )
            self.form['extraFieldItems'] = extraFieldItemValues
        self.form['signInstanceWid'] = self.task['signInstanceWid']
        self.form['longitude'] = self.userInfo['lon']
        self.form['latitude'] = self.userInfo['lat']
        self.form['isMalposition'] = self.task['isMalposition']
        self.form['abnormalReason'] = self.userInfo[
            'abnormalReason'] if 'abnormalReason' in self.userInfo else ''
        self.form['position'] = self.userInfo['address']
        self.form['uaIsCpadaily'] = True
        self.form['signVersion'] = '1.0.0'

    # DES加密
    def DESEncrypt(self, s, key='b3L26XNL'):
        key = key
        iv = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        k = des(key, CBC, iv, pad=None, padmode=PAD_PKCS5)
        encrypt_str = k.encrypt(s)
        return base64.b64encode(encrypt_str).decode()

    #AES加密
    def AESEncrypt(self,data,key='ytUQ7l2ZZu8mLvJZ'):
        data = data + (16 - len(data.encode()) % 16) * chr(16 - len(data.encode()) % 16)
        iv=b'\x01\x02\x03\x04\x05\x06\x07\x08\t\x01\x02\x03\x04\x05\x06\x07'
        cipher = AES.new(key.encode("utf-8"), AES.MODE_CBC, iv=iv)
        ciphertext = cipher.encrypt(data.encode("utf-8"))
        return base64.b64encode(ciphertext).decode()

    def Sign_Encrypt(self,raw_sign_code_str):
        m = hashlib.md5()
        m.update(raw_sign_code_str.encode("utf8"))
        sign = m.hexdigest()
        return sign

    # def AESEncrypt(self, text):
    #     key = b'ytUQ7l2ZZu8mLvJZ'
    #     mode = AES.MODE_CBC
    #     iv = b"\x01\x02\x03\x04\x05\x06\x07\x08\t\x01\x02\x03\x04\x05\x06\x07"
    #     cryptor = AES.new(key, mode, iv)
    #     if len(text.encode('utf-8')) % 16:
    #         add = 16 - (len(text.encode('utf-8')) % 16)
    #     else:
    #         add = 0
    #     text = text + ('\0' * add)
    #     en = cryptor.encrypt(text.encode("utf-8"))
    #     return base64.b64encode(en).decode()

    # 提交签到信息
    def submitForm(self):
        extension = {
            "lon": self.userInfo['lon'],
            "model": "OPPO R11 Plus",
            "appVersion": "9.0.12",
            "systemVersion": "4.4.4",
            "userId": self.userInfo['username'],
            "systemName": "android",
            "lat": self.userInfo['lat'],
            "deviceId": str(uuid.uuid1())
        }
        headers = {
            'User-Agent': self.session.headers['User-Agent'],
            'CpdailyStandAlone': '0',
            'extension': '1',
            'Cpdaily-Extension': self.DESEncrypt(json.dumps(extension)),
            'Content-Type': 'application/json; charset=utf-8',
            'Accept-Encoding': 'gzip',
            'Host': re.findall('//(.*?)/', self.host)[0],
            'Connection': 'Keep-Alive'
        }
        dada = {
            "appVersion": "9.0.12",
            "sign": self.Sign_Encrypt(json.dumps(self.form)),
            "bodyString": self.AESEncrypt(json.dumps(self.form)),
            "deviceId": str(uuid.uuid1()),
            "lat": self.userInfo['lat'],
            "lon": self.userInfo['lon'],
            "model": "OPPO R11 Plus",
            "systemName": "android",
            "systemVersion": "11",
            "userId": self.userInfo['username'],
            "calVersion": 'firstv',
            "version": "first_v2",
        }
        # print(json.dumps(self.form))
        res = self.session.post(
            f'{self.host}wec-counselor-sign-apps/stu/sign/submitSign',
            headers=headers,
            data=json.dumps(dada),
            verify=False).json()
        return res['message']