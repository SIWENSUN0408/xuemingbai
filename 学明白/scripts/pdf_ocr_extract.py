#!/usr/bin/env python3
"""
PDF 文本提取与 OCR 脚本。
自动判断 PDF 是否为扫描件，普通 PDF 直接提取文本，扫描件使用 OCR 识别。

用法:
    python3 pdf_ocr_extract.py <pdf_path> [--output <output_txt_path>]
    python3 pdf_ocr_extract.py <pdf_path> --pages 1-5,10  # 只处理指定页

依赖:
    普通 PDF: pip install pdfplumber
    扫描件 OCR: pip install pdfplumber pdf2image pytesseract
               并安装系统依赖: brew install tesseract poppler (macOS)
"""

import sys
import os
import argparse
import re


def check_dependencies(need_ocr=False):
    """检查依赖，缺失时给出安装提示。"""
    missing = []
    try:
        import pdfplumber  # noqa: F401
    except ImportError:
        missing.append("pdfplumber")

    if need_ocr:
        try:
            import pdf2image  # noqa: F401
        except ImportError:
            missing.append("pdf2image")
        try:
            import pytesseract  # noqa: F401
        except ImportError:
            missing.append("pytesseract")

    if missing:
        print(f"[错误] 缺少依赖: {', '.join(missing)}", file=sys.stderr)
        print(f"安装命令: pip install {' '.join(missing)}", file=sys.stderr)
        if need_ocr:
            print("OCR 还需系统依赖: macOS 执行 `brew install tesseract poppler`", file=sys.stderr)
        sys.exit(1)


def extract_text_normal(pdf_path, page_numbers=None):
    """用 pdfplumber 提取普通 PDF 文本。"""
    import pdfplumber

    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        if page_numbers is None:
            page_numbers = range(1, total_pages + 1)

        for page_num in page_numbers:
            if page_num < 1 or page_num > total_pages:
                continue
            page = pdf.pages[page_num - 1]
            text = page.extract_text() or ""
            texts.append(f"=== 第 {page_num} 页 ===\n{text}")

    return "\n\n".join(texts), total_pages


def is_scanned_pdf(text, total_pages, threshold=50):
    """判断是否为扫描件：平均每页文本少于阈值字符。"""
    if total_pages == 0:
        return False
    # 移除页码标记后统计
    clean_text = re.sub(r'=== 第 \d+ 页 ===', '', text)
    avg_chars = len(clean_text.strip()) / total_pages
    return avg_chars < threshold


def extract_text_ocr(pdf_path, page_numbers=None, lang='chi_sim+eng'):
    """对扫描件 PDF 进行 OCR 识别。"""
    from pdf2image import convert_from_path
    import pytesseract

    if page_numbers is None:
        images = convert_from_path(pdf_path)
        page_numbers = range(1, len(images) + 1)
    else:
        images = convert_from_path(pdf_path, first_page=min(page_numbers), last_page=max(page_numbers))

    texts = []
    for idx, img in enumerate(images):
        page_num = page_numbers[idx] if idx < len(page_numbers) else idx + 1
        print(f"[OCR] 正在识别第 {page_num} 页...", file=sys.stderr)
        text = pytesseract.image_to_string(img, lang=lang)
        texts.append(f"=== 第 {page_num} 页 ===\n{text}")

    return "\n\n".join(texts)


def parse_page_ranges(page_str, total_pages):
    """解析页码范围字符串，如 '1-5,10,12-15'。"""
    if not page_str:
        return None
    pages = set()
    for part in page_str.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            pages.update(range(start, end + 1))
        else:
            pages.add(int(part))
    return sorted(p for p in pages if 1 <= p <= total_pages)


def main():
    parser = argparse.ArgumentParser(description='PDF 文本提取与 OCR')
    parser.add_argument('pdf_path', help='PDF 文件路径')
    parser.add_argument('--output', '-o', help='输出文本文件路径（默认输出到终端）')
    parser.add_argument('--pages', help='指定页码，如 1-5,10,12-15')
    parser.add_argument('--lang', default='chi_sim+eng', help='OCR 语言（默认中英混合）')
    parser.add_argument('--force-ocr', action='store_true', help='强制使用 OCR（即使能提取文本）')
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"[错误] 文件不存在: {args.pdf_path}", file=sys.stderr)
        sys.exit(1)

    # 先检查基础依赖
    check_dependencies(need_ocr=False)

    # 第一次提取：普通方式
    print(f"[信息] 正在提取文本: {args.pdf_path}", file=sys.stderr)
    text, total_pages = extract_text_normal(args.pdf_path)
    page_numbers = parse_page_ranges(args.pages, total_pages)

    # 判断是否需要 OCR
    need_ocr = args.force_ocr or is_scanned_pdf(text, total_pages)

    if need_ocr:
        print("[信息] 检测到扫描件或文本过少，切换到 OCR 模式", file=sys.stderr)
        check_dependencies(need_ocr=True)
        text = extract_text_ocr(args.pdf_path, page_numbers=page_numbers, lang=args.lang)
    elif page_numbers is not None:
        # 普通 PDF 但指定了页码
        text, _ = extract_text_normal(args.pdf_path, page_numbers=page_numbers)

    # 输出
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"[完成] 文本已保存到: {args.output}", file=sys.stderr)
    else:
        print(text)

    # 统计信息
    char_count = len(re.sub(r'=== 第 \d+ 页 ===', '', text).strip())
    print(f"[统计] 共 {total_pages} 页，提取 {char_count} 字符", file=sys.stderr)


if __name__ == '__main__':
    main()
