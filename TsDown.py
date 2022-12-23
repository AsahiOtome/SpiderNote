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
        video_url, audio_url, title, actual_quality, highest_quality = self.get_url(url)
        title = fix_filename(title)
        if os.path.exists(os.path.join(self.down_path, f'{title}.mp4')):
            print(f'{title} | 视频文件已存在, 执行跳过...')
            return
        print(f'{title} | 视频最高品质: {highest_quality} | 可下载最高品质: {actual_quality}')
        dl = Downloader(video_url, '视频文件', os.path.join(self.down_path, f'{title}_.mp4'), self.session)
        dl.main()
        dl = Downloader(audio_url, '音频文件', os.path.join(self.down_path, f'{title}_.mp3'), self.session)
        dl.main()
        self._splicing(self.down_path, title)
        time.sleep(2 + random.random())


    @staticmethod
    def _splicing(path, title):
        video_path = os.path.join(path, f'{title}_.mp4')
        audio_path = os.path.join(path, f'{title}_.mp3')
        file_path = os.path.join(path, f'{title}.mp4')
        cmd = f'ffmpeg -i "{video_path}" -i ' \
              f'"{audio_path}" -c copy "{file_path}"'
        examine_file(file_path)
        print("\t合并处理: 正在合并视频文件与音频文件中……", end='\r')
        p = Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        p.communicate()
        while True:
            time.sleep(0.2)
            if p.returncode == 0:
                print("\t合并处理: 正在删除临时文件……", end='\r')
                try:
                    if os.path.exists(video_path):
                        os.remove(video_path)
                    if os.path.exists(audio_path):
                        os.remove(audio_path)
                except IOError:
                    continue
                break
        print("\t合并处理: 已完成")

