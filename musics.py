import os
import json
import requests
import traceback
import time
import sys
from subprocess import call
from tqdm import tqdm
import platform

host = "https://netease-cloud-music-api-gamma-orpin.vercel.app"  # 网易云api地址
header = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}  # 请求头
config_ = "user.json"  # 配置文件


def confirmPassword(name, password, data): # 判断密码是否正确
    url = host
    d = {}
    if "@" in name:
        url += "/login"
        d["email"] = name
    else:
        url += "/login/cellphone"
        d["phone"] = name
    d["password"] = password
    t = int(time.time())
    url += "?timestamp=" + str(t)
    response = requests.post(url, data=d, headers=header)
    json_obj = json.loads(response.text)
    if json_obj["code"] == 502:
        print("密码错误")
        inputAgain(data)
        return False
    elif json_obj["code"] == 200:
        print("密码正确")
        data["cookie"] = json_obj["cookie"]
        return True
    else:
        print("登录出错")
        inputAgain(data)


def confirmCookie(cookies): # 验证cookie可用性
    t = int(time.time())
    url = host + "/login/status?timestamp=" + str(t)
    response = requests.get(url, headers=header, cookies=cookies)
    json_obj = json.loads(response.text)
    if json_obj["data"]["account"] is None:
        return False
    else:
        return True


def inputAgain(data):
    data["name"] = input("请重新输入您的网易云账号（支持电话，邮箱）")
    data["password"] = input("请重新输入您的网易云密码")
    confirmPassword(data["name"], data["password"], data)


def getCookieDict(cook):
    cookies = {}  # 初始化cookies字典变量
    for line in cook.split(';'):  # 按照字符：进行划分读取
        # 其设置为1就会把字符串拆分成2份
        if line != "":
            name, value = line.strip().split('=')
            cookies[name] = value  # 为字典cookies添加内容
    return cookies


def login(): # 登录方法
    try:
        r = open(config_, "r")
        s = r.read()
        # print(s)
        data = json.loads(s)
        # 判断用户名是否存在
        if "name" in data:
            print("当前账户:" + data["name"])
        else:
            data["name"] = input("请输入您的网易云账号（支持电话，邮箱）")
        name = data["name"]
        # 判断密码是否存在
        if "password" in data:
            print("密码已保存")
        else:
            data["password"] = input("请输入您的网易云密码")
        password = data["password"]
        # 判断密码是否正确
        confirmPassword(name, password, data)

        # 还需要将配置保存
        w = open(config_, "w")
        w.write(json.dumps(data))
        w.close()
        cookie = ""
        if "cookie" in data:
            cookie = data["cookie"]
        return cookie
    except Exception as ex:
        print(traceback.format_exc())


def init():  # 初始化，检查目录
    # 读去配置文件name，password，cookie
    if not os.path.exists(config_):
        w = open(config_, "w")
        w.write('{}')
        w.close()
    # 创建默认下载目录
    if not os.path.isdir("DownLoads"):
        os.makedirs("DownLoads")


def getListDetail(ids, cookie): # 获取歌单详情(包括介绍，名字等等)
    url = host + "/playlist/detail?id=" + str(ids)
    response = requests.get(url, headers=header, cookies=cookie)
    json_obj = json.loads(response.text)
    if json_obj["code"] == 200:
        j = json_obj["playlist"]
    else:
        print("歌单获取失败，请检查您输入的歌单id")
        sys.exit()
    return j


def getListId(j): # 获取歌单所有歌曲id,返回 列表 一系列id
    l = []
    trackIds = j["trackIds"]
    for ids in trackIds:
        # print(ids["id"])
        l.append(ids["id"])
    return l


def getMusicUrl(id, cookie): # 获取音乐真实下载地址
    url = host + "/song/url?id=" + str(id)
    response = requests.get(url, headers=header, cookies=cookie)
    json_obj = json.loads(response.text)
    return json_obj["data"][0]["url"]


def getMusicDetail(id, cookie):  # 获取音乐详情（歌名，作者，专辑)
    url = host + "/song/detail?ids=" + str(id)
    response = requests.get(url, headers=header, cookies=cookie)
    json_obj = json.loads(response.text)
    data = {}
    if len(json_obj["songs"]) > 0:
        data["name"] = json_obj["songs"][0]["name"]  # 获得歌曲名字
        data["imgUrl"] = json_obj["songs"][0]["al"]["picUrl"]  # 获得专辑封面
        # 循环获得作者,拼接字符串
        s = ""
        for au in json_obj["songs"][0]["ar"]:
            s += au["name"] + ","
        data["author"] = s
        data["album"] = json_obj["songs"][0]["al"]["name"]  # 获得专辑名字
    else:
        pass
    return data


def publishDownLoad(ids, cookie): # 打包歌单的歌曲下载链接、歌名等，返回的是json数组对象 # 过程时间比较长，需要进度条
    downl = []
    with tqdm(total=len(ids), desc='进度') as bar:
        t = 0
        for i in ids:
            t += 1
            # print("正在处理："+str(i))
            music = {}
            music["url"] = getMusicUrl(i, cookie)
            detail = getMusicDetail(i, cookie)
            if detail != {}:
                music["name"] = detail["name"]
                music["author"] = detail["author"]
                music["album"] = detail["album"]
                music["imgUrl"] = detail["imgUrl"]
            else:
                print("歌曲获取失败")
            downl.append(music.copy())
            music.clear()
            bar.update(1)

        # 导出下载链接
        file = open("download_link.json", "w")
        file.write(json.dumps(downl))
        file.close()
        # bar.update(t+1)
    print("资源整合成功，下载链接已导出至'download_link.json'")
    return downl


def IDMdownload(dl, down_path):  # dl参数是列表，每个列表项为字典
    IDM = 'C:\\Program Files (x86)\\Internet Download Manager\\IDMan.exe'
    for i in dl:
        if i["url"] is not None:
            down_url = i["url"]
            name_str = i["name"]
            name = ReplaceName(name_str)
            output_filename = name.strip() + ".mp3"
            if os.path.exists(IDM):
                # 使用IDM下载
                call([IDM, '/d', down_url, '/p', down_path,
                      '/f', output_filename, '/n', '/a'])
                print("%s已加入IDM队列" % output_filename)
            else:
                # print("IDM程序不存在,转为普通下载")
                wb_download(down_url, output_filename, down_path)
    print("已下载完成 !!!")


def wb_download(down_url, output_filename, down_path):  # 普通下载
    os.chdir(down_path)
    headers = {
        'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:56.0) Gecko/20100101 Firefox/56.0"}
    try:
        r = requests.get(down_url, headers=headers)
        f = open(output_filename, "wb")
        f.write(r.content)
        print(output_filename, "已下载 !!!")
        f.close()
    except Exception as e:
        print(e)
        pass


def start_download(down_path):  # 下载
    xz = input("是否下载歌曲?(y/n):")
    if xz == 'y' or xz == 'Y' or xz == '':
        print("默认保存路径为%s" % down_path)
        IDMdownload(download, down_path)
    elif xz == "n" or xz == "N":
        exit()
    else:
        print("输入有误!")
        start_download(down_path)


def ReplaceName(name_str):
    sets = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in name_str:
        if char in sets:
            name_str = name_str.replace(char, '')
    return name_str


cookie = {}
playlistName = ""
print("欢迎使用网易云歌单音乐批量导出工具")
init()
# 是否要登录？
user_input = input("您是否要登录网易云音乐？(y/n):").strip()
if user_input == 'y' or user_input == 'Y' or user_input == '':
    cook = login()
    # print(cookie)
    cookie = getCookieDict(cook)
    if not confirmCookie(cookies=cookie):
        print("ERROR! cookie验证失败,请重新启动")
        sys.exit()
    else:
        # print("验证cookie成功")
        print("登录完成!")
else:
    cookie = {}
ids = input("请输入您要下载的歌单id:").strip()
try:
    play_list = getListDetail(ids=int(ids), cookie=cookie)
    print("歌单名称:" + play_list["name"])
    playlistName = play_list["name"]
    print("歌单里歌曲的数量:" + str(play_list["trackCount"]))
    musics = getListId(play_list)
    download = publishDownLoad(musics, cookie)
except BaseException:
    print("资源整合出错!")
    print(traceback.format_exc())
    sys.exit()
if platform.system() == "Windows":
    down_path = os.getcwd() + "\\DownLoads"
    start_download(down_path)
elif platform.system() == "Linux":
    down_path = os.getcwd() + "/DownLoads"
    start_download(down_path)
