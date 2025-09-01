import os.path

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
        try:
            url_share = data.xpath("//article[@class='article-content']/p/iframe")[0].attrib.get("src")
        except IndexError:
            return ConnectionError
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
        try_times = 1
        while try_times <= 3:
            logger.info("开始尝试链接网址信息")
            try_times += 1
            try:
                self.parser()
                if "未命名" not in self.title:
                    break
            except ConnectionError:
                logger.info("链接错误，尝试重新连接网址，尝试第 {} 次".format(try_times))

        if try_times > 3:
            logger.info("下载失败！")
            return False
        self.title = fix_filename(self.title)
        # 创建目录
        self.path = os.path.join(self.path, 'temp')
        try_times = 1
        while True:
            try_times += 1
            if try_times >= 4:
                raise Exception("下载流程超时次数过多，强制中止！")
            examine_dir(self.path, delete=True)
            logger.info("开始进行资源载入")
            if self._stack_downloader():
                break
        while True:
            if self.getsize >= self.size:
                self.session.close()
                time.sleep(2)
                break
        dir_path = os.path.dirname(self.path)
        logger.info("下载已完成, 开始进行视频合并")
        try:
            self.merge_ts_files(os.path.join(dir_path, self.title+'.mp4'))
        except Exception as e:
            return False
        logger.info("合并任务完成")
        examine_dir(self.path, delete=True)
        return True

    def _stack_downloader(self, timeout_event=None):
        """
        使用多线程函数进行管理
        :return:
        """
        """添加了5分钟超时控制的多线程下载函数"""
        timeout = 300
        timeout_event = threading.Event()
        timer = threading.Timer(timeout, timeout_event.set)  # 超时后触发event
        timer.start()

        try:
            self.getsize = 0  # 记录已下载文件的数量, 用于比较进度
            self.size = len(self.index_info)  # 获取对象切片数量信息

            # 启动监控线程
            t = threading.Thread(target=self._monitor, )
            t.start()
            # t.join() 用于阻塞主线程, 使主线程等待线程执行完成后才继续
            # 线程池执行下载任务
            tp = ThreadPoolExecutor(max_workers=16)  # 加载多线程函数, 设置最大线程数
            futures = []
            for index in self.index_info:  # 依次启动多线程, 每个线程分配 size/8 的数据字节量
                if timeout_event.is_set():  # 检查超时
                    raise TimeoutError("下载超时终止")

                url = self.url_head + '/' + index
                future = tp.submit(self._down, url, index)  # 将函数提交多线程, 并赋予参数
                futures.append(future)

            # 等待所有任务完成（带超时检查）
            for future in futures:
                if timeout_event.is_set():
                    raise TimeoutError("下载超时终止")
                future.result()  # 阻塞等待单个任务完成
            return True

        except TimeoutError:
            # 超时后的处理
            logger.error("[超时] 下载任务已超过10分钟，强制终止")
            return False
        finally:
            timer.cancel()  # 确保取消定时器
            if hasattr(self, 'tp'):  # 确保线程池关闭
                self.tp.shutdown(wait=False)
            return True

    def merge_ts_files(self, output_path):
        # 生成文件路径列表，并确保它们是按顺序排列的
        # 假设文件名格式为 'index<number>.ts'，并按数字排序
        file_paths = [os.path.join(self.path, ts) for ts in
                      sorted(os.listdir(self.path), key=lambda x: int(x.replace('index', '').replace('.ts', '')))]

        with open(output_path, 'wb') as output_file:  # 以二进制写入模式打开输出文件
            for file_path in file_paths:
                with open(file_path, 'rb') as input_file:  # 以二进制读取模式打开每个.ts文件
                    while True:
                        chunk = input_file.read(1024)  # 读取一小块内容
                        if not chunk:
                            break  # 如果没有内容了，结束循环
                        output_file.write(chunk)  # 将内容写入最终文件

    def _down(self, url, index, chunk_size=10240):
        """
        下载程序主体
        :param url: 实际访问的切片下载地址
        :param index: 下载的切片序号)
        :param chunk_size: 分块大小(按大小进行对象数据的切割, 依次操作, 以防止内存占用过大)
        :return:
        """
        if hasattr(self, 'timeout_event') and self.timeout_event.is_set():
            raise TimeoutError()
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
            if hasattr(self, 'timeout_event') and self.timeout_event.is_set():
                raise TimeoutError()
            time.sleep(1)  # 按照间隔1s来更新下载进展
            process = 0 if self.getsize == 0 else self.getsize / self.size * 100  # 已完成下载进度, 转化为百分率
            print(f'\t{self.title} | 下载进度: {process:6.2f}% | 下载进程: {self.getsize}/{self.size}', end='\r')  # 展示即时下载速度
            if process >= 100:  # 下载进度超过100%
                print(f'\t{self.title} | 下载进度: {100.00:6}% | 下载进程: {self.size}/{self.size}')
                break


if __name__ == "__main__":
    logger.info("开始执行TS下载任务")

    save_path = 'D:\\Spyder_Web\\Ts'    # 注：路线不可含有空格，否则ffmpeg执行命令时会报路径错误
    with open("video.txt", 'r', encoding='utf-8') as f:
        down_list = f.read().split('\n')
        while "" in down_list:
            down_list.remove("")
    logger.info(f"目标链接共 {len(down_list)} 个, 开始进行解析")
    for _ in down_list:
        md = TsDown(_, save_path)
        if md.main():
            remove_processed_url("video.txt", _)
            logger.info(f"已移除处理完成的链接: {_}")
            time.sleep(3)
        else:
            raise Exception("下载失败，请重新启动程序！")
    logger.info("全部任务完成")
