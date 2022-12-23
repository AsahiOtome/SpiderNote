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
from concurrent.futures import ThreadPoolExecutor
import copy

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
            zip_file = f'{file}.{fmt}'
            cmd = f'"D:\\ProgramFiles\\7-Zip\\7z.exe" a -t{fmt}' \
                  f' \"{os.path.join(target_dir, zip_file)}\" \"{os.path.join(target_dir, file)}\"'
            p = Popen(cmd, shell=True, universal_newlines=True, encoding='utf-8')
            while True:
                """等待单个文件压缩完成后再进行下一个"""
                if p.poll() == 0:
                    break
        return True
    except Exception as e:
        return e


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
    return json.loads(string[begin:end])


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
            if session is not None:
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
        content += f'[0] 全选\n'
    content += f'[{esp}] 退出程序'
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


class Downloader(object):
    """多线程下载器"""

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
        self.getsize = 0  # 记录已下载文件的大小, 用于比较进度
        r = self.session.head(self.url, allow_redirects=True)  # 预先载入一次对象链接, 获取Header信息
        self.size = int(r.headers['Content-Length'])  # 获取对象总字节大小信息

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
        while True:
            resp = self.session.get(self.url, headers=headers, stream=True)
            if str(resp.status_code).startswith('2'):
                break
            else:
                trys += 1
                resp.close()
                if trys >= 3:
                    raise Exception(f"访问下载链接超时! | range: {headers['range']} | status: {resp.status_code}")
                time.sleep(2)
        with open(self.path, "rb+") as f:
            f.seek(start)
            for chunk in resp.iter_content(chunk_size):
                f.write(chunk)
                self.getsize += chunk_size  # 更新getsize值, 已下载内容大小
        resp.close()

    def main(self):
        """
        使用多线程函数进行管理
        :return:
        """
        with open(self.path, 'wb') as f:  # 加载保存对象文件
            f.truncate(self.size)  # .truncate()设立截断, 此处是用总文件大小预先用空格把文件填充, 方便后续选定不同的位置进行写入
        tp = ThreadPoolExecutor(max_workers=self.num)  # 加载多线程函数, 设置最大线程数
        futures = []
        start = 0  # 下载数据的起点锚点
        for i in range(self.num):  # 依次启动多线程, 每个线程分配 size/8 的数据字节量
            end = int((i + 1) / self.num * self.size)  # 下载数据的终点锚点
            future = tp.submit(self.down, start, end)  # 将函数提交多线程, 并赋予参数
            futures.append(future)
            start = end + 1  # 下一线程从另一个起点开始
        while True:
            process = self.getsize / self.size * 100  # 已完成下载进度, 转化为百分率
            last = self.getsize
            time.sleep(1)  # 按照间隔1s来更新下载进展
            curr = self.getsize
            down = (curr - last) / 1024  # 两次时间间隔的相差字节数/1024 转化为KB单位, 用以描述下载速度
            if down > 1024:
                speed = f'{down / 1024:6.2f}MB/s'  # 大于1024则再转化为MB单位
            else:
                speed = f'{down:6.2f}KB/s'
            print(f'\t{self.name} | 下载进度: {process:6.2f}% | 下载速度: {speed}', end='\r')  # 展示即时下载速度
            if process >= 100:  # 下载进度超过100%
                print(f'\t{self.name} | 下载进度: {100.00:6}% | speed:  00.00KB/s')
                break


if __name__ == "__main__":
    pass
