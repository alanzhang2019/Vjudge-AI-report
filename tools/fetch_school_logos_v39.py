#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下载 39 强基校徽 PNG + QQ 图标（针对中国网络环境，无维基/百度百科时回退到校官网/腾讯 CDN）。

输出:
  static/schools/<slug>.png   — 39 校校徽
  static/qq_logo.png          — QQ 官方 logo

用法: python tools/fetch_school_logos_v39.py [--force]
"""
import os
import sys
import time
import urllib.request
import socket

socket.setdefaulttimeout(10)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_SCHOOLS = os.path.join(ROOT, "static", "schools")
OUT_QQ = os.path.join(ROOT, "static", "qq_logo.png")

# (slug, name, [url候选...]) - 按优先级
SCHOOL_URLS = {
    "pku":   "北京大学",
    "thu":   "清华大学",
    "ruc":   "中国人民大学",
    "buaa":  "北京航空航天大学",
    "bit":   "北京理工大学",
    "cau":   "中国农业大学",
    "bnu":   "北京师范大学",
    "muc":   "中央民族大学",
    "nankai":"南开大学",
    "tju":   "天津大学",
    "dlut":  "大连理工大学",
    "neu":   "东北大学",
    "jlu":   "吉林大学",
    "hit":   "哈尔滨工业大学",
    "fdu":   "复旦大学",
    "tongji":"同济大学",
    "sjtu":  "上海交通大学",
    "ecnu":  "华东师范大学",
    "nju":   "南京大学",
    "seu":   "东南大学",
    "zju":   "浙江大学",
    "ustc":  "中国科学技术大学",
    "xmu":   "厦门大学",
    "sdu":   "山东大学",
    "ouc":   "中国海洋大学",
    "whu":   "武汉大学",
    "hust":  "华中科技大学",
    "csu":   "中南大学",
    "hnu":   "湖南大学",
    "nudt":  "国防科技大学",
    "sysu":  "中山大学",
    "scut":  "华南理工大学",
    "scu":   "四川大学",
    "cqu":   "重庆大学",
    "uestc": "电子科技大学",
    "xjtu":  "西安交通大学",
    "nwpu":  "西北工业大学",
    "nwafu": "西北农林科技大学",
    "lzu":   "兰州大学",
}

# 校徽 URL 候选表（从多轮探测合并）
URLS = {
    "pku":   ["https://www.pku.edu.cn/favicon.ico", "https://www.pku.edu.cn/images/logo.png"],
    "thu":   ["https://www.tsinghua.edu.cn/image/logo180.png", "https://www.tsinghua.edu.cn/favicon.ico"],
    "ruc":   ["https://www.ruc.edu.cn/template/1/out/imgs/mob-logo1.png",
              "https://www.ruc.edu.cn/template/1/out/imgs/logo.png",
              "https://www.ruc.edu.cn/template/1/out/imgs/favicon.ico"],
    "buaa":  ["https://www.buaa.edu.cn/images/logo.png"],
    "bit":   ["https://www.bit.edu.cn/images/gb20190805/footer_logo.png", "https://www.bit.edu.cn/favicon.ico"],
    "cau":   ["https://www.cau.edu.cn/images/logo.png"],
    "bnu":   ["https://www.bnu.edu.cn/images/logo_bg.png", "https://www.bnu.edu.cn/images/logo1.png"],
    "muc":   ["https://www.muc.edu.cn/images/logo.png"],
    "nankai":["https://www.nankai.edu.cn/_upload/tpl/02/58/600/template600/images/logo1.png",
              "https://www.nankai.edu.cn/_upload/tpl/02/58/600/template600/images/logo.png"],
    "tju":   ["https://www.tju.edu.cn/images/logo.png"],
    "dlut":  ["https://www.dlut.edu.cn/images/logo.png", "https://www.dlut.edu.cn/favicon.ico"],
    "neu":   ["https://www.neu.edu.cn/images/libpic/logo.png", "https://www.neu.edu.cn/favicon.ico"],
    "jlu":   ["https://www.jlu.edu.cn/images/logo.jpg", "https://www.jlu.edu.cn/favicon.ico"],
    "hit":   ["https://www.hit.edu.cn/_upload/site/00/ee/238/logo.png"],
    "fdu":   ["https://www.fudan.edu.cn/_upload/site/00/02/2/logo.png"],
    "tongji":["https://www.tongji.edu.cn/images/logo.png"],
    "sjtu":  ["https://www.sjtu.edu.cn/resource/assets/img/ico/favicon.png"],
    "ecnu":  ["https://www.ecnu.edu.cn/images/logo.svg"],
    "nju":   ["https://www.nju.edu.cn/images/logo.png"],
    "seu":   ["https://www.seu.edu.cn/_upload/tpl/0b/59/2905/template2905/images/mlogo.png"],
    "zju":   ["https://www.zju.edu.cn/_upload/tpl/0b/bf/3007/template3007/favicon.ico"],
    "ustc":  ["https://www.ustc.edu.cn/images/logo.png"],
    "xmu":   ["https://www.xmu.edu.cn/images/logo.png"],
    "sdu":   ["https://www.sdu.edu.cn/images/logo.svg", "https://www.sdu.edu.cn/favicon.ico"],
    "ouc":   ["https://www.ouc.edu.cn/_upload/tpl/0c/00/3072/template3072/images/logo.svg"],
    "whu":   ["https://www.whu.edu.cn/images/logo.png"],
    "hust":  ["https://www.hust.edu.cn/images/logo.svg"],
    "csu":   ["https://www.csu.edu.cn/images/logo.png"],
    "hnu":   ["https://www.hnu.edu.cn/images/logo.png"],
    "nudt":  ["https://www.nudt.edu.cn/images/logo.png"],
    "sysu":  ["https://www.sysu.edu.cn/images/logo.png", "https://www.sysu.edu.cn/favicon.ico"],
    "scut":  ["https://www2.scut.edu.cn/_upload/tpl/02/35/565/template565/favicon.ico"],
    "scu":   ["https://www.scu.edu.cn/images/logo.png"],
    "cqu":   ["https://www.cqu.edu.cn/images/bottom_logo_20231214.png",
              "https://www.cqu.edu.cn/images/logo1.png"],
    "uestc": ["https://www.uestc.edu.cn/images/1.png", "https://www.uestc.edu.cn/favicon.ico"],
    "xjtu":  ["https://www.xjtu.edu.cn/img/logo_pic99.png"],
    "nwpu":  ["https://www.nwpu.edu.cn/images/logo2.png", "https://www.nwpu.edu.cn/images/logo_xl.png"],
    "nwafu": ["https://www.nwsuaf.edu.cn/images/logo.png"],
    # lzu 全部 412, 走兜底
    "lzu":   [],
}

# QQ 官方 logo 候选
QQ_URLS = [
    "https://mat1.gtimg.com/www/images/qq2012/qqlogo_1x.png",  # 经典红 Q 企鹅
    "https://www.qq.com/favicon.ico",
]


def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*"})
        r = urllib.request.urlopen(req, timeout=10)
        return r.status, r.headers.get("Content-Type", ""), r.read()
    except Exception as e:
        return None, str(e)[:60], b""


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def download_school(slug, force=False):
    out = os.path.join(OUT_SCHOOLS, f"{slug}.png")
    if not force and os.path.exists(out) and os.path.getsize(out) > 500:
        print(f"  [skip] {slug:7s} {SCHOOL_URLS[slug]:14s} 已有 {os.path.getsize(out)}B")
        return True
    for url in URLS.get(slug, []):
        status, ct, body = fetch(url)
        if status == 200 and len(body) > 300 and ("image" in ct or url.endswith((".ico", ".png", ".jpg", ".svg", ".jpeg"))):
            save(out, body)
            print(f"  [ok]   {slug:7s} {SCHOOL_URLS[slug]:14s} <- {url[:60]:60s} {len(body)}B")
            return True
    print(f"  [miss] {slug:7s} {SCHOOL_URLS[slug]:14s} 全部 URL 失败 (将用占位)")
    return False


def download_qq(force=False):
    if not force and os.path.exists(OUT_QQ) and os.path.getsize(OUT_QQ) > 500:
        print(f"  [skip] qq_logo.png 已有 {os.path.getsize(OUT_QQ)}B")
        return True
    for url in QQ_URLS:
        status, ct, body = fetch(url)
        if status == 200 and len(body) > 500:
            save(OUT_QQ, body)
            print(f"  [ok]   qq_logo.png <- {url}  {len(body)}B")
            return True
    print(f"  [miss] qq_logo.png 全部 URL 失败")
    return False


def main():
    force = "--force" in sys.argv
    print(f"OUT_DIR = {OUT_SCHOOLS}")
    print(f"QQ      = {OUT_QQ}")
    print(f"FORCE   = {force}")
    print(f"========== 39 校校徽 ==========")
    ok = 0
    for slug in SCHOOL_URLS:
        if download_school(slug, force=force):
            ok += 1
    print(f"========== QQ 图标 ==========")
    download_qq(force=force)
    n = len([f for f in os.listdir(OUT_SCHOOLS) if f.endswith(".png")]) if os.path.isdir(OUT_SCHOOLS) else 0
    print(f"\n完成：成功下载 {ok}/39 校徽, static/schools/ 现有 {n} 张")


if __name__ == "__main__":
    main()
