#!/usr/bin/env python
# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import requests
import time
import uuid
import os
from urllib.parse import quote_plus, urlencode
from database import Database

database = Database()


class NLS:
    def __init__(self, appkey, access_key_id, access_key_secret):
        self.appkey = appkey
        self.popapi = PopApi(access_key_id, access_key_secret)

    def asr(self, audio_file, sample_rate: int = 16000):
        '''音频转文字'''
        print(f'Start Audio to Text: audio={audio_file}')
        params = {
            "appkey": self.appkey,
            "format": "pcm",
            "sample_rate": sample_rate,
            "enable_punctuation_prediction": True,      # 是否在后处理中添加标点
            "enable_inverse_text_normalization": True,  # 中文数字转换阿拉伯数字
            "enable_voice_detection": True              # 是否启动语音检测，若不设置环境背景音会触发误识别
        }
        params_str = '&'.join(f'{k}={v}' for k, v in params.items())
        url = f'https://nls-gateway.aliyuncs.com/stream/v1/asr?{params_str}'
        headers = {
            'Content-type': 'application/octet-stream',
            'X-NLS-Token': self._get_nls_token()
        }
        with open(audio_file, 'rb') as f:
            content = requests.post(
                url=url, data=f.read(), headers=headers).json()
            text = content.get('result')
            database.insert_audio(text, audio_file, 'asr')
            return text
        # {'task_id': 'f138c56ad4c241949dc1687966a47977', 'result': '我在你说。', 'status': 20000000, 'message': 'SUCCESS'}

    def tts(self, text, format: str = 'wav', sample_rate: int = 16000):
        '''文字转音频。如果已经有转换会优先用缓存'''
        audio_file = database.get_tts_cache(text)
        if audio_file and os.path.exists(audio_file):
            print(f'tts cache: text={text} audio_file={audio_file}')
            return audio_file
        url = 'https://nls-gateway.aliyuncs.com/stream/v1/tts'
        body = {
            "appkey": self.appkey,
            "token": self._get_nls_token(),
            "text": text,
            "format": format,
            "sample_rate": sample_rate
        }
        audio_file = f'./data/wav/{int(time.time())}-a.wav'
        database.insert_audio(text, audio_file, 'tts')
        content = requests.post(url=url, json=body).content
        with open(audio_file, 'wb') as f:
            f.write(content)
        return audio_file

    def _get_nls_token(self, path: str = '.nlstoken'):
        try:
            with open(path, 'r') as f:
                token, expire_time = f.read().strip().split(',')
                if int(expire_time) > int(time.time()):
                    return token
        except (ValueError, FileNotFoundError):
            pass
        token, expire_time = self.popapi.create_token()
        with open(path, 'w') as f:
            f.write(f'{token},{expire_time}')
        return token


class PopApi:

    def __init__(self, access_key_id, access_key_secret):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret

    def _encode_text(self, text):
        return quote_plus(text).replace('+', '%20').replace('*', '%2A').replace('%7E', '~')

    def _encode_dict(self, dic):
        return urlencode(sorted(dic.items())).replace('+', '%20').replace('*', '%2A').replace('%7E', '~')

    def _generate_signature(self, parameters, access_key_secret):
        query_string = self._encode_dict(parameters)
        string_to_sign = 'GET' + '&' + \
            self._encode_text('/') + '&' + \
            self._encode_text(query_string)

        secreted_string = hmac.new(bytes(
            access_key_secret + '&', 'utf-8'), bytes(string_to_sign, 'utf-8'), hashlib.sha1).digest()
        return self._encode_text(base64.b64encode(secreted_string).decode('utf-8')), query_string

    def create_token(self):
        parameters = {
            'AccessKeyId': self.access_key_id,
            'Action': 'CreateToken',
            'Format': 'JSON',
            'RegionId': 'cn-shanghai',
            'SignatureMethod': 'HMAC-SHA1',
            'SignatureNonce': str(uuid.uuid1()),
            'SignatureVersion': '1.0',
            'Timestamp': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            'Version': '2019-02-28'
        }

        signature, query_string = self._generate_signature(
            parameters, self.access_key_secret)
        full_url = f'http://nls-meta.cn-shanghai.aliyuncs.com/?Signature={signature}&{query_string}'
        try:
            response = requests.get(full_url)
            response.raise_for_status()
            root_obj = response.json()
            token_data = root_obj.get('Token', {})
            return token_data.get('Id'), token_data.get('ExpireTime')
        except requests.RequestException:
            print(response.text)
            return None, None

