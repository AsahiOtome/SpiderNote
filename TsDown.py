import os.path
import parsel
import subprocess
from util import *
import random
import pickle
import copy
from util import *


class TsDown(object):
    def __init__(self):
        pass

    def download_video(self, url):
        video_url, audio_url, title = self.get_url(url)
        title = fix_filename(title)
        if os.path.exists(os.path.join(self.down_path, f'{title}.mp4')):
            print(f'{title} | 视频文件已存在, 执行跳过...')
            return
        print(f'{title} | 视频最高品质: {highest_quality} | 可下载最高品质: {actual_quality}')
        dl = Downloader(video_url, '视频文件', os.path.join(self.down_path, f'{title}_.mp4'), self.session)
        dl.main()
        self._splicing(self.down_path, title)
        time.sleep(2 + random.random())


