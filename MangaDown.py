import os.path
import parsel
import subprocess
from util import *
import random
import pickle
import copy
from util import *


class MangaDown(object):
    def __init__(self, url, path):
        self.url = url
        self.path = path
        self.session = requests.session()
        self.session.headers = create_headers()

    def _get_info(self):
        resp = try_until_response_get(self.url, headers=self.session.headers, trys=3)
        return resp

    def parsel(self):
        data = parsel.Selector(self._get_info())
        data.xpath("")

    def main(self):
        logger.info("开始解析")
        self.parsel()
        logger.info("开始下载")


class PicDownloader(object):
    """
    图片夹下载器, 标准调用方法:
    dl = PicDownloader(url, 文件名, path, session)
    dl.main()
    """

    def __init__(self, url, name, filepath, session: requests.session, max_num=8):
        """
        载入关键信息并初始化
        :param url: 待爬取的对象下载链接
        :param max_num: 设定的线程最大数目
        :param filepath: 保存的文件路径
        :param session: 用户连接信息
        """
        self.url = url
        self.name = name
        self.num = max_num
        self.path = filepath
        self.session = session
        self.getsize = 0  # 记录已下载文件的数量, 用于比较进度
        r = self.session.get(self.url, headers=self.session.headers)
        self.size = r   # 读取该网页包含的图片总数

    def down(self, url, index, chunk_size=10240):
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
        with open(os.path.join(self.path, f'{self.name}_{index}.ts'), "wb") as f:
            for chunk in resp.iter_content(chunk_size):
                f.write(chunk)
                self.getsize += 1  # 更新getsize值, 已下载内容大小

    def main(self):
        """
        使用多线程函数进行管理
        :return:
        """
        tp = ThreadPoolExecutor(max_workers=self.num)  # 加载多线程函数, 设置最大线程数
        futures = []
        for _ in range(self.size):  # 依次启动多线程, 每个线程分配 size/8 的数据字节量
            url = self.url + '.ts'
            future = tp.submit(self.down, url)  # 将函数提交多线程, 并赋予参数
            futures.append(future)
        while True:
            process = self.getsize / self.size * 100  # 已完成下载进度, 转化为百分率
            time.sleep(1)  # 按照间隔1s来更新下载进展
            print(f'\t{self.name} | 下载进度: {process:6.2f}% | 下载进程: {self.getsize}/{self.size}', end='\r')  # 展示即时下载速度
            if process >= 100:  # 下载进度超过100%
                print(f'\t{self.name} | 下载进度: {100.00:6}% | 下载进程: {self.size}/{self.size}')
                break