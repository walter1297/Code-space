import os
import zipfile
from bs4 import BeautifulSoup
import opencc

# 初始化繁体转简体转换器
converter = opencc.OpenCC('t2s')

def extract_epub(epub_path, extract_path):
    """解压 EPUB 文件"""
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

def convert_text_to_simplified(text):
    """使用 OpenCC 将繁体转换为简体"""
    return converter.convert(text)

def process_html_file(file_path):
    """处理 HTML 文件，将繁体转换为简体"""
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    # 转换 HTML 内的文本
    for tag in soup.find_all(text=True):
        tag.replace_with(convert_text_to_simplified(tag))

    # 保存转换后的文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(str(soup))

def process_epub(extract_path):
    """遍历解压后的 EPUB 内容并转换"""
    for root, _, files in os.walk(extract_path):
        for file in files:
            if file.endswith('.html') or file.endswith('.xhtml'):
                file_path = os.path.join(root, file)
                process_html_file(file_path)

def create_epub(output_path, extract_path):
    """重新打包 EPUB 文件"""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        for root, _, files in os.walk(extract_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, extract_path)
                zip_ref.write(file_path, arcname)

def convert_epub(epub_input, epub_output):
    """主函数：解压 -> 转换 -> 重新打包"""
    extract_path = "/workspaces/extracted_epub"  # 适用于 Codespaces
    os.makedirs(extract_path, exist_ok=True)

    extract_epub(epub_input, extract_path)
    process_epub(extract_path)
    create_epub(epub_output, extract_path)

    print(f'转换完成！简体版 EPUB 已保存至 {epub_output}')

def batch_convert_epub(input_folder, output_foler):
    '''批量转换文件夹中的所有EPUB文件'''
    os.makedirs(output_foler, exist_ok=True)

    for file in os.listdir(input_folder):
        if file.endswith(".epub"):
            epub_input = os.path.join(input_folder, file)
            epub_output = os.path.join(output_foler, f"simplified_{file}")
            print(f"正在转换{epub_input}...")
            convert_epub(epub_input, epub_output)

    print("所有文件转换完成")

# 适用于 GitHub Codespaces
input_folder = "/workspaces/Code-space/input"  # 先上传 input.epub 到 /workspaces/
output_folder = "/workspaces/Code-space/converted_epubs"

convert_epub(input_folder, output_folder)
    
