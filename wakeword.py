import pvporcupine
from pvrecorder import PvRecorder
import pvporcupine

class PicoWakeWord:
    def __init__(self, picovoice_api_key, keyword_path):
        self.porcupine = pvporcupine.create(
            access_key=picovoice_api_key,
            keyword_paths=[keyword_path]
        )
        for i, device in enumerate(PvRecorder.get_available_devices()):
            print('Device %d: %s' % (i, device))
        self.recorder = PvRecorder(device_index=0, frame_length=self.porcupine.frame_length)

    def detect_wake_word(self):
        '''唤醒词检测，命中唤醒词后会主动释放麦克风'''
        if not self.recorder.is_recording:
            self.recorder.start()
        pcm = self.recorder.read()
        result = self.porcupine.process(pcm)
        if result >= 0:
            self.recorder.stop()
            return True
        return False
    
    def delete(self):
        self.porcupine.delete()
        self.recorder.delete()