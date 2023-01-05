import os.path

import parsel
from io import BytesIO
from PIL import Image
from util import *


class MangaLogin(Login):
    def __init__(self, user, pwd):
        super().__init__()
        self.cookies_file_name = __file__.split('/')[-1].split('.')[0]
        self.user = user
        self.pwd = pwd

    def login(self):
        """
        1. 读取本地cookies 2.尝试访问用户页面 3.访问失败则重新登陆
        :return:
        """
        cookie_path = '{}{}.cookies'.format(self.cookies_dir_path, self.cookies_file_name)
        if os.path.exists(cookie_path):
            self.load_cookies_from_local()
            if self._validate_login():
                return True

        login_url = 'https://jmcomic2.onl/login'
        self.session.headers['refer'] = 'https://jmcomic2.onl/'
        data = {
            'username': self.user,
            'password': self.pwd,
            'id_remember': 'on',
            'login_remember': 'on',
            'submit_login': ''
        }
        self.session.post(login_url, data=data)
        self.save_cookies_to_local()
        return True

    def _validate_login(self):
        """
        访问用户个人页面, 状态为200则为成功, 状态为301则说明跳转至登陆页面
        :return:
        """
        user_url = 'https://jmcomic2.onl/user'
        resp = self.session.get(user_url)
        if resp.status_code == '200':
            return True
        else:
            return False


class MangaDown(object):
    def __init__(self, url, path, session):
        self.session = session
        self.title = self.parsel(url)
        self.album_id = re.findall(r"onl/album/(\d+)/", url)[0]
        self.down_url = 'https://jmcomic2.onl/album_download/' + self.album_id
        self.path = path

    def _get_info(self, url):
        resp = try_until_response_get(url, session=self.session, trys=3)
        return resp

    def parsel(self, url):
        data = parsel.Selector(self._get_info(url).text)
        title = data.xpath("//h1[@class='book-name' and @id='book-name']/text()").extract_first()
        # url_tail = data.xpath("//div[contains(@class, 'read-block')]")[0].\
        #     xpath("./a[@style='padding: 5px']").attrib.get('href')
        return title

    def main(self):
        # 创建目录
        self.path = os.path.join(self.path, self.title)
        # examine_file(self.path)
        # logger.info("开始解析资源链接")
        self._download()

    def _download(self):
        vcode_url = 'https://jmcomic2.onl/captcha/'
        self.session.get(self.down_url)
        self.session.headers['refer'] = self.down_url

        # 获取验证码
        resp = self.session.get(vcode_url)
        with open("./vcode.jpg", 'wb') as p:
            p.write(resp.content)
        verification = recognize_text("./vcode.jpg")

        data = {
            'album_id': self.album_id,
            'verification': verification
        }
        resp = self.session.post(self.down_url)
        url = resp.headers['location']
        self.session.headers['refer'] = 'https://jmcomic2.onl'

        select_list = data.xpath("//div[@class='center scramble-page']")
        for select in select_list:
            self.pic_url.append(select.xpath("./img").attrib.get("data-original"))
        # logger.info(f"准备开始多线程下载, 需下载图片总数: {len(self.pic_url)}")
        pdown = PicDownloader(self.pic_url, self.title, self.path, self.session)
        pdown.main()


class PicDownloader(object):
    """
    图片夹下载器, 标准调用方法:
    dl = PicDownloader(url, 文件名, path, session)
    dl.main()
    """

    def __init__(self, url_list, name, filepath, session: requests.session, max_num=8):
        """
        载入关键信息并初始化
        :param url_list: 待爬取的对象下载链接
        :param max_num: 设定的线程最大数目
        :param filepath: 保存的文件路径
        :param session: 用户连接信息
        """
        self.url_list = url_list
        self.name = name
        self.num = max_num
        self.path = filepath
        self.session = session
        self.getsize = 0  # 记录已下载文件的数量, 用于比较进度
        self.size = len(self.url_list)

    def down(self, url, index):
        """
        下载程序主体
        :param url: 实际访问的切片下载地址
        :param index: 下载的切片序号
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
        byte_stream = BytesIO(resp.content)
        img = Image.open(byte_stream)
        index = fix_filename(index)
        examine_file(os.path.join(self.path, f'{index}.jpg'))
        img.save(os.path.join(self.path, f'{index}.jpg'), 'JPEG')
        self.getsize += 1  # 更新getsize值, 已下载内容大小

    def main(self):
        """
        使用多线程函数进行管理
        :return:
        """
        t = threading.Thread(target=self._process, )
        t.start()
        # t.join() 用于阻塞主线程, 使主线程等待线程执行完成后才继续
        tp = ThreadPoolExecutor(max_workers=self.num)  # 加载多线程函数, 设置最大线程数
        futures = []
        for url in self.url_list:  # 依次启动多线程, 每个线程分配 size/8 的数据字节量
            index = re.findall(r'.*/(.*?)\.\w+$', url)[0]
            future = tp.submit(self.down, url, index)  # 将函数提交多线程, 并赋予参数
            futures.append(future)
        tp.shutdown(wait=True)
        # logger.info("任务完成")

    def _process(self):
        while True:
            process = self.getsize / self.size * 100  # 已完成下载进度, 转化为百分率
            time.sleep(0.5)  # 按照间隔1s来更新下载进展
            print(f'\t{self.name} | 下载进度: {process:6.2f}% | 下载进程: {self.getsize}/{self.size}', end='\r')  # 展示即时下载速度
            if process >= 100:  # 下载进度超过100%
                print(f'\t{self.name} | 下载进度: {100.00:6}% | 下载进程: {self.size}/{self.size}')
                break


if __name__ == "__main__":
    logger.info("开始执行漫画下载任务")
    logger.info("正在登陆中")
    ml = MangaLogin(user='j4205166118', pwd='kNbF57yO')
    ml.login()
    logger.info("登陆成功")

    save_path = 'D:\\SpiderNote\\Manga'
    with open("manga.txt", 'r', encoding='utf-8') as f:
        down_list = f.read().split('\n')
        down_list.remove("")
    logger.info(f"目标链接共 {len(down_list)} 个, 开始进行解析")
    for _ in down_list:
        md = MangaDown(_, save_path, ml.get_session())
        md.main()
    logger.info("全部任务完成")
