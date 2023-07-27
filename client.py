import base64
import datetime
import math
import os
import threading
import wave
from time import sleep
import pygame
import pyttsx3
import requests
from PyQt5 import Qt
from PyQt5.QtGui import QDesktopServices, QColor, QMovie, QIcon, QContextMenuEvent, QKeySequence, QTextImageFormat, \
    QImage, QPixmap, QCursor, QFontMetrics, QFont
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import QLineEdit, QHBoxLayout, QLabel, QTextEdit, QSlider, QMenu, QAction, QFileDialog, \
    QListWidget, QStyledItemDelegate, QListWidgetItem, QSizePolicy, QTextBrowser, QAbstractButton, QProgressBar, \
    QActionGroup, QDialog, QMessageBox
import sys

from PyQt5.QtCore import Qt, QAbstractListModel, QModelIndex, QUrl, QSize, QEvent, QRect, QBasicTimer, QTimer, \
    pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QListView, QPushButton
from moviepy.video.io.VideoFileClip import VideoFileClip
from pyaudio import PyAudio, paInt16
from datetime import timedelta
import jieba
from mutagen.mp3 import MP3

# 存放语音的标记
FILE_PATHS = []
Audio_Idx = 0
Audio_last_Idx = -1

video_Idx = 0
video_last_Idx = -1

# 视频文件夹路径
file_path_mp4 = ''
# # 词库文件路径
# file_path_ai = ''
# 语音缓存路径
file_path_tmp = ''
current_path = ''
pygame.mixer.init()

keywords = {}

# 百度的token
APP_ID = ''
API_KEY = ''
SECRET_KEY = ''
# 百度 API 接口
class BaiduApi:
    def __init__(self, id, key, skey):
        global Audio_Idx
        self.framerate = 16000  # 采样率
        self.num_samples = 2000  # 采样点
        self.channels = 1  # 声道
        self.sampwidth = 2  # 采样宽度2bytes
        self.FILEPATH = ''
        # self.APP_ID = '36237366'
        # self.API_KEY = 'cWEustIH8LQSxIz7IbDgADus'
        # self.SECRET_KEY = 's4UZ7PpuDh4G9oARrIg8sqd22qokcQZr'
        self.APP_ID = id
        self.API_KEY = key
        self.SECRET_KEY = skey
        self.base_url = "https://openapi.baidu.com/oauth/2.0/token?grant_type=client_credentials&client_id=%s&client_secret=%s"
        self.HOST = self.base_url % (self.API_KEY, self.SECRET_KEY)
        self._running = True
        self._frames = []

    def setFilePath(self, idx):
        self.FILEPATH = file_path_tmp + '/speech' + str(idx) + '.wav'

    def getToken(self, host):
        res = requests.post(host)
        return res.json()['access_token']

    def save_wave_file(self, filepath, data):
        wf = wave.open(filepath, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.sampwidth)
        wf.setframerate(self.framerate)
        wf.writeframes(b''.join(data))
        wf.close()

    def __recording(self):
        self._running = True
        self._frames = []
        pa = PyAudio()
        stream = pa.open(format=paInt16,
                         channels=self.channels,
                         rate=self.framerate,
                         input=True,
                         frames_per_buffer=self.num_samples)

        while self._running:
            data = stream.read(self.num_samples)
            self._frames.append(data)

        stream.stop_stream()
        stream.close()
        pa.terminate()

    def get_audio(self, file):
        with open(file, 'rb') as f:
            data = f.read()
        return data

    def speech2text(self, speech_data, token, dev_pid=1537):
        FORMAT = 'wav'
        RATE = '16000'
        CHANNEL = 1
        CUID = '*******'
        SPEECH = base64.b64encode(speech_data).decode('utf-8')

        data = {
            'format': FORMAT,
            'rate': RATE,
            'channel': CHANNEL,
            'cuid': CUID,
            'len': len(speech_data),
            'speech': SPEECH,
            'token': token,
            'dev_pid': dev_pid
        }
        url = 'https://vop.baidu.com/server_api'
        headers = {'Content-Type': 'application/json'}
        # r=requests.post(url,data=json.dumps(data),headers=headers)
        print('正在识别...')
        r = requests.post(url, json=data, headers=headers)
        Result = r.json()
        if 'result' in Result:
            return Result['result'][0]
        else:
            return Result

    def toText(self, file_path):
        TOKEN = self.getToken(self.HOST)
        speech = self.get_audio(file_path)
        # result = speech2text(speech, TOKEN, int(devpid))
        result = self.speech2text(speech, TOKEN, 1537)
        return result

    def start(self):
        print("开始录音")
        threading._start_new_thread(self.__recording, ())

    def stop(self, idx):
        self._running = False
        print("结束录音, 保存wav文件")
        self.setFilePath(idx)
        self.save_wave_file(self.FILEPATH, self._frames)

        TOKEN = self.getToken(self.HOST)
        speech = self.get_audio(self.FILEPATH)
        # result = speech2text(speech, TOKEN, int(devpid))
        result = self.speech2text(speech, TOKEN, 1537)
        return result

    def cancle(self):
        self._running = False
        print("取消录音")


# 播放音频
class Mp3Player:
    def read(self, file_path):
        outfile = file_path
        pygame.mixer.music.load(outfile)
        pygame.mixer.music.play()
        # threading._start_new_thread(pygame.mixer.music.play, ())

    def stop(self):
        pygame.mixer.music.stop()

    def pause(self):
        pygame.mixer.music.pause()

    def unpause(self):
        pygame.mixer.music.unpause()

    def get_wav_duration(self, file_path):
        with wave.open(file_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            return round(duration, 2)

    def get_mp3_duration(self, file_path):
        audio = MP3(file_path)
        duration = audio.info.length
        return duration


# 播放视频
class Mp4Player:
    type = 'MP4'

    def play(self, path):
        from os import startfile
        startfile(path)


class NoSelectionDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        # 不绘制任何选中效果，留空即可
        pass

    def sizeHint(self, option, index):
        return super().sizeHint(option, index)


# 聊天框
class Chat_Box(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置右键菜单策略为CustomContextMenu，以便触发自定义右键菜单事件
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

    # 右键单击菜单
    def showContextMenu(self, pos):
        # 创建右键菜单
        menu = QMenu(self)

        # 添加清屏菜单项
        clear_action = QAction("清屏", self)
        clear_action.triggered.connect(self.clearScreen)
        menu.addAction(clear_action)

        # 显示菜单
        menu.exec_(self.mapToGlobal(pos))

    def clearScreen(self):
        global Audio_Idx, Audio_last_Idx, video_Idx, video_last_Idx
        FILE_PATHS.clear()
        Audio_Idx = 0

        Audio_Idx = 0
        Audio_last_Idx = -1
        video_Idx = 0
        video_last_Idx = -1
        self.clear()


# 聊天记录
class Chat_history(QTextBrowser):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

        # 右键单击菜单

    def showContextMenu(self, pos):
        # 创建右键菜单
        menu = QMenu(self)

        # 创建复制、粘贴和全选的动作
        copy_action = QAction("复制", self)
        paste_action = QAction("粘贴", self)
        select_all_action = QAction("全选", self)
        # 将动作与对应的槽函数连接
        copy_action.triggered.connect(self.copy)
        paste_action.triggered.connect(self.paste)
        select_all_action.triggered.connect(self.selectAll)

        # 将动作添加到右键菜单
        menu.addAction(copy_action)
        menu.addAction(paste_action)
        menu.addAction(select_all_action)

        # 显示菜单
        menu.exec_(self.mapToGlobal(pos))


# 输入框
class Chat_Input(QLineEdit):
    def enterEvent(self, e):
        super().enterEvent(e)
        QApplication.setOverrideCursor(Qt.IBeamCursor)

    def leaveEvent(self, e):
        super().leaveEvent(e)
        QApplication.setOverrideCursor(Qt.ArrowCursor)

    def contextMenuEvent(self, event: QContextMenuEvent):
        # 创建上下文菜单
        context_menu = QMenu(self)

        # 创建复制和粘贴动作
        copy_action = QAction("复制", self)
        copy_action.setShortcut(QKeySequence.Copy)  # 设置快捷键 Ctrl+C
        copy_action.triggered.connect(self.copy)

        paste_action = QAction("粘贴", self)
        paste_action.setShortcut(QKeySequence.Paste)  # 设置快捷键 Ctrl+V
        paste_action.triggered.connect(self.paste)

        # 创建剪切动作
        cut_action = QAction("剪切", self)
        cut_action.setShortcut(QKeySequence.Cut)  # 设置快捷键 Ctrl+X
        cut_action.triggered.connect(self.cut)

        # 创建全选动作
        select_all_action = QAction("全选", self)
        select_all_action.setShortcut(QKeySequence.SelectAll)  # 设置快捷键 Ctrl+A
        select_all_action.triggered.connect(self.selectAll)

        # 添加动作到菜单中
        context_menu.addAction(copy_action)
        context_menu.addAction(paste_action)
        context_menu.addAction(select_all_action)
        context_menu.addAction(cut_action)

        # 在指定位置显示上下文菜单
        context_menu.exec_(event.globalPos())


# 发送与录音按钮
class MyButton(QPushButton):
    def enterEvent(self, e):
        super().enterEvent(e)
        QApplication.setOverrideCursor(Qt.PointingHandCursor)

    def leaveEvent(self, e):
        super().leaveEvent(e)
        QApplication.setOverrideCursor(Qt.ArrowCursor)


# 播放音频按钮
class PlayMp3Button(QPushButton):

    def __init__(self):
        super().__init__()
        # 播放语音的喇叭
        self.start = QTextImageFormat()
        self.start.setName('Images/laba/start.jpg')
        self.start.setHeight(30)  # 设置图片宽度
        self.start.setWidth(30)  # 设置图片高度

        # 暂停语音的喇叭
        self.stop = QTextImageFormat()
        self.stop.setName('Images/laba/stop.jpg')
        self.stop.setHeight(30)  # 设置图片宽度
        self.stop.setWidth(30)  # 设置图片高度

    def enterEvent(self, e):
        QApplication.setOverrideCursor(Qt.PointingHandCursor)
        super().enterEvent(e)

    def leaveEvent(self, e):
        QApplication.setOverrideCursor(Qt.ArrowCursor)
        super().leaveEvent(e)

    def mouseReleaseEvent(self, event):
        print("按钮被点击了！")
        print(self.objectName())
        global Audio_last_Idx
        # 与按钮绑定的语音条
        Myqpb = window.findChild(MyQProgressBar, self.objectName())

        # 上次点的不是这个按钮
        if Audio_last_Idx != self.objectName():
            Mp3Player().read(FILE_PATHS[int(self.objectName())])
            # threading._start_new_thread(Mp3Player().read, (FILE_PATHS[int(self.objectName())],))
            Myqpb.startAnimation()
            print("第一次点击")
            self.setIcon(QIcon(QPixmap(self.stop.name())))
        else:
            # 现在在读
            if Audio_last_Idx == self.objectName() and pygame.mixer.music.get_busy() == True:
                Mp3Player().pause()
                Myqpb.stopAnimation()
                print("暂停了", FILE_PATHS[int(self.objectName())])
                self.setIcon(QIcon(QPixmap(self.start.name())))
                pass
            # 已经暂停了
            else:
                Mp3Player().unpause()
                Myqpb.startAnimation()
                print("继续", FILE_PATHS[int(self.objectName())])
                self.setIcon(QIcon(QPixmap(self.stop.name())))

        super().mouseReleaseEvent(event)
        Audio_last_Idx = self.objectName()
        print(Audio_last_Idx)


# 语音条
class MyQProgressBar(QProgressBar):
    def __init__(self, max, min, parent=None):
        super().__init__(parent)
        # 播放语音的喇叭
        self.start = QTextImageFormat()
        self.start.setName('Images/laba/start.jpg')
        self.start.setHeight(30)  # 设置图片宽度
        self.start.setWidth(30)  # 设置图片高度

        self.setStyleSheet(
            "QProgressBar { border: 2px solid grey; "
            "border-radius: 5px; color: rgb(20,20,20);  "
            "background-color: #FFFFFF; "
            "text-align: center;}"
            "QProgressBar::chunk {"
            "background-color: rgb(100,200,200); "
            "border-radius: 10px; "
            "margin: 0.1px;  "
            "width: 1px;}")
        self.setFixedSize(300, 20)
        # 设置字体
        font = QFont()
        font.setBold(True)
        font.setWeight(30)
        # 设置最大值最小值
        self.setMaximum(max)
        self.setMinimum(min)
        self.setValue(0)
        # 剩余时间
        seconds = self.maximum() - self.value()
        time_delta = timedelta(seconds=seconds)
        hours = time_delta // timedelta(hours=1)
        minutes = (time_delta % timedelta(hours=1)) // timedelta(minutes=1)
        seconds = (time_delta % timedelta(minutes=1)) // timedelta(seconds=1)
        # 格式化
        self.setFormat("")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateProgressBar)

    def startAnimation(self, interval=1000):
        self.timer.start(interval)

    def stopAnimation(self):
        self.timer.stop()

    def updateProgressBar(self):
        global Audio_last_Idx
        value = self.value() + 1
        if value > self.maximum():
            value = self.minimum()
        self.setValue(value)

        if self.value() == self.maximum():
            button = window.findChild(PlayMp3Button, self.objectName())
            self.stopAnimation()
            self.setValue(0)
            button.setIcon(QIcon(QPixmap(self.start.name())))
            Audio_last_Idx = -1

        # 剩余时间
        seconds = self.maximum() - self.value()
        time_delta = timedelta(seconds=seconds)
        hours = time_delta // timedelta(hours=1)
        minutes = (time_delta % timedelta(hours=1)) // timedelta(minutes=1)
        seconds = (time_delta % timedelta(minutes=1)) // timedelta(seconds=1)
        # 格式化
        self.setFormat(f"{hours:02d}:{minutes:02d}:{seconds:02d}")


# 视频列表
class VideoPlayer(QWidget):
    def __init__(self, video_file):
        super().__init__()
        global video_last_Idx
        self.layout = QVBoxLayout(self)
        self.video_widget = QVideoWidget()
        self.layout.addWidget(self.video_widget)

        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_content = QMediaContent(QUrl.fromLocalFile(video_file))
        self.media_player.setMedia(self.media_content)
        # 自动播放
        self.media_player.play()

    def enterEvent(self, e):
        QApplication.setOverrideCursor(Qt.PointingHandCursor)
        super().enterEvent(e)

    def leaveEvent(self, e):
        QApplication.setOverrideCursor(Qt.ArrowCursor)
        super().leaveEvent(e)

    def mouseReleaseEvent(self, event):
        global video_last_Idx

        # 暂停上次播放的视频
        if not video_last_Idx == -1 and video_last_Idx != self.objectName():
            last = window.findChild(VideoPlayer, str(video_last_Idx))
            last.media_player.pause()

        video_last_Idx = self.objectName()

        # 现在在读
        if self.media_player.state() == 1:
            print("暂停播放")
            self.media_player.pause()
        # 已经暂停了
        elif self.media_player.state() == 2:
            self.media_player.play()
            print("继续播放")

        super().mouseReleaseEvent(event)


# 设置窗口
class SettingDialog(QDialog):
    token_updated = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("百度语音识别设置")

        # 创建标签和输入框
        self.app_id_label = QLabel("APP_ID:")
        self.app_id_input = Chat_Input()

        self.api_key_label = QLabel("API_KEY:")
        self.api_key_input = Chat_Input()

        self.secret_key_label = QLabel("SECRET_KEY:")
        self.secret_key_input = Chat_Input()

        # 创建保存按钮
        self.save_button = MyButton("保存")
        self.save_button.clicked.connect(self.save_settings)

        # 创建布局并添加控件
        layout = QVBoxLayout()
        layout.addWidget(self.app_id_label)
        layout.addWidget(self.app_id_input)
        layout.addWidget(self.api_key_label)
        layout.addWidget(self.api_key_input)
        layout.addWidget(self.secret_key_label)
        layout.addWidget(self.secret_key_input)
        layout.addWidget(self.save_button)

        self.setLayout(layout)
        self

    def save_settings(self):
        app_id = self.app_id_input.text()
        api_key = self.api_key_input.text()
        secret_key = self.secret_key_input.text()
        if not app_id or not api_key or not secret_key:
            QMessageBox.warning(self, "警告", "请输入完整的设置信息！")
        else:
            self.token_updated.emit(app_id, api_key, secret_key)  # 发送自定义信号，将文件路径传递给主窗口
            QMessageBox.warning(self, "恭喜", "保存成功")


class ChatRoomWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("智能回复助手")
        self.setGeometry(200, 200, 800, 800)
        # 初始化菜单栏
        self.initMenu()
        # 回复模式
        self.mode = 'MP4'
        # 回复接口
        self.mp3 = Mp3Player()
        self.mp4 = Mp4Player()
        # 视频文件夹路径
        self.file_path_mp4 = ''
        # # 词库文件路径
        # self.file_path_ai = ''
        # 语音缓存路径
        self.file_path_tmp = ''
        # 回复的视频音频链接
        self.video_path = ''
        self.audio_path = ''

        # 设置图标
        icon = QIcon("Images/touxiang/log.jpg")
        self.setWindowIcon(icon)

        # 创建消息显示框
        self.message_box = Chat_Box()
        delegate = NoSelectionDelegate()
        self.message_box.setItemDelegate(delegate)
        # 设置水平滚动条策略为不显示
        self.message_box.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 启用文本自动换行
        self.message_box.setWordWrap(True)
        self.message_box.setStyleSheet("font-size:25px")

        # 机器人头像
        self.gptLog = QTextImageFormat()
        self.gptLog.setName('Images/touxiang/gpt.jpg')
        self.gptLog.setHeight(40)  # 设置图片宽度
        self.gptLog.setWidth(40)  # 设置图片高度

        # 使用者头像
        self.userLog = QTextImageFormat()
        self.userLog.setName('Images/touxiang/user.jpg')
        self.userLog.setHeight(40)  # 设置图片宽度
        self.userLog.setWidth(40)  # 设置图片高度

        # 播放语音的喇叭
        self.start = QTextImageFormat()
        self.start.setName('Images/laba/start.jpg')
        self.start.setHeight(30)  # 设置图片宽度
        self.start.setWidth(30)  # 设置图片高度

        # 播放语音的喇叭
        self.stop = QTextImageFormat()
        self.stop.setName('Images/laba/stop.jpg')
        self.stop.setHeight(30)  # 设置图片宽度
        self.stop.setWidth(30)  # 设置图片高度

        # 创建输入框
        self.chat_entry = Chat_Input(self)
        # 连接回车键的clicked信号到发送消息的槽函数
        self.chat_entry.returnPressed.connect(self.send_message)
        self.chat_entry.setFixedHeight(60)
        self.chat_entry.setStyleSheet("color:black; "
                                      "font-size:25px; "
                                      "border: 10px solid #f4f4f4; "
                                      "background-color: rgb(255, 255, 255);")

        # 开始录音按钮
        self.record_button = MyButton("语音消息", self)
        self.record_button.setFixedSize(90, 50)
        # 百度api的接口类
        # self.luyin = BaiduApi()
        self.label = QLabel()
        self.label.setText("正在录音...")
        self.label.setVisible(False)
        # 创建一个占位的QWidget
        self.spacer = QWidget()
        self.send_luyin = MyButton("发送", self)
        self.stop_luyin = MyButton("取消", self)
        self.send_luyin.setFixedSize(60, 30)
        self.stop_luyin.setFixedSize(60, 30)
        self.send_luyin.setVisible(False)
        self.stop_luyin.setVisible(False)
        # 开始录音
        self.record_button.clicked.connect(self.startRecord)
        # 发送录音
        self.send_luyin.clicked.connect(self.send_Record)
        # 取消录音
        self.stop_luyin.clicked.connect(self.stopRecord)

        # 创建发送按钮
        self.send_button = MyButton("发送", self)
        # 连接发送按钮的clicked信号到发送消息的槽函数
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setFixedSize(70, 50)

        self.send_button.setStyleSheet(
            "QPushButton{color:black;"  # 颜色 中的四个参数,前三个是控制颜色,第四个控制透明度
            # "font-size:20px;"  # 字体大小  设置字体大小
            # "font-weight:bold;"  # 字体大小    bold可设置字体加粗
            "font:30px bold;"  # 字体大小并且加出
            "font-family:宋体;"  # 字体
            "background-color:(128,128,128);"  # 设置背景颜色
            # "selection-color:red;"       # 选中时的颜色
            # "border-color: rgba(0, 0, 255, 255);" # 边框的颜色
            "border-radius:14px;"  # 边框弧度
            "border:3px solid (140,140,140);"  # 边框宽度和颜色
            "border-style:outsert insert;"              # 边框样式，按下是inset
            "}"
        )

        # 布局
        self.layout_luyin = QHBoxLayout()
        # 设置水平布局
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.addWidget(self.record_button)
        self.horizontalLayout.addWidget(self.chat_entry)
        self.horizontalLayout.addWidget(self.send_button)
        # 设置垂直布局
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.message_box)
        self.layout.addLayout(self.layout_luyin)
        self.layout.addLayout(self.horizontalLayout)
        self.central_widget = QWidget()
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)

    # 添加菜单
    def initMenu(self):
        menubar = self.menuBar()
        # 创建设置菜单
        setting = menubar.addMenu('设置')

        # 创建切换回复模式菜单
        switch_respond_model = setting.addMenu('切换回复模式')
        # 创建动作组
        respond_mode_group = QActionGroup(self)
        respond_mode_group.setExclusive(True)  # 设置为互斥选择
        # 创建切换mp4模式
        mp4Mode = QAction('MP4', self)
        mp4Mode.setCheckable(True)
        mp4Mode.setChecked(True)  # 设置选中可视化
        switch_respond_model.addAction(mp4Mode)
        # 添加分隔线
        switch_respond_model.addSeparator()
        # 创建切换mp3模式
        mp3Mode = QAction('MP3', self)
        mp3Mode.setCheckable(True)
        switch_respond_model.addAction(mp3Mode)

        mp4Mode.setActionGroup(respond_mode_group)  # 将动作添加到动作组中
        mp3Mode.setActionGroup(respond_mode_group)  # 将动作添加到动作组中

        # 创建设置文件路径菜单
        file_path_setting = QAction('设置百度Token', self)
        file_path_setting.triggered.connect(self.openSettingDialog)
        setting.addAction(file_path_setting)

        # 创建退出动作，并添加到设置菜单中
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        setting.addAction(exit_action)
        # 连接切换模式的槽函数
        respond_mode_group.triggered.connect(self.onModeChanged)

    def onModeChanged(self, action):
        self.mode = action.text()
        print("切换回复模式为:", action.text())
        print(self.mode)

    def openSettingDialog(self):
        dialog = SettingDialog(self)
        dialog.token_updated.connect(self.token_updated)
        dialog.exec_()

    # 获取变化的MP4文件路径
    def token_updated(self, id, key, skey):
        global APP_ID, API_KEY, SECRET_KEY
        APP_ID = id
        API_KEY = key
        SECRET_KEY = skey

        self.APP_ID = id
        self.API_KEY = key
        self.SECRET_KEY = skey

        self.config.set('BAIDU_API', 'APP_ID', APP_ID)
        self.config.set('BAIDU_API', 'API_KEY', API_KEY)
        self.config.set('BAIDU_API', 'SECRET_KEY', SECRET_KEY)
        with open('config.ini', "w") as config_file:
            self.config.write(config_file)
        self.luyin = BaiduApi(self.APP_ID, self.API_KEY, self.SECRET_KEY)

    # 开始录音
    def startRecord(self):
        self.record_button.setDisabled(True)
        self.send_luyin.setVisible(True)
        self.stop_luyin.setVisible(True)
        self.label.setVisible(True)
        self.layout_luyin.addWidget(self.label)
        self.layout_luyin.addWidget(self.spacer)
        self.layout_luyin.addWidget(self.send_luyin)
        self.layout_luyin.addWidget(self.stop_luyin)
        self.luyin.start()

    # 结束录音
    def stopRecord(self):
        self.record_button.setDisabled(False)
        self.send_luyin.setVisible(False)
        self.stop_luyin.setVisible(False)
        self.label.setVisible(False)
        self.layout_luyin.removeWidget(self.label)
        self.layout_luyin.removeWidget(self.spacer)
        self.layout_luyin.removeWidget(self.send_luyin)
        self.layout_luyin.removeWidget(self.stop_luyin)
        self.luyin.cancle()

    # 发送语音
    def send_Record(self):
        global file_path_mp4, file_path_tmp
        self.record_button.setDisabled(False)
        self.record_button.setDisabled(False)
        self.send_luyin.setVisible(False)
        self.stop_luyin.setVisible(False)
        self.label.setVisible(False)
        self.layout_luyin.removeWidget(self.label)
        self.layout_luyin.removeWidget(self.spacer)
        self.layout_luyin.removeWidget(self.send_luyin)
        self.layout_luyin.removeWidget(self.stop_luyin)
        global Audio_Idx
        # 语音转文本
        try  :
            message = self.luyin.stop(Audio_Idx)
        except requests.exceptions.ConnectionError :
            self.response_error("没连上网络，请先连接网络")
            return
        except KeyError :
            self.response_error("API参数设置有问题，请进行修改")
            return
        text = Chat_history()
        text.setText(message)
        text.setStyleSheet(
            "font:22px bold;"
            "font-family:Arial;"
            "background-color: rgb(0,250,154);"
            "border-radius: 20px; "
        )
        xlen = QFontMetrics(text.font()).width(text.toPlainText()) // 600 + 1
        text.setFixedSize(600, xlen * 40)


        # 创建自定义的QListWidgetItem
        item = QListWidgetItem()
        # 创建包含滑动条的小部件
        widget = QWidget()
        v_layout = QVBoxLayout()
        h_layout = QHBoxLayout()
        t_layout = QHBoxLayout()

        # 发消息初始化 添加头像
        touxiang = QLabel()
        touxiang.setText(f"<img src={self.userLog.name()} width='40' height='40'>")
        touxiang.setStyleSheet(
            "font:18px bold;"
            "font-family:宋体"
        )
        touxiang.setAlignment(Qt.AlignRight)

        # 语音条
        length = self.mp3.get_wav_duration(file_path_tmp + '/speech' + str(Audio_Idx) + '.wav')
        print(length)
        if length < 1:
            self.response_error("录音时长太短啦，请说话时长超过一秒哟")
            return
        # 创建一个占位的QWidget
        spacer = QWidget()
        # 创建滑块控件充当语音条
        # Myqpb = MyQProgressBar(math.ceil(length), 0)
        # 创建播放语音按钮
        play = PlayMp3Button()
        play.setIcon(QIcon(QPixmap(self.start.name())))
        play.setFixedSize(30, 30)
        # 给播放按钮和语音条进行相应的标注
        # Myqpb.setValue(0)
        # Myqpb.setObjectName(str(Audio_Idx))
        play.setObjectName(str(Audio_Idx))

        # # 水平布局
        # h_layout.addWidget(spacer)
        # h_layout.addWidget(Myqpb)
        # 文字部分
        t_layout.addWidget(spacer)
        t_layout.addWidget(text)
        t_layout.addWidget(play)

        # 垂直布局
        v_layout.addWidget(touxiang)
        v_layout.addLayout(h_layout)
        v_layout.addLayout(t_layout)

        widget.setLayout(v_layout)
        # 将小部件设置为项目的小部件
        item.setSizeHint(widget.sizeHint())
        self.message_box.addItem(item)
        self.message_box.setItemWidget(item, widget)

        # 讲发送的语音识别成文字保存到 Messages
        FILE_PATHS.append(file_path_tmp + '/speech' + str(Audio_Idx) + '.wav')
        if self.mode == 'MP3':
            self.response_mp3(message)
        elif self.mode == 'MP4':
            self.response_mp4(message)

        Audio_Idx += 1
        # 将QListWidget滚动到最底部
        self.message_box.scrollToBottom()

    # 发送文本
    def send_message(self):
        message = self.chat_entry.text()
        if message:
            # 创建自定义的QListWidgetItem
            item = QListWidgetItem()
            # 创建包含滑动条的小部件
            widget = QWidget()
            # 设置布局
            v_layout = QVBoxLayout()
            h_layout = QHBoxLayout()

            # 发消息初始化 添加头像
            touxiang = QLabel()
            touxiang.setText(f"<img src={self.userLog.name()} width='40' height='40'>")
            touxiang.setAlignment(Qt.AlignRight)
            touxiang.setStyleSheet(
                "font:18px bold;"
                "font-family:宋体"
            )
            # 创建一个占位的QWidget
            spacer = QWidget()
            # 添加其他控件或标签等
            text = Chat_history()
            text.setText(message)
            text.setStyleSheet(
                "font:22px bold;"
                "font-family:Arial;"
                "background-color: rgb(0,250,154);"
                "border-radius: 20px; "
            )
            xlen = QFontMetrics(text.font()).width(text.toPlainText()) // 600 + 1
            text.setFixedSize(600, xlen * 40)

            # 水平布局
            h_layout.addWidget(spacer)
            h_layout.addWidget(text)
            # 垂直布局
            v_layout.addWidget(touxiang)
            v_layout.addLayout(h_layout)

            widget.setLayout(v_layout)
            # 将小部件设置为项目的小部件
            item.setSizeHint(widget.sizeHint())
            self.message_box.addItem(item)
            self.message_box.setItemWidget(item, widget)

            self.chat_entry.clear()
            if self.mode == 'MP3':
                self.response_mp3(message)
            elif self.mode == 'MP4':
                self.response_mp4(message)
        # 将QListWidget滚动到最底部
        self.message_box.scrollToBottom()
        self.chat_entry.setFocus()

    def HuiFu_text(self, message):
        global keywords
        keys = keywords.keys()
        for key in keys:
            if key in message:
                return keywords[key]
            pass

    # 回复语音
    def response_mp3(self, message):
        global Audio_Idx, file_path_tmp

        # AI 回复内容

        # 创建自定义的QListWidgetItem
        item = QListWidgetItem()
        # 创建包含滑动条的小部件
        widget = QWidget()
        v_layout = QVBoxLayout()
        h_layout = QHBoxLayout()

        # 发消息初始化 添加头像
        touxiang = QLabel()
        touxiang.setText(f"<img src={self.gptLog.name()} width='40' height='40'>")
        touxiang.setAlignment(Qt.AlignLeft)
        touxiang.setStyleSheet(
            "font:18px bold;"
            "font-family:宋体"
        )
        gpt_message = self.HuiFu_text(message)
        print("问" + message + '\n' + "答" + str(gpt_message))

        # 语音路径
        self.audio_path = self.file_path_mp4 + '\\' + str(gpt_message) + '.mp3'
        print(self.audio_path)

        # 创建一个占位的QWidget
        spacer = QWidget()
        if str(gpt_message) != 'None' and os.path.exists(self.audio_path):
            length = self.mp3.get_mp3_duration(self.audio_path)
            print(length)
            # 创建滑块控件充当语音条
            Myqpb = MyQProgressBar(math.ceil(length), 0)
            # 创建播放语音按钮
            play = PlayMp3Button()
            play.setIcon(QIcon(QPixmap(self.start.name())))
            play.setFixedSize(30, 30)
            FILE_PATHS.append(self.file_path_mp4 + '\\' + str(gpt_message) + '.mp3')

            # 给播放按钮和语音条进行相应的标注
            Myqpb.setValue(0)
            Myqpb.setObjectName(str(Audio_Idx))
            play.setObjectName(str(Audio_Idx))
            # 水平布局
            h_layout.addWidget(Myqpb)
            h_layout.addWidget(play)
            h_layout.addWidget(spacer)

            Audio_Idx += 1
        else:
            text = Chat_history()
            text.setStyleSheet(
                "font:22px bold;"
                "font-family:Arial;"
                "background-color: rgb(0,250,154);"
                "border-radius: 20px; "
            )

            text.setText("我也不知道哟 这边建议您百度呢")
            xlen = QFontMetrics(text.font()).width(text.toPlainText()) // 600 + 1
            text.setFixedSize(600, xlen * 40)

            h_layout.addWidget(text)
            h_layout.addWidget(spacer)
            pass

        # 垂直布局
        v_layout.addWidget(touxiang)
        v_layout.addLayout(h_layout)

        widget.setLayout(v_layout)
        # 将小部件设置为项目的小部件
        item.setSizeHint(widget.sizeHint())
        self.message_box.addItem(item)
        self.message_box.setItemWidget(item, widget)

        # 将QListWidget滚动到最底部
        self.message_box.scrollToBottom()

    # 回复视频超链接
    def response_mp4(self, message):
        # 创建自定义的QListWidgetItem
        text_item = QListWidgetItem()
        video_item = QListWidgetItem()
        # 创建包含滑动条的小部件
        widget = QWidget()
        # 设置布局
        v_layout = QVBoxLayout()
        h_layout = QHBoxLayout()

        # 发消息初始化 添加头像
        touxiang = QLabel()
        touxiang.setText(f"<img src={self.gptLog.name()} width='40' height='40'>")
        touxiang.setAlignment(Qt.AlignLeft)
        touxiang.setStyleSheet(
            "font:18px bold;"
            "font-family:宋体"
        )
        v_layout.addWidget(touxiang)

        # 创建一个占位的QWidget
        spacer = QWidget()
        text = Chat_history()
        # AI 回复内容
        gpt_message = self.HuiFu_text(message)
        print(gpt_message)
        self.video_path = self.file_path_mp4 + '\\' + str(gpt_message) + '.mp4'
        video_player = None
        # 判断文件存在
        if str(gpt_message) != 'None' and os.path.exists(self.video_path):
            # video_player = VideoPlayer(r"C:\Users\ChenDong\Desktop\backup\Project\PyCharm\app\answer\导航设计.mp4")
            global video_Idx, video_last_Idx
            # 暂停上次播放的视频
            if not video_last_Idx == -1:
                last = window.findChild(VideoPlayer, str(video_last_Idx))
                last.media_player.pause()

            video_player = VideoPlayer(self.video_path)
            video_player.setObjectName(str(video_Idx))
            # 将视频设置为上次播放视频
            video_last_Idx = video_player.objectName()
            video_Idx += 1
            # video_item.setSizeHint(video_player.size())
            video_item.setSizeHint(QSize(200, 200))
            video_player.setFixedSize(200, 200)
        else:
            if not video_last_Idx == -1:
                last = window.findChild(VideoPlayer, str(video_last_Idx))
                last.media_player.pause()
            text.setText("我也不知道哟 这边建议您百度呢")
            text.setStyleSheet(
                "font:22px bold;"
                "font-family:Arial;"
                "background-color: rgb(0,250,154);"
                "border-radius: 20px; "
            )
            xlen = QFontMetrics(text.font()).width(text.toPlainText()) // 600 + 1
            text.setFixedSize(600, xlen * 40)
            # 水平布局
            h_layout.addWidget(text)
            h_layout.addWidget(spacer)

            # 垂直布局
            v_layout.addLayout(h_layout)


        widget.setLayout(v_layout)
        # 将小部件设置为项目的小部件
        text_item.setSizeHint(widget.sizeHint())
        self.message_box.addItem(text_item)
        self.message_box.setItemWidget(text_item, widget)
        if video_player != None:
            self.message_box.addItem(video_item)
            self.message_box.setItemWidget(video_item, video_player)

        # 将QListWidget滚动到最底部
        self.message_box.scrollToBottom()
        pass

    # 出现错误的回复信息
    def response_error(self, message):
        global Audio_Idx, file_path_tmp
        # AI 回复内容

        # 创建自定义的QListWidgetItem
        item = QListWidgetItem()
        # 创建包含滑动条的小部件
        widget = QWidget()
        v_layout = QVBoxLayout()
        h_layout = QHBoxLayout()

        # 发消息初始化 添加头像
        touxiang = QLabel()
        touxiang.setText(f"<img src={self.gptLog.name()} width='40' height='40'>")
        touxiang.setAlignment(Qt.AlignLeft)
        touxiang.setStyleSheet(
            "font:18px bold;"
            "font-family:宋体"
        )
        spacer = QWidget()
        text = Chat_history()
        text.setStyleSheet(
            "font:22px bold;"
            "font-family:Arial;"
            "background-color: rgb(0,250,154);"
            "border-radius: 20px; "
        )

        text.setText(message)
        xlen = QFontMetrics(text.font()).width(text.toPlainText()) // 600 + 1
        text.setFixedSize(600, xlen * 40)

        h_layout.addWidget(text)
        h_layout.addWidget(spacer)
        pass

        # 垂直布局
        v_layout.addWidget(touxiang)
        v_layout.addLayout(h_layout)

        widget.setLayout(v_layout)
        # 将小部件设置为项目的小部件
        item.setSizeHint(widget.sizeHint())
        self.message_box.addItem(item)
        self.message_box.setItemWidget(item, widget)

        # 将QListWidget滚动到最底部
        self.message_box.scrollToBottom()

    def init_lunch(self):
        global file_path_mp4, file_path_tmp, current_path, APP_ID, API_KEY, SECRET_KEY
        import os
        import shutil
        import configparser

        # 文件不存在就创建配置文件
        ini_file = "config.ini"
        if not os.path.exists(ini_file):
            with open(ini_file, "w") as f:
                f.write("[FILE_PATH]\n")
                f.write("MP4_PATH = answer\n")
                f.write("TMP = tmp\n")
                f.write("[BAIDU_API]\n")
                f.write("APP_ID = .\n")
                f.write("API_KEY = .\n")
                f.write("SECRET_KEY = .\n")
                f.close()
        # 创建ConfigParser对象
        self.config = configparser.ConfigParser()
        # 读取配置文件
        self.config.read(ini_file)

        # 获取配置项的值
        file_path_mp4 = self.config.get('FILE_PATH', 'MP4_PATH')
        file_path_tmp = self.config.get('FILE_PATH', 'TMP')

        APP_ID = self.config.get('BAIDU_API', 'APP_ID')
        API_KEY = self.config.get('BAIDU_API', 'API_KEY')
        SECRET_KEY = self.config.get('BAIDU_API', 'SECRET_KEY')
        current_path = os.path.dirname(os.path.realpath(__file__))

        self.file_path_mp4 = file_path_mp4
        self.file_path_tmp = file_path_tmp

        self.APP_ID = APP_ID
        self.API_KEY = API_KEY
        self.SECRET_KEY = SECRET_KEY

        if not os.path.exists(file_path_mp4):
            os.makedirs(file_path_mp4)

        if not os.path.exists(file_path_tmp):
            os.makedirs(file_path_tmp)

        # 删除录音存档
        file_list = os.listdir(file_path_tmp)
        for file_name in file_list:
            file_path = os.path.join(file_path_tmp, file_name)

            # 判断是否为文件
            if os.path.isfile(file_path):
                # 删除文件
                os.remove(file_path)
            else:
                # 如果是子文件夹，则使用 shutil.rmtree() 递归删除文件夹及其内容
                shutil.rmtree(file_path)

        # mp4提取mp3
        file_list = os.listdir(file_path_mp4)
        for file_name in file_list:
            file_path = os.path.join(file_path_mp4, file_name)
            # 判断是否为文件
            if os.path.isfile(file_path) and file_path.endswith('.mp4') and not os.path.exists(
                    file_path.split('.')[0] + '.mp3'):
                # 转换成mp3
                video = VideoFileClip(file_path)
                audio = video.audio
                audio.write_audiofile(file_path.split('.')[0] + '.mp3')
        print("提取mp3成功")

        # 关键字设置
        global keywords
        if not os.path.exists('keywords.txt'):
            with open('keywords.txt', "w", encoding='utf-8') as f:
                f.write("请删除此行以 ‘关键字:视频的文件名’ 形式配置关键字+\n例：‘吃饭:我吃完饭啦’ 请使用英文的冒号 谢谢")
                f.close()

        with open('keywords.txt', 'r', encoding='utf-8') as file:
            # 逐行读取文件内容
            for line in file:
                # 使用等号进行分割
                split_result = line.strip().split(':')
                # 检查分割结果是否符合预期
                if len(split_result) == 2:
                    key, value = split_result
                    keywords[key] = value
        print(keywords.keys())
        # 重新初始化一下 避免token没进去
        self.luyin = BaiduApi(self.APP_ID, self.API_KEY, self.SECRET_KEY)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatRoomWindow()
    window.init_lunch()

    # 创建自定义的QListWidgetItem
    item = QListWidgetItem()
    # 创建包含滑动条的小部件
    widget = QWidget()
    layout = QVBoxLayout()
    layout_text = QHBoxLayout()

    # 发消息初始化 添加头像
    touxiang = QLabel()
    touxiang.setText(f"<img src={window.gptLog.name()} width='40' height='40'>")
    touxiang.setAlignment(Qt.AlignLeft)
    touxiang.setStyleSheet(
        "font:18px bold;"
        "font-family:宋体"
    )
    layout.addWidget(touxiang)

    # 创建一个占位的QWidget
    spacer = QWidget()
    # 添加其他控件或标签等
    text = Chat_history()
    text.setStyleSheet(
        "font:22px bold;"
        "font-family:Arial;"
        "background-color: rgb(0,250,154);"
        "border-radius: 20px; "
    )

    text.setText("我是您的智能回复助手，请问有什么可以帮您？")

    xlen = QFontMetrics(text.font()).width(text.toPlainText()) // 600 + 1
    h = QFontMetrics(text.font()).height() * text.document().lineCount()
    # print(h)
    text.setFixedSize(600, xlen * 40)

    layout_text.addWidget(text)
    layout_text.addWidget(spacer)
    layout.addLayout(layout_text)

    widget.setLayout(layout)
    # 将小部件设置为项目的小部件
    item.setSizeHint(widget.sizeHint())
    window.message_box.addItem(item)
    window.message_box.setItemWidget(item, widget)

    window.show()
    sys.exit(app.exec_())
