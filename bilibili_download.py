import os.path
import parsel
import subprocess
from util import *
import random
import pickle
import copy
from concurrent.futures import ThreadPoolExecutor

"""获取哔哩哔哩网站视频, 更新时间2022-05-22"""


class BilibiliLogin(object):
    """
    登陆组件, 采用读取哔哩哔哩登陆二维码的方式登陆
    """

    def __init__(self):
        self.cookies_dir_path = "./cookies/"
        self.session = requests.session()
        self.session.headers = create_headers()

    def _get_login_page(self):
        """访问登陆页面，获取二维码信息"""
        passport_url = 'https://passport.bilibili.com/login'
        qrcode_url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/generate'
        params = {
            'source': 'main-web',
            'go_url': 'https://member.bilibili.com/'
        }
        self.session.get(passport_url, headers=self.session.headers)
        self.session.headers['referer'] = passport_url
        resp = self.session.get(qrcode_url, headers=self.session.headers, params=params)
        return resp

    def _validate_qr_code(self, qrcode_key):
        """校验二维码的认证情况"""
        validate_url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/poll'
        params = {
            'qrcode_key': qrcode_key
        }
        resp = self.session.get(validate_url, headers=self.session.headers, params=params)
        return parse_json(resp.text).get("data")

    def login_by_qrcode(self):
        cookie_file_name = 'bilibilidown'
        logger.info("正在访问哔哩哔哩登陆页面")
        cookie_path = os.path.join(self.cookies_dir_path, f'{cookie_file_name}.cookies')
        if os.path.exists(cookie_path):
            is_delete = input("检测到存在本地cookies, 是否重置? 输入[y/n]")
            if is_delete == 'y':
                os.remove(cookie_path)
            elif is_delete == 'n':
                self.load_cookies_from_local(cookie_file_name)
                logger.info("已读取本地cookies, 成功登入系统")
                return
            else:
                logger.info(f"输入错误, 请勿输入 {is_delete}")
                raise Exception("输入错误")

        """进行登陆二维码验证并反馈结果"""
        resp = self._get_login_page()
        qrcode_data = parse_json(resp.text).get("data")

        image_file = './qrcode.png'
        qrcode_save(qrcode_data.get("url"), image_file)
        logger.info("已获取登陆验证二维码, 请打开手机App扫码进行登陆")
        open_image(image_file)

        # 根据测试, 哔哩哔哩的二维验证码的失效时长为3分钟
        retry_times = 85
        for _ in range(retry_times):
            ticket = self._validate_qr_code(qrcode_data.get("qrcode_key"))
            if ticket.get("timestamp") != 0:
                logger.info("已扫码, 成功登入系统")
                break
            else:
                logger.info(ticket.get("message"))
                time.sleep(2)
        else:
            raise Exception("二维码已超时, 需重新获取验证信息")

        self.save_cookies_to_local(cookie_file_name)

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

    def load_cookies_from_local(self, cookie_file_name):
        """
        从本地加载Cookie
        :return:
        """
        cookies_file = '{}{}.cookies'.format(self.cookies_dir_path, cookie_file_name)
        if not os.path.exists(self.cookies_dir_path):
            return False
        with open(cookies_file, 'rb') as f:
            local_cookies = pickle.load(f)
        self.set_cookies(local_cookies)

    def save_cookies_to_local(self, cookie_file_name):
        """
        保存Cookie到本地
        :param cookie_file_name: 存放Cookie的文件名称
        :return:
        """
        cookies_file = '{}{}.cookies'.format(self.cookies_dir_path, cookie_file_name)
        directory = os.path.dirname(cookies_file)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(cookies_file, 'wb') as f:
            pickle.dump(self.get_cookies(), f)


class GetBilibiliVideo(object):
    def __init__(self, directory):
        logger.info("哔哩哔哩自动化下载程序已启动")
        gl = BilibiliLogin()
        logger.info("登陆组件已加载, 准备执行登入操作")
        gl.login_by_qrcode()
        self.session = gl.session
        self.user_agent = self.session.headers.get("User-Agent")
        self.uid = self._get_uid()
        self.bv_id = []

        # 下载文件存储与校对地址
        examine_dir(directory)
        self.down_path = directory

    def _get_uid(self):
        """获取到对应账号的uid用以访问个人空间"""
        space_url = 'https://space.bilibili.com/'
        resp = self.session.get(space_url, headers=self.session.headers)
        uid = isnull(re.findall(r"/(\d+)$", resp.url), False)
        if not uid:
            raise Exception("获取uid失败!")
        return uid

    def main(self):
        """作为用户交互界面调用组件"""
        # 1. 访问收藏夹主页
        logger.info("开始访问个人空间主页面")
        list_fav = self._get_list_favorites()
        content = []
        for item in list_fav:
            content.append(f"收藏夹名: {item.get('title')} 视频数: {item.get('media_count')}")
        logger.info("请输入收藏夹对象id")
        fn = get_digit_input(content, mode='single')
        # 获取对应收藏夹的id号
        logger.info(f"已接收指令, 正在访问收藏夹: {list_fav[fn - 1].get('title')}")
        fid = list_fav[fn - 1].get("id")
        page_amount = math.ceil(list_fav[fn - 1].get('media_count') / 20)
        time.sleep(0.1)
        while True:
            print(f"当前收藏夹视频页数总共为 {page_amount} 页, 请选择访问页数:\n[输入0] 全选+全部下载\n[输入1至{page_amount}] 选择第N页")
            pn = int(input("请输入:"))
            if pn == 0:
                logger.info("已选择 [全选] 指令, 正在添加全部对象至指令台...")
                for _ in range(1, page_amount + 1):
                    df = self._collect_video_info(fid, _)
                    self.bv_id.extend(list(df['bv_id']))
                    time.sleep(1)
                break
            else:
                df = self._collect_video_info(fid, pn)
                content = []
                for i in range(len(df)):
                    content.append(f"视频名称: {df.loc[i + 1, 'title']}")
                media_chosen = get_digit_input(content, mode='list')
                self.bv_id.extend(list(df['bv_id'][df.index.isin(media_chosen)]))
                break

        # 进行去重
        bv_id = self.bv_id
        self.bv_id = list(set(bv_id))
        self.bv_id.sort(key=bv_id.index)

        # 开始下载
        print(f'————————————开始下载————————————')
        for _ in self.bv_id:
            bv_url = f'https://www.bilibili.com/video/{_}/'
            self.download_video(bv_url)

        logger.info("下载任务已全部完成")

    def _collect_video_info(self, fid, pn):
        data = self._retrieve_favorites(fid, pn=pn)
        # 使用临时数据表df来存储收藏中的视频信息
        df = pd.DataFrame(data)
        for i in range(len(df)):
            df.loc[i, 'cnt_info'] = df.loc[i, 'cnt_info'].get('bv_id')
        # 序列加1以方便匹配用户的输入
        df.index = df.index + 1
        return df

    def _get_list_favorites(self):
        """访问个人收藏夹页面，获取收藏夹目录"""
        # 访问个人收藏的链接
        fav_url = 'https://space.bilibili.com/{}/favlist'.format(self.uid)
        self.session.get(fav_url, headers=self.session.headers)
        # 获取收藏夹目录
        fav_list = 'https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid={}&jsonp=jsonp'.format(self.uid)
        resp = self.session.get(fav_list, headers=self.session.headers)
        data = parse_json(resp.text).get("data").get("list")
        # 返回结果数据, 为list对象
        return data

    def _retrieve_favorites(self, fid, pn, ps=20):
        """
        检索收藏夹: 从登陆账号的收藏中进行检索, 选定要下载的对象
        :param fid: 收藏夹序列号
        :param pn: 页面编号, 从1开始
        :param ps: 每页展示视频数, 默认按20
        """
        # 获取收藏夹目录
        fav_list = 'https://api.bilibili.com/x/v3/fav/resource/list'
        params = {
            'media_id': fid,
            'pn': pn,
            'ps': ps,
            'keyword': '',
            'order': 'mtime',
            'type': 0,
            'tid': 0,
            'platform': 'web',
            'jsonp': 'jsonp'
        }
        resp = self.session.get(fav_list, headers=self.session.headers, params=params)
        data = parse_json(resp.text).get("data").get("medias")
        return data

    def download_video(self, url):
        try:
            video_url, audio_url, title, actual_quality, highest_quality = self.get_url(url)
        except FileNotFoundError:
            print(f'None | 视频已被删除, 执行跳过...')
            return
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

    def get_url(self, url):
        """根据给予的url访问其视频、音频所在地址"""
        self.session.headers['referer'] = url
        resp = self.session.get(url=url, headers=self.session.headers)
        xpath = parsel.Selector(resp.text)
        title = xpath.xpath('//*[@id="viewbox_report"]/h1').attrib.get('title')
        author = xpath.xpath('//meta[@name="author"]').attrib.get('content')

        # 获取视频播放信息
        play_info = xpath.xpath('/html/head/script[contains(text(), "window.__playinfo")]/text()').extract_first()
        if type(play_info) == 'NoneType':
            raise FileNotFoundError()
        data = parse_json(play_info).get("data")
        video = pd.DataFrame(data.get("dash").get("video"))
        audio = pd.DataFrame(data.get("dash").get("audio"))

        # 默认可选视频质量是由高到低排序的，所以此处直接选最高的
        quality_chart = dict(zip(data.get("accept_quality"), data.get("accept_description")))

        # highest_quality: 视频可使用的最高质量, actual_quality: 当前用户能够访问的最高质量
        highest_quality = quality_chart.get(max(data.get("accept_quality")))
        actual_quality = quality_chart.get(video.loc[0, 'id'])
        video_url = video.loc[0, 'baseUrl']
        audio_url = audio.loc[0, 'baseUrl']

        if title.find(f'【{author}】') >= 0:
            pass
        else:
            title = f'【{author}】 {title}'  # 文件名命名格式, 不含后缀

        return video_url, audio_url, title, actual_quality, highest_quality

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


"""
def download(self, url):
    '''添加线程调用, 提高运行速度'''
    url_param = self.get_url(url)
    t = threading.Thread(target=self._download, args=(*list(url_param.values()),))
    t.start()
    t.join()

def _download(self, video_url, audio_url, title):
    video = requests.get(video_url, headers=self.header).content
    audio = requests.get(audio_url, headers=self.header).content
    title_new = title + "纯"
    with open(f'./videoMP4\\{title_new}.mp4', 'wb') as f:
        f.write(video)
    with open(f'./videoMP4\\{title_new}.mp3', 'wb') as f:
        f.write(audio)
    self._splicing(title, title_new)
"""

if __name__ == '__main__':
    gbv = GetBilibiliVideo()
    gbv.main()
