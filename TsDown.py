import os.path
import re

import parsel
import subprocess
from util import *
import random
import pickle
import copy
from util import *


class TsDown(object):
    def __init__(self, url, path):
        self.url = url
        self.path = path
        self.title = "未命名"
        self.url_head = ""
        self.index_info = []
        self.session = requests.session()
        self.session.headers = create_headers()
        self.getsize = 0  # 记录已下载文件的数量, 用于比较进度
        self.size = 0  # 获取对象切片数量信息

    def _get_info(self):
        resp = try_until_response_get(self.url, headers=self.session.headers, trys=3)
        return resp

    def parsel(self):
        data = parsel.Selector(self._get_info().text)
        self.title = data.xpath("//h1[@class='book-name' and @id='book-name']/text()").extract_first()
        m3u8_url = data.xpath("")
        resp = try_until_response_get(m3u8_url, headers=self.session.headers, trys=3)
        self.url_head = ""
        self.index_info = re.findall(r"index(\d+).ts", resp.text)

    def main(self):
        # logger.info("开始解析对象属性")
        self.parsel()
        self.title = fix_filename(self.title)
        # 创建目录
        self.path = os.path.join(self.path, self.title)
        examine_dir(self.path)
        # logger.info("开始解析资源链接")
        self._stack_downloader()
        ts_concat(os.path.join(self.path, 'index.txt'), os.path.join(os.path.dirname(self.path), self.title+'.mp4'))

    def _stack_downloader(self):
        self.getsize = 0  # 记录已下载文件的数量, 用于比较进度
        self.size = len(self.index_info)  # 获取对象切片数量信息
        """
        使用多线程函数进行管理
        :return:
        """
        t = threading.Thread(target=self._monitor, )
        t.start()
        # t.join() 用于阻塞主线程, 使主线程等待线程执行完成后才继续
        tp = ThreadPoolExecutor(max_workers=8)  # 加载多线程函数, 设置最大线程数
        futures = []
        for index in self.index_info:  # 依次启动多线程, 每个线程分配 size/8 的数据字节量
            url = self.url_head + index + '.ts'
            future = tp.submit(self._down, url, index)  # 将函数提交多线程, 并赋予参数
            futures.append(future)

    def _down(self, url, index, chunk_size=10240):
        """
        下载程序主体
        :param url: 实际访问的切片下载地址
        :param index: 下载的切片序号)
        :param chunk_size: 分块大小(按大小进行对象数据的切割, 依次操作, 以防止内存占用过大)
        :return:
        """
        trys = 0
        while True:
            resp = self.session.get(url, headers=self.session.headers)
            if str(resp.status_code).startswith('2'):
                break
            else:
                trys += 1
                if trys >= 3:
                    raise Exception(f"访问下载链接超时! | index: {index} | status: {resp.status_code}")
                time.sleep(2)
        with open(os.path.join(self.path, 'index.txt'), 'a+') as f:
            f.write('file \"' + os.path.join(self.path, f'{index}.ts') + '\"\n')
        with open(os.path.join(self.path, f'{index}.ts'), "wb") as f:
            for chunk in resp.iter_content(chunk_size):
                f.write(chunk)
        self.getsize += 1  # 更新getsize值, 已下载内容大小

    def _monitor(self):
        while True:
            process = self.getsize / self.size * 100  # 已完成下载进度, 转化为百分率
            time.sleep(1)  # 按照间隔1s来更新下载进展
            print(f'\t{self.title} | 下载进度: {process:6.2f}% | 下载进程: {self.getsize}/{self.size}', end='\r')  # 展示即时下载速度
            if process >= 100:  # 下载进度超过100%
                print(f'\t{self.title} | 下载进度: {100.00:6}% | 下载进程: {self.size}/{self.size}')
                break
