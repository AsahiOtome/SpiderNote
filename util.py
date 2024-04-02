import pickle
import sys
import json
import re
import math
import shutil
import time
import requests
import os
import logging.handlers
import pandas as pd
import datetime
import threading
import faker
from subprocess import Popen
import qrcode
from concurrent.futures import ThreadPoolExecutor, as_completed
import copy
import subprocess
import ddddocr
from PIL import Image

"""包含了所有通用性爬虫、数据分析、文件处理等功能的要你命3000功能包"""


def zipfile(target_dir, pattern=None, fmt='zip'):
    """
    使用 7z 软件对文件夹中的文件进行逐一压缩
    :param target_dir: 目标文件所在目录, 默认按照每个文件单独压缩打包
    :param pattern: 识别符, 默认为None, 即将所有文件进行打包
    :param fmt: 压缩格式设定, 默认为 .zip
    :return:
    """
    try:
        for file in os.listdir(target_dir):
            if not pattern or file.find(pattern) >= 0:
                pass
            if re.findall(r'\.[\d\w]+$', file):
                # 如果对象为文件, 非文件夹, 则进行跳过
                continue
            zip_file = f'{file}.{fmt}'
            if examine_file(os.path.join(target_dir, zip_file), delete=False):
                # 压缩包文件已存在则跳过
                continue
            cmd = f'"D:\\ProgramFiles\\7-Zip\\7z.exe" a -t{fmt}' \
                  f' \"{os.path.join(target_dir, zip_file)}\" \"{os.path.join(target_dir, file)}\"'
            p = Popen(cmd, shell=True, universal_newlines=True, encoding='utf-8', stdout=subprocess.PIPE
                      , stderr=subprocess.STDOUT)
            while True:
                """等待单个文件压缩完成后再进行下一个"""
                if p.poll() == 0:
                    break
            shutil.rmtree(os.path.join(target_dir, file))
        return True
    except Exception as e:
        return e


def recognize_text(image):
    """
    验证码识别组件
    :param image:图片对象或文件路径
    :return:
    """
    orc = ddddocr.DdddOcr(show_ad=False)
    res = orc.classification(image)
    return res


def set_logger():
    """设置简易日志输出台, 由于在脚本中运行, 结束时需要去除handler"""
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(fmt='[%(asctime)s] %(levelname)s: %(message)s', datefmt="%Y-%m-%d %T")
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(formatter)
    logger.addHandler(sh)


logger = logging.getLogger()
set_logger()


def parse_json(string: str) -> dict:
    """
    将获取到的字符串转译为json串
    :param string: 获取到的jsonQuery字符串
    :return:
    """
    begin = string.find('{')
    """end: 按自后往前查找第一个标志"""
    end = len(string) - string[::-1].find('}')
    return json.loads(string[begin:end], strict=False)


def response_status(resp):
    """检查resp的返回是否为200正常"""
    if resp.status_code != requests.codes.OK:
        print('Status: %u, Url: %s' % (resp.status_code, resp.url))
        return False
    return True


def try_until_response_get(url, headers=None, params=None, data=None, stream=False, trys=1, session=None):
    """
    设定按一定次数限制对某一个链接进行发送get尝试
    :param url: 对象链接
    :param headers: 表头
    :param params: 参数
    :param data: 参数
    :param stream: 是否保持连接
    :param trys: 尝试次数上限
    :param session: 是否沿用session
    :return:
    """
    if not isinstance(trys, int) or trys < 1:
        raise Exception("trys参数需要为大于1的整数")
    try_times = 0
    try:
        while True:
            try_times += 1
            if session:
                resp = session.get(url=url, headers=headers, params=params, data=data, stream=stream)
            else:
                resp = requests.get(url=url, headers=headers, params=params, data=data, stream=stream)
            if response_status(resp):
                return resp
            elif str(resp.status_code).startswith('5'):
                print(f"状态代码: {resp.status_code}, try_times: {try_times}, 程序仍继续运行")
            elif try_times >= trys:
                raise ConnectionError(f"网址响应获取超时")
    except Exception as e:
        raise Exception(f'{e}:\n出错对象:{url}')


def create_user_agent(computer_limit=True, chrome=False):
    """获取随机的user_agent, 默认为限制是电脑端发起的用户授权"""
    # Faker(zh_CN) 获取地区专属的伪造
    f = faker.Faker()
    if computer_limit:
        while True:
            if chrome:
                ua = f.chrome()
            else:
                ua = f.user_agent()
            if not re.findall(r'(Android|Mobile|iPhone|iPad|X11)', ua):
                break
    else:
        if chrome:
            ua = f.chrome()
        else:
            ua = f.user_agent()
    return ua


def create_headers():
    header = {
        "User-Agent": create_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;"
                  "q=0.9,image/webp,image/apng,*/*;"
                  "q=0.8,application/signed-exchange;"
                  "v=b3",
        "Connection": "keep-alive"
    }
    return header


def examine_file(path, delete=True):
    """
    检查 文件 是否存在, 默认状态下: 对象文件存在则删除; delete为False时, 存在则返回 True
    :param path: 对象路径
    :param delete: 如果对象已存在, 是否删除
    """
    # 以是否以.数字/英文结尾来判断是否为文件路径
    if re.findall(r'\.[\d\w]+$', path):
        if os.path.exists(path):
            if delete:
                os.remove(path)
            return True
        else:
            return False
    else:
        raise TypeError(f"对象不是文件类型: {path}")


def examine_dir(path, delete=False, exist_ok=True):
    """
    检查 文件夹 是否存在, 默认状态下: 文件夹不存在则新建, 存在则不执行操作
    :param path: 对象路径
    :param delete: 如果对象已存在, 是否删除, 默认为当选 True 时, 直接删除文件夹并新建
    :param exist_ok: 如果文件夹内有文件存在, 是否删除, True为继续删除, False为报错
    """
    # 对象非文件时按文件夹处理
    if re.findall(r'\.[\d\w]+$', path):
        raise TypeError(f"对象路径不是文件夹: {path}")
    elif not os.path.exists(path):
        """不存在时, 默认新建文件夹"""
        os.makedirs(path)
    elif delete:
        if exist_ok:
            shutil.rmtree(path)
        else:
            try:
                os.rmdir(path)
            except OSError:
                raise Exception("目标文件夹下存在文件, 无法删除!")
        os.makedirs(path)


def isnull(array: list, var, return_first=True):
    """
    判断是否为空, 为空则返回参数var
    :param array:对象数组
    :param var:为空时返回的参数
    :param return_first:是否返回数组首位, 为否则原样返回数组
    :return:
    """
    if return_first:
        return var if not array else array[0]
    else:
        return var if not array else array


def numeric_transfer(string: str):
    """把文本类的数据格式转化为数值"""
    if string in ['?', 'nan']:
        return string
    string = string.replace(" ", "")
    string = string.replace(",", "")
    return pd.to_numeric(string)


def date_transfer(date):
    """将日期数据转化为文本，便于保存"""
    if type(date) == pd.Timestamp or type(date) == datetime.datetime:
        """ pd._libs.tslibs.timestamps.Timestamp 可用 pd.Timestamp 直接表达"""
        return datetime.date(date.year, date.month, date.day).strftime('%Y-%m-%d')
    else:
        return date


def pre_processing(data: pd.DataFrame, numeric_keys: list, date_keys: list):
    """
    对表格格式进行预处理, 包括：将文本数字转换为数值, 将日期数据转换为文本
    :param data:
    :param numeric_keys:用于判断字段是否需要转换数值的关键词
    :param date_keys:用于判断字段是否需要转换日期文本的关键词
    :return:
    """
    for col in data.columns.tolist():
        simple = False
        for key in numeric_keys:
            if col.find(key) >= 0:
                simple = True
                if data[col].dtype == 'float' or data[col].dtype == 'int64':
                    pass
                else:
                    data[col] = data[col].apply(str)  # 避免字段中含有非str格式数值导致报错, 因为str与int混合
                    data[col] = data[col].apply(numeric_transfer)
        if simple:
            continue
        for key in date_keys:
            if col.find(key) >= 0:
                data[col] = data[col].apply(date_transfer)
        data[col] = data[col].apply(str)
    return data


def qrcode_save(url, image_file='qrcode.png'):
    """简单使用qrcode工具将链接转化为二维码"""
    img = qrcode.make(url)
    with open(image_file, 'wb') as f:
        img.save(f)


def save_image(resp, image_file, chunk_size=1024):
    """保存图片, 对象必须为request.response类型"""
    with open(image_file, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            f.write(chunk)


def open_image(image_file):
    """调用控制台进行图片浏览"""
    if os.name == "nt":
        cmd = 'start ' + image_file  # for Windows
        p = Popen(cmd, shell=True, universal_newlines=True, encoding='utf-8')
    else:
        if os.uname()[0] == "Linux":
            if "deepin" in os.uname()[2]:
                os.system("deepin-image-viewer " + image_file)  # for deepin
            else:
                os.system("eog " + image_file)  # for Linux
        else:
            os.system("open " + image_file)  # for Mac


def save_excel(data: pd.DataFrame, path: str, sheet_name='Sheet1', index=True):
    """实现复杂表格存储, 可继承原数据而不覆盖"""
    writer = pd.ExcelWriter(path, engine='openpyxl', mode='a')
    data.to_excel(writer, sheet_name=sheet_name, index=index)
    sheet = writer.sheets[sheet_name]
    sheet.set_column(0, len(data.columns.tolist()), 16)
    writer.close()


def pre_simple(data: pd.DataFrame):
    """极简化的数据预处理, 除了一列都是float, int等情况外, 统一转化为str"""
    for col in data.columns.tolist():
        if data[col].dtype in ['float64', 'int64']:
            continue
        elif data[col].dtype == 'object':
            data[col] = data[col].apply(str)
    return data


def get_video_mp4(url, save_path=None, header=None, param=None, data=None):
    if save_path:
        examine_dir(save_path)
    else:
        examine_dir('./videoMP4')
        save_path = 'videoMP4\\' + 'video' + ''.join(str(time.time()).split('.', 2)) + '.mp4'

    resp = requests.get(url=url, stream=True)
    if resp.status_code != requests.codes.ok:
        return '下载出错'

    length = float(resp.headers['content-length'])

    def write_video():
        count = 0
        with open(save_path, 'wb') as fp:
            for chunk in resp.iter_content(chunk_size=512):
                if chunk:
                    fp.write(chunk)
                    count += len(chunk)

    # 计算下载进度，用已下载的文件大小/文件总的大小
    def progress_bar():
        time.sleep(0.3)
        start = time.perf_counter()
        while True:
            down_size = os.path.getsize(save_path)
            p = math.ceil((down_size / length) * 100)  # 向上进行取整，确保下载完成是的进度为100%
            dur = time.perf_counter() - start

            print("\r", end="")
            print("下载进度: {}%: ".format(p), "▋" * (p // 2), "{:.2f}s".format(dur), end="")
            sys.stdout.flush()
            time.sleep(0.05)
            if p == 100:
                break
        print()

    t1 = threading.Thread(target=write_video)
    t1.start()
    progress_bar()
    t1.join()
    resp.close()
    path_log = os.path.join(os.getcwd(), save_path)
    print('视频合并完成！视频路径：{0}'.format(path_log))


def get_digit_input(obj_list, esp='esp', mode='single'):
    """
    对input组件做一定的整合, 默认以数字输入, 输入esp退出
    :param obj_list: 提供一个字符串列表, 自动进行索引组合
    :param esp: 退出键, 防止程序卡死, 会报错
    :param mode: single: 单数字输入, 返回为int数值, list: 多数字输入, 默认按','划分, 返回为列表对象
    """
    if esp.isdigit():
        raise Exception("参数esp不可为数字!")
    if not obj_list:
        raise Exception("列表对象为空!")
    else:
        content = "输入[]内数字以选择, 列表需用\',\'分割\n"
        for i in range(len(obj_list)):
            _ = str(i + 1).rjust(2, "0")
            content += f'[{_}] {obj_list[i]}\n'
    if mode == 'list':
        content += f'[0] 全选/全部下载\n'
    content += f'[{esp}] 退出程序\n请输入: '
    while True:
        reply = input(content)
        reply = reply.strip()
        if reply == esp:
            raise Exception("退出输入子程序")
        if reply.isdigit():
            if mode == 'single':
                if int(reply) not in range(1, len(obj_list) + 1):
                    _ = input("Error: 输入数字不在可选范围内, 需要重新输入!\n按Enter以继续:")
                else:
                    return int(reply)
            elif mode == 'list':
                if int(reply) not in range(0, len(obj_list) + 1):
                    _ = input("Error: 输入数字不在可选范围内, 需要重新输入!\n按Enter以继续:")
                elif int(reply) == 0:
                    return list(range(1, len(obj_list) + 1))
                else:
                    return [int(reply)]
        elif reply.replace(" ", "").replace(",", "").isdigit():
            temp_reply = list(map(int, reply.split(",")))
            mark = False
            for item in temp_reply:
                if item not in range(len(obj_list) + 1):
                    _ = input("Error: 输入数字不在可选范围内, 请重新输入!\n按Enter以继续:")
                    mark = True
                    continue
            if mark:
                continue
            return temp_reply
        else:
            _ = input("Error: 输入参数错误, 请输入数字!\n按Enter以继续:")


def fix_filename(filename):
    """对文件名中的系统字符进行删除, 以避免保存时报错"""
    regex = r'[\?\.\:\>\<\\\/\|\*]'
    filename = re.sub(regex, "", filename)
    return filename


def ts_concat(file_in, file_out):
    """
    用于把ts文件切片合并为单一文件, 注意: file_in与file_out不可在同一目录下, 否则会删除file_out
    :param file_in: 输入文件路径
    :param file_out: 输出对象路径, 含文件名
    :return:
    """
    if not examine_file(file_in, delete=False):
        raise Exception("对象文件不存在")
    else:
        cmd = f"ffmpeg.exe -f concat -safe 0 -i {file_in} -c copy {file_out}"
        examine_file(file_out)
        p = Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        p.communicate()
        while True:
            time.sleep(12)
            if p.returncode == 0:
                print("\t合并处理: 正在删除临时文件……", end='\r')
                shutil.rmtree(os.path.dirname(file_in))
                break
        print("\t合并处理: 已完成")


class Downloader(object):
    """
    切分型多线程下载器, 适用于单个长视频, 标准调用方法:
    dl = Downloader(url, '文件名或提示信息', path, session)
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
        self.num_threads = max_num
        self.path = filepath
        self.session = session
        self.getsize = 0  # 记录已下载文件的大小, 用于比较进度
        r = self.session.head(self.url, allow_redirects=True)  # 预先载入一次对象链接, 获取Header信息
        if r.status_code == 404:
            r = self.session.get(self.url, allow_redirects=True)
        self.size = int(r.headers['Content-Length'])  # 获取对象总字节大小信息
        self.lock = threading.Lock()  # 用于同步
        self.errors = []  # 用于存储下载过程中的错误
        self.prev_size = 0  # 记录上次检查时已下载完成的大小
        self.prev_time = time.time()  # 上次检查时的时间戳
        self.logs = [f"{time.time()} 总size为 {self.size}"]  # 用于记录多线程下运行情况

    def down(self, start, end, chunk_size=10240):
        """
        下载程序主体
        :param start: 下载的起点(从何处截断开始)
        :param end: 下载的终点(何处截断停止)
        :param chunk_size: 分块大小(按大小进行对象数据的切割, 依次操作, 以防止内存占用过大)
        :return:
        """
        headers = copy.deepcopy(self.session.headers)
        headers['range'] = f'bytes={start}-{end}'
        trys = 0
        try:
            # 设置timeout，例如10秒，可以根据实际情况调整
            with self.session.get(self.url, headers=headers, stream=True, timeout=10) as resp:
                with open(self.path, "rb+") as f:
                    f.seek(start)
                    for chunk in resp.iter_content(chunk_size=chunk_size):
                        with self.lock:
                            f.write(chunk)
                            self.getsize += len(chunk)  # 根据实际读取到的块大小更新getsize值
            self.logs.append(f'{time.time()} 线程start为{start},end为 {end}部分已完成, getsize={self.getsize}')
        except Exception as e:
            with self.lock:
                self.errors.append(e)  # 记录错误

    def main(self):
        """
        使用多线程函数进行管理
        :return:
        """
        with open(self.path, 'wb') as f:  # 加载保存对象文件
            f.truncate(self.size)  # .truncate()设立截断, 此处是用总文件大小预先用空格把文件填充, 方便后续选定不同的位置进行写入
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            futures = []
            start = 0   # 下载数据的起始点
            for i in range(self.num_threads):
                end = int((i + 1) * self.size / self.num_threads) if i < self.num_threads else self.size  # 下载数据的终点锚点
                futures.append(executor.submit(self.down, start, end))
                start = end + 1  # 下一线程从另一个起点开始

            # 实时监控下载进度
            while not all(future.done() for future in futures):
                self.print_progress()
                time.sleep(0.5)

            # 完成所有线程后再次打印
            self.print_progress()

            # 关闭主链接
            self.session.close()

            # 检查是否有错误发生
            if self.errors:
                return False
            else:
                return self.size

    def print_progress(self):
        process = self.getsize / self.size * 100  # 已完成下载进度, 转化为百分率

        current_time = time.time()
        elapsed_time = current_time - self.prev_time
        downloaded = self.getsize - self.prev_size

        if elapsed_time > 0:
            speed = downloaded / elapsed_time  # bytes per second
            if speed > 1024 * 1024:  # 如果速度大于1MB/s
                speed_str = f"{speed / (1024 * 1024):.2f} MB/s"
            elif speed > 1024:  # 如果速度大于1KB/s
                speed_str = f"{speed / 1024:.2f} KB/s"
            else:
                speed_str = f"{speed:.2f} B/s"
        else:
            speed_str = "计算中..."

        print(f'\t{self.name} | 下载进度: {process:6.2f}% | 下载速度: {speed_str}', end='\r')  # 展示即时下载速度
        if process >= 100:  # 下载进度超过100%
            self.logs.append(f'{time.time()} 输出下载进度超过100%')
            print(f'\t{self.name} | 下载进度: {100.00:6}% | speed:  00.00KB/s')

        self.prev_size = self.getsize
        self.prev_time = current_time


class Login(object):
    """
    登陆组件原型
    """

    def __init__(self):
        self.cookies_dir_path = "./cookies/"
        # 此变量需要被重写
        self.cookies_file_name = __file__.split('/')[-1].split('.')[0]
        self.session = requests.session()
        self.session.headers = create_headers()

    def _validate_login(self):
        pass

    def login(self):
        self.save_cookies_to_local()

    def get_session(self):
        """
        获取当前Session
        :return:
        """
        return self.session

    def get_cookies(self):
        """
        获取当前Cookies
        :return:
        """
        return self.get_session().cookies

    def set_cookies(self, cookies):
        self.session.cookies.update(cookies)

    def load_cookies_from_local(self):
        """
        从本地加载Cookie
        :return:
        """
        cookies_file = '{}{}.cookies'.format(self.cookies_dir_path, self.cookies_file_name)
        if not os.path.exists(cookies_file):
            return False
        with open(cookies_file, 'rb') as f:
            local_cookies = pickle.load(f)
        self.set_cookies(local_cookies)

    def save_cookies_to_local(self):
        """
        保存Cookie到本地
        :return:
        """
        cookies_file = '{}{}.cookies'.format(self.cookies_dir_path, self.cookies_file_name)
        directory = os.path.dirname(cookies_file)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(cookies_file, 'wb') as f:
            pickle.dump(self.get_cookies(), f)


if __name__ == "__main__":
    pass
