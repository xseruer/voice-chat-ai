import requests
import config
import time
from database import Database
import json

database = Database()


class ChatGPT:

    def __init__(self, api_key: str, model: str = 'gpt-3.5-turbo', server: str = 'https://api.openai.com') -> None:
        self.api_key = api_key
        self.server = server
        self.model = model
        self.chatfun = ChatFunction()
        self._reset_chat()

    def _reset_chat(self):
        self.session = str(int(time.time()))
        self.total_tokens = 0
        system_content = f"你是无所不知的智能助理，你的名字叫做{config.ASSISTANT_NAME}，我是一个不到8岁的小朋友，所以你需要以我这个年龄段能理解的方式回答我的各种提问。"
        self.history = []
        self._record_message({"role": "system", "content": system_content})

    def completions(self, prompt: str) -> str:
        print('gpt-q:', prompt)
        self._check_session()
        if prompt:
            self._record_message({"role": "user", "content": prompt})
        data = {
            "model": self.model,
            "messages": self.history,
            "temperature": 0.7,
            "functions": self.chatfun.get_all_function(),
            "function_call": "auto"
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        response = requests.post(
            url=f'{self.server}/v1/chat/completions', headers=headers, json=data).json()
        choice = response.get('choices')[0]
        message = choice['message']
        self._record_message(message)
        if choice['finish_reason'] == 'function_call':
            # 函数调用
            function_call = message.get('function_call')
            func_name = function_call['name']
            arguments = function_call.get("arguments")
            function_response = self.chatfun.invoke_method(func_name, arguments)
            self._record_message({"role": "function", "name":func_name, "content": function_response})
            if func_name == 'reset_chat_session':
                # 清空对话
                self._reset_chat()
            return self.completions(None)
        else:
            answer = message['content']
            print('gpt-a:',answer)
            usage = response.get('usage')
            self.total_tokens += usage.get('total_tokens')
            print(f'use total-tokens:{self.total_tokens} usage:{json.dumps(usage)}')
            return answer

    def _record_message(self, message):
        '''记录会话消息，支持持续对话'''
        self.history.append(message)
        self.last_time = int(time.time())
        # 记录数据到数据库
        role = message['role']
        if 'function_call' in message:
            content = json.dumps(message['function_call'])
        elif 'function' == role and 'name' in message:
            content = message.get('name')+':' + message.get('content')
        else:
            content=message['content']
        database.insert_chat(self.session, role, content)

    def _check_session(self):
        '''超过3天或者tokens数超过2048就自动重置会话'''
        if self.total_tokens >= 2048 or int(time.time()) - self.last_time > 3*60*60*24:
            self._reset_chat()


class ChatFunction:

    def __init__(self) -> None:
        '''初始化当作，主要是加在城市名称与区号的对应关系，方便查询实时天气'''
        self.citycode = {}
        with open('./data/citycode.csv', 'r', encoding='UTF-8') as f:
            lines = f.readlines() 
            for line in lines:
                city, code = line.strip().split(',')
                self.citycode[city] = code

    def get_all_function(self):
        return [
            {
                "name": "get_now_time",
                "description": "获取当前详细时间和星期几",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },{
                "name": "reset_chat_session",
                "description": "具有重置会话，清空历史聊天记录，忘记过去，重新开始的作用。",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }, {
                "name": "get_weather",
                "description": "获取指定地区的当前天气情况",
                "parameters": {
                        "type": "object",
                        "properties": {
                            "city_name": {
                                "type": "string",
                                "description": "城市或地区，例如：杭州市、北京市、余杭区。如果参数为空将默认查询当前网络所在城市的天气",
                            },
                        },
                },
            }
        ]

    def invoke_method(self, method_name, arguments):
        method = getattr(self, method_name)
        result = method(arguments)
        print('invoke_method:', method_name,
              ' args:', arguments, ' result:', result)
        return result

    def get_now_time(self, arguments):
        '''获取当前时间'''
        import datetime
        now = datetime.datetime.now()
        weekday_num = now.weekday()
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        formatted_time = now.strftime('%Y-%m-%d %H:%M')
        return f"当前时间:{formatted_time} {weekdays[weekday_num]}"
    
    def reset_chat_session(self,arguments):
        '''重置会话用，实际操作在上层完成，本方法仅用于返回提示信息'''
        return '操作成功'

    def get_weather(self, arguments: str):
        '''获取某个城市的实时天气，如果没有传城市信息，就默认查询当前IP所在城市。'''
        city_name = json.loads(arguments).get('city_name')

        def get_curent_city():
            response = requests.get(
                f"https://restapi.amap.com/v3/ip?key={config.GAODE_APIKEY}")
            return response.json()['adcode']

        def get_city_weather(city_code):
            url = "https://restapi.amap.com/v3/weather/weatherInfo?"
            params = {
                "key": config.GAODE_APIKEY,
                "city": city_code
            }
            response = requests.get(url=url, params=params)
            return response.json().get("lives")[0]

        if not city_name:
            tips = '默认查询当前网络所在城市的天气'
            city_code = get_curent_city()
        elif city_name not in self.citycode:
            tips = f'未匹配到{city_name}，当前结果为当前网络所在城市的天气'
            city_code = get_curent_city()
        else:
            city_code = self.citycode.get(city_name)

        weather_str = json.dumps(get_city_weather(city_code))
        if tips:
            return f'{tips}:\n```{weather_str}```'
        else:
            return weather_str
