
from wakeword import PicoWakeWord
from aliyun import NLS
import config
import simpleaudio as sa
import speech_recognition as sr
import time
import requests
from openai import ChatGPT

picowakeword = PicoWakeWord(
    config.PICOVOICE_API_KEY, config.PICOVOICE_MODEL_PATH)
nls = NLS(config.ALIYUN_NLS_APPKEY, config.ALIYUN_ACCESSKEY_ID,
          config.ALIYUN_ACCESSKEY_SECRET)
chatgpt = ChatGPT(config.OPENAI_KEY,config.OPENAI_MODEL,config.OPENAI_SERVER)
recognizer = sr.Recognizer()


def say(msg: str):
    '''将文本转语音并进行播放'''
    print('say:', msg)
    wav_file = nls.tts(msg)
    wave_obj = sa.WaveObject.from_wave_file(wav_file)
    play_obj = wave_obj.play()
    play_obj.wait_done()


def listen():
    '''录音，然后返回文字'''
    with sr.Microphone(sample_rate=16000) as source:
        print("listening...")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=30)
        except sr.exceptions.WaitTimeoutError:
            return ''
        audio_file = f'./data/wav/{int(time.time())}-q.wav'
        with open(audio_file, "wb") as f:
            f.write(audio.get_wav_data())
        text = nls.asr(audio_file)
        print('listen:', text)
        return text


if __name__ == '__main__':
    print('Detecting key words...')
    try:
        while True:
            if not picowakeword.detect_wake_word():
                continue
            say('我在你说')
            continue_chat = True
            no_chat_count = 0   # 没有对话计数器
            while continue_chat:
                text = listen()
                if not text:
                    no_chat_count += 1
                else:
                    no_chat_count = 0
                    answer = chatgpt.completions(text)
                    say(answer)
                    continue
                if no_chat_count == 1:
                    say('你似乎没有说话，可以再说一遍吗？')
                    continue
                elif no_chat_count == 2:
                    continue_chat = False
                    say('我还是没有听清你的问题，我先退出，有事随时呼唤我。')
                    continue
    except requests.exceptions.ConnectTimeout as e:
        say('网络连接超时，请检查网络后重新运行')
    finally:
        picowakeword.delete()
