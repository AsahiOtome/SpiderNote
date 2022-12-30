from MangaDown import MangaDown
from bilibili_download import GetBilibiliVideo
from util import *


if __name__ == '__main__':
    logger.info("启动下载系统主程序...")
    time.sleep(0.1)
    while True:
        down_xpath = input("选择需下载对象类型:\n0. 退出程序\n1. 哔哩哔哩下载\n2. .ts视频下载\n3. 漫画下载\n")
        if down_xpath == '1':
            gbv = GetBilibiliVideo()
            gbv.main()
            break
        elif down_xpath == '2':
            logger.info("开始执行TS video下载任务")
            path = 'D:\\SpiderNote\\Video'
            with open("video.txt", 'r', encoding='utf-8') as f:
                down_list = f.read().split('\n')
                down_list.remove("")
            logger.info(f"目标链接共 {len(down_list)} 个, 开始进行解析")
            for url in down_list:
                md = MangaDown(url, path)
                md.main()
            time.sleep(2)
            break
        elif down_xpath == '3':
            logger.info("开始执行漫画下载任务")
            path = 'D:\\SpiderNote\\Manga'
            with open("manga.txt", 'r', encoding='utf-8') as f:
                down_list = f.read().split('\n')
                down_list.remove("")
            logger.info(f"目标链接共 {len(down_list)} 个, 开始进行解析")
            for url in down_list:
                md = MangaDown(url, path)
                md.main()
            time.sleep(2)
            logger.info("已完成全部下载任务, 开始压缩文件")
            zipfile(path, "zip")
            break
        elif down_xpath == '0':
            break
        else:
            logger.error("输入错误!")







