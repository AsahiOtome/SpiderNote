import os.path
import time

import parsel
from util import *
from Crypto.Cipher import AES
from requests.adapters import HTTPAdapter


class TsDown(object):
    def __init__(self, url, path):
        self.url = url
        self.path = path
        self.title = "未命名"
        self.url_head = ""
        self.index_info = []
        self.cryptor = AES.new('CFebG10dfcF1E23f'.encode('utf-8'), AES.MODE_CBC, 'CFebG10dfcF1E23f'.encode('utf-8'))
        self.session = requests.session()
        adapter = HTTPAdapter(pool_connections=1000, pool_maxsize=1000, max_retries=3)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.session.headers = create_headers()
        self.getsize = 0  # 记录已下载文件的数量, 用于比较进度
        self.size = 0  # 获取对象切片数量信息

    def _get_info(self, url):
        """访问主页面"""
        resp = self.session.get(url)
        return resp.text

    def parser(self):
        """解析网址, 获取基本信息与下载访问地址"""
        data = parsel.Selector(self._get_info(self.url))
        if not data.xpath("//article[@class='article-content']/p/iframe"):
            data = parsel.Selector(self._get_info(self.url))
        # 获取share网址, 访问获得token
        url_share = data.xpath("//article[@class='article-content']/p/iframe")[0].attrib.get("src")
        self.title = data.xpath("./head/title/text()").extract_first()
        self.title = fix_filename(self.title)
        self.session.headers['refer'] = 'https://madou.club/'
        data = self._get_info(url_share)
        m3u8 = re.findall(r'var m3u8 = [\'\"](.*?)[\'\"]', data)[0]
        token = re.findall(r'var token = [\'\"](.*?)[\'\"]', data)[0]

        # 访问m3u8网址, 获取index序号信息| 视频被加密, 需读取key信息进行解密
        m3u8_url = 'https://dash.madou.club' + m3u8
        params = {
            'token': token
        }
        self.session.headers['refer'] = 'https://dash.madou.club/share/6132de4e99eca8077667be7f'
        resp = self.session.get(m3u8_url, params=params)

        url_key = re.findall(r'URI=\"(.*?)\"', resp.text)[0]
        key = self.session.get(url_key).text
        self.cryptor = AES.new(key.encode('utf-8'), AES.MODE_CBC, key.encode('utf-8'))
        self.url_head = url_share.replace("share", 'videos')
        self.index_info = re.findall(r"\n(index.*?\.ts)\n", resp.text)

    def main(self):
        logger.info("开始解析对象属性")
        self.parser()
        self.title = fix_filename(self.title)
        # 创建目录
        self.path = os.path.join(self.path, 'temp')
        examine_dir(self.path, delete=True)
        logger.info("开始解析资源链接")
        self._stack_downloader()
        while True:
            if self.getsize >= self.size:
                time.sleep(2)
                break
        dir_path = os.path.dirname(self.path)
        logger.info("下载已完成, 开始进行视频合并")
        ts_concat(os.path.join(self.path, 'temp.txt'),
                  os.path.join(dir_path, 'temp_output.mp4'))
        os.rename(os.path.join(os.path.dirname(self.path), 'temp_output.mp4'),
                  os.path.join(dir_path, self.title+'.mp4'))

    def _stack_downloader(self):
        self.getsize = 0  # 记录已下载文件的数量, 用于比较进度
        self.size = len(self.index_info)  # 获取对象切片数量信息
        """
        使用多线程函数进行管理
        :return:
        """
        temp_content = ''
        for _ in range(self.size):
            temp_content += 'file ' + os.path.join(self.path, f'index{_}.ts').replace('\\', '\\\\') + '\n'
        with open(os.path.join(self.path, 'temp.txt'), 'w') as f1:
            f1.write(temp_content)
        t = threading.Thread(target=self._monitor, )
        t.start()
        # t.join() 用于阻塞主线程, 使主线程等待线程执行完成后才继续
        tp = ThreadPoolExecutor(max_workers=16)  # 加载多线程函数, 设置最大线程数
        futures = []
        for index in self.index_info:  # 依次启动多线程, 每个线程分配 size/8 的数据字节量
            url = self.url_head + '/' + index
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
        with open(os.path.join(self.path, index), "wb") as f2:
            f2.write(self.cryptor.decrypt(resp.content))
        self.getsize += 1  # 更新getsize值, 已下载内容大小

    def _monitor(self):
        while True:
            time.sleep(1)  # 按照间隔1s来更新下载进展
            process = self.getsize / self.size * 100  # 已完成下载进度, 转化为百分率
            print(f'\t{self.title} | 下载进度: {process:6.2f}% | 下载进程: {self.getsize}/{self.size}', end='\r')  # 展示即时下载速度
            if process >= 100:  # 下载进度超过100%
                print(f'\t{self.title} | 下载进度: {100.00:6}% | 下载进程: {self.size}/{self.size}')
                break


if __name__ == "__main__":
    logger.info("开始执行TS下载任务")

    save_path = 'D:\\SpiderNote\\Ts'
    with open("video.txt", 'r', encoding='utf-8') as f:
        down_list = f.read().split('\n')
        if "" in down_list:
            down_list.remove("")
    logger.info(f"目标链接共 {len(down_list)} 个, 开始进行解析")
    for _ in down_list:
        md = TsDown(_, save_path)
        md.main()
    logger.info("全部任务完成")
