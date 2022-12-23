from bilibili_download import GetBilibiliVideo
from util import *


if __name__ == 'main':
    logger.info("启动下载系统主程序...")
    while True:
        down_xpath = input("选择需下载对象类型:\n0. 退出程序\n1. 哔哩哔哩下载\n2. .ts视频下载\n3. 漫画下载")
        if down_xpath == '1':
            gbv = GetBilibiliVideo()
            gbv.main()
        elif down_xpath == '2':
            pass
        elif down_xpath == '3':
            pass
        elif down_xpath == '0':
            break
        else:
            logger.error("输入错误!")







