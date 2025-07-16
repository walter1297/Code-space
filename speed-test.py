#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
simple_speed_test.py   ——   查看出口 IP + 下载速度
------------------------------------------------
用法示例：
    python simple_speed_test.py                 # 本机直连，1 线程
    python simple_speed_test.py socks5://...    # 走代理，1 线程
    python simple_speed_test.py socks5://... 4  # 走代理，4 线程
"""

import sys
import time
import argparse          # 解析命令行参数
import threading         # 多线程
import queue             # 线程安全队列
import requests          # HTTP 客户端库
from requests.exceptions import RequestException
from tqdm import tqdm    # 进度条显示
from colorama import init, Fore, Style

# ----------- 全局常量 -------------
init(autoreset=True)     # 让终端颜色自动重置
IPINFO_ENDPOINT = "https://ipinfo.io/json"
DEFAULT_TEST_FILE_URL = "http://download.thinkbroadband.com/20MB.zip"   # 默认测速文件

# ----------- 辅助函数 -------------
def format_human_readable_speed(bytes_per_second):
    """
    将字节/秒转换为人眼友好的格式，例如 "1.23 MB/s"
    """
    speed_value = float(bytes_per_second)
    for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
        if speed_value < 1024:
            return "%.2f %s" % (speed_value, unit)
        speed_value /= 1024
    return "%.2f GB/s" % speed_value

def create_requests_session(proxy_url):
    """
    创建一个 requests.Session()，并根据 proxy_url 设置 HTTP/HTTPS 代理。
    如果 proxy_url 为 None，则不使用代理。
    """
    session = requests.Session()
    if proxy_url:
        session.proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
    session.trust_env = False   # 忽略系统环境变量中的代理设置
    return session

def display_ip_information(requests_session):
    """
    使用 ipinfo.io 查询并打印当前出口 IP、ASN 和国家信息。
    """
    try:
        start_time = time.time()
        response = requests_session.get(IPINFO_ENDPOINT, timeout=8).json()
        elapsed_time_ms = (time.time() - start_time) * 1000   # 转为毫秒
        print(Fore.CYAN + "\n出口 IP 查询耗时: %.0f ms" % elapsed_time_ms)
        print(Fore.GREEN + "  IP      :", response.get("ip"))
        print(Fore.GREEN + "  ASN     :", response.get("org"))
        print(Fore.GREEN + "  国家   :", response.get("country"))
    except Exception as exception:
        print(Fore.RED + "IP 查询失败：", exception)

# ----------- 下载线程 -------------
def download_thread_worker(file_url, requests_session, bytes_queue):
    """
    后台线程函数：下载 file_url 指定的文件，分块读取并将每块字节长度放入 bytes_queue。
    下载完成后放入 None 以通知主线程。
    """
    try:
        with requests_session.get(file_url, stream=True, timeout=15) as http_response:
            http_response.raise_for_status()
            #这个是request库里的一个方法，检查服务器返回的http响应状态码，如果是不成功就不会执行接下来的代码。
            for data_chunk in http_response.iter_content(chunk_size=8192):
                bytes_queue.put(len(data_chunk))
    except RequestException as exception:
        print(Fore.RED + "下载线程出错：", exception)
    finally:
        bytes_queue.put(None)   # 通知主线程，这个线程已完成

def perform_speed_test(requests_session, file_url, number_of_threads):
    """
    启动 number_of_threads 个下载线程并行下载 file_url，
    主线程从 bytes_queue 读取各线程汇报的字节数，计算总和并显示进度条。
    最后打印总下载量、用时和平均速度。
    """
    print(Fore.CYAN + "\n测速文件 URL:", file_url)
    print(Fore.CYAN + "并发线程数  :", number_of_threads)

    total_downloaded_bytes = 0
    completed_thread_count = 0
    bytes_queue = queue.Queue()

    progress_bar = tqdm(
        total=0,
        unit="B",
        unit_scale=True,
        bar_format="{l_bar}{bar}| {n_fmt}B"
    )

    # 启动每个下载线程
    for _ in range(number_of_threads):
        worker = threading.Thread(
            target=download_thread_worker,
            args=(file_url, requests_session, bytes_queue)
        )
        worker.daemon = True
        worker.start()

    test_start_time = time.time()

    # 主线程从队列收集数据
    while completed_thread_count < number_of_threads:
        queue_item = bytes_queue.get()
        if queue_item is None:
            completed_thread_count += 1
        else:
            total_downloaded_bytes += queue_item
            progress_bar.update(queue_item)

    elapsed_seconds = time.time() - test_start_time
    progress_bar.close()

    downloaded_megabytes = total_downloaded_bytes / 1_048_576
    print(Fore.GREEN + "\n总共下载: %.2f MB  用时: %.1f 秒" 
          % (downloaded_megabytes, elapsed_seconds))
    average_speed = format_human_readable_speed(total_downloaded_bytes / elapsed_seconds)
    print(Fore.GREEN + "平均速度:", average_speed)

# ----------- 主入口 -------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser("简单速度测试")
    parser.add_argument(
        "proxy_url",
        nargs="?",
        default=None,
        help="可选：SOCKS5/HTTP 代理 URL，例如 socks5://user:pass@host:port"
    )
    parser.add_argument(
        "thread_count",
        nargs="?",
        type=int,
        default=1,
        help="可选：并发下载线程数，默认 1"
    )
    args = parser.parse_args()

    print(Style.BRIGHT + "=== Speed Test ===")
    print("代理:", args.proxy_url or "直连")
    print("线程:", args.thread_count)

    session = create_requests_session(args.proxy_url)
    display_ip_information(session)
    perform_speed_test(session, DEFAULT_TEST_FILE_URL, max(1, args.thread_count))