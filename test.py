import os
import sys
import cv2
import time
import ctypes
from GlobalVar import gloVar
import datetime
import configparser
import numpy as np
from threading import Thread
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *



class Ui_MainWindow(QWidget):
    # 视频初始化
    STATUS_INIT = 0
    # 视频播放中
    STATUS_PLAYING = 1
    # 视频暂停
    STATUS_PAUSE = 2
    # 视频播放完毕
    STATUS_STOP = 3
    # 保存模板状态
    STATUS_SAVE_TEMPLATE = False
    # 数据处理标志
    FLAG_DATA_PROCESS = False
    # 保存当前暂停时的图片(定义1280*1024/三通道的图片)
    IMAGE = np.zeros((1280, 1024, 3), np.uint8)
    # 传入模板路径
    MASK_PATH = None

    # 字体 'Microsoft YaHei'
    font = 'Times New Roman'
    # icon文件
    icon_file = 'config/Icon.jpg'
    # background文件
    background_file = 'config/background.jpg'

    def setupUi(self, MainWindow):
        # 保存的case执行完的视频
        self.videos = []
        # 保存的视频中case类型和视频名字
        self.videos_title = []
        # 获取到的视频目录
        self.get_path = None
        self.video_play_flag = False  # False直播/True录播
        self.current_video = 0  # 当前视频所在序列号(第0个视频)
        self.current_frame = 0  # 当前帧数
        self.frame_count = 0  # 总帧数
        # 滑动条标志位(如果有滑动动作标志为True, 否则为False)
        self.slider_flag = False
        # 使用自定义定时器
        self.timer_video = Timer()
        self.timer_video.timeSignal.signal[str].connect(self.show_video)
        # 使用pyqt定时器
        # self.timer_video = QTimer(self)
        # self.timer_video.timeout.connect(self.show_video)
        # self.timer_video.start(1)
        # cv实时流
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1024)
        # 初始化播放状态
        self.video_status = self.STATUS_INIT

        MainWindow.setObjectName("MainWindow")
        MainWindow.setGeometry(0, 0, 1800, 950)
        MainWindow.setMinimumSize(QtCore.QSize(100, 300))
        MainWindow.setWindowTitle("Auto Robot")
        MainWindow.setWindowIcon(QIcon(Ui_MainWindow.icon_file))
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.grid = QtWidgets.QGridLayout(self.centralwidget)
        # self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setObjectName('grid')
        ## 定义UI 字体 和 字号大小
        QFontDialog.setFont(self, QFont(Ui_MainWindow.font, 13))
        # 设置UI背景颜色为灰色
        self.setStyleSheet('background-color:lightgrey')
        # 控制台输出框架
        self.output_text()
        # 视频播放框架
        self.video_play_frame()

        # 视频进度条
        self.slider_thread = Timer(frequent=4)
        self.slider_thread.timeSignal.signal[str].connect(self.slider_refresh)
        self.slider_thread.start()

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(30, 0, 290, 30))
        self.menubar.setObjectName("menubar")

        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        sys.stdout = Stream(newText=self.update_text)
        sys.stderr = Stream(newText=self.update_text)

    # 摄像头截屏线程
    def screen_capture_thread(self, capture_type):
        capture_path = os.path.join(self.project_root_path, 'capture')
        if os.path.exists(capture_path) is False:
            os.makedirs(capture_path)
        capture_name = str(datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')) + '.' + capture_type
        capture_name = os.path.join(capture_path, capture_name)
        cv2.imencode('.' + capture_type, self.image.copy())[1].tofile(capture_name)
        print('[截取的图片为: %s]' % capture_name)



    # 更新控制台内容
    def update_text(self, text):
        cursor = self.console.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.console.setTextCursor(cursor)
        self.console.ensureCursorVisible()


    # 视频播放框架
    def video_play_frame(self):
        self.label_video = Video_Label(self.centralwidget)
        self.grid.addWidget(self.label_video, 0, 0, 3, 8)
        self.label_video.setObjectName('label_video')
        # self.label_video.setGeometry(QRect(0, 0, 1280, 1024))
        # 填充背景图片
        self.label_video.setPixmap(QtGui.QPixmap(self.background_file))
        self.label_video.setScaledContents(True)
        # 十字光标
        self.label_video.setCursor(Qt.CrossCursor)
        # label垂直布局
        self.label_v_layout = QVBoxLayout(self.label_video)
        # button水平布局
        self.button_h_layout = QHBoxLayout(self.label_video)
        # 暂停按钮/空格键
        self.status_video_button = QtWidgets.QPushButton(self.label_video)
        self.status_video_button.setObjectName('status_video_button')
        self.status_video_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.status_video_button.setShortcut(Qt.Key_Space)
        # self.status_video_button.setGeometry(QtCore.QRect(600, 933, 80, 30))
        self.status_video_button.clicked.connect(self.switch_video)
        # 上一个视频
        self.last_video_button = QtWidgets.QPushButton(self.label_video)
        self.last_video_button.setObjectName('last_video_button')
        self.last_video_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.last_video_button.setShortcut(Qt.Key_Up)
        # self.last_video_button.setGeometry(QtCore.QRect(500, 933, 80, 30))
        self.last_video_button.clicked.connect(self.last_video)
        self.last_video_button.setEnabled(False)
        # 下一个视频
        self.next_video_button = QtWidgets.QPushButton(self.label_video)
        self.next_video_button.setObjectName('next_video_button')
        self.next_video_button.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        self.next_video_button.setShortcut(Qt.Key_Down)
        # self.next_video_button.setGeometry(QtCore.QRect(700, 933, 80, 30))
        self.next_video_button.clicked.connect(self.next_video)
        self.next_video_button.setEnabled(False)
        # 上一帧
        self.last_frame_button = QtWidgets.QPushButton(self.label_video)
        self.last_frame_button.setObjectName('last_frame_button')
        self.last_frame_button.setText('上一帧')
        self.last_frame_button.setShortcut(Qt.Key_Left)
        # self.last_frame_button.setGeometry(QtCore.QRect(400, 933, 80, 30))
        self.last_frame_button.clicked.connect(self.last_frame)
        self.last_frame_button.setEnabled(False)
        # 下一帧
        self.next_frame_button = QtWidgets.QPushButton(self.label_video)
        self.next_frame_button.setObjectName('next_frame_button')
        self.next_frame_button.setText('下一帧')
        self.next_frame_button.setShortcut(Qt.Key_Right)
        # self.next_frame_button.setGeometry(QtCore.QRect(800, 933, 80, 30))
        self.next_frame_button.clicked.connect(self.next_frame)
        self.next_frame_button.setEnabled(False)
        # 帧数显示
        self.label_frame_show = QtWidgets.QLabel(self.label_video)
        self.label_frame_show.setGeometry(QtCore.QRect(1150, 940, 130, 20))
        self.label_frame_show.setObjectName("label_frame_show")
        self.label_frame_show.setAlignment(Qt.AlignCenter)
        self.label_frame_show.setText('')
        self.label_frame_show.setFont(QFont(Ui_MainWindow.font, 12))
        self.label_frame_show.setAlignment(Qt.AlignCenter)
        self.label_frame_show.setStyleSheet('color:black')
        # 显示视频名字
        self.label_video_title = QtWidgets.QLabel(self.label_video)
        self.label_video_title.setGeometry(QtCore.QRect(0, 20, 1280, 30))
        self.label_video_title.setObjectName("label_video_title")
        self.label_video_title.setAlignment(Qt.AlignCenter)
        self.label_video_title.setText('实时视频流')
        self.label_video_title.setFont(QFont(Ui_MainWindow.font, 15))
        # 视频进度条
        self.video_progress_bar = QSlider(Qt.Horizontal, self.label_video)
        # self.video_progress_bar.setGeometry(QtCore.QRect(0, 915, 1280, 20))
        self.video_progress_bar.valueChanged.connect(self.connect_video_progress_bar)
        # button布局管理
        self.button_h_layout.addWidget(self.last_frame_button)
        self.button_h_layout.addWidget(self.last_video_button)
        self.button_h_layout.addWidget(self.status_video_button)
        self.button_h_layout.addWidget(self.next_video_button)
        self.button_h_layout.addWidget(self.next_frame_button)
        self.button_h_layout.setSpacing(30)
        # label布局管理
        self.label_v_layout.insertStretch(1)
        self.label_v_layout.addWidget(self.video_progress_bar)
        self.label_v_layout.addLayout(self.button_h_layout)


# 进度条刷新
    def slider_refresh(self):
        if self.video_play_flag is True and self.slider_flag is True:
            try:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                flag, self.image = self.cap.read()
            except Exception as e:
                pass
            self.slider_flag = False

    # 控制台输出
    def output_text(self):
        self.frame_of_console_output = QtWidgets.QFrame(self.centralwidget)
        # self.frame_of_console_output.setGeometry(QtCore.QRect(1360, 730, 608, 243))
        self.grid.addWidget(self.frame_of_console_output, 2, 8, 1, 2)
        self.frame_of_console_output.setFrameShape(QtWidgets.QFrame.Box)
        self.frame_of_console_output.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame_of_console_output.setObjectName("frame_of_console_output")
        self.label_output = QtWidgets.QLabel(self.frame_of_console_output)
        self.label_output.setGeometry(QtCore.QRect(10, 5, 110, 25))
        self.label_output.setObjectName("label_output")
        self.label_output.setText('[Console输出]')
        self.label_output.setAlignment(Qt.AlignCenter)
        self.label_output.setFont(QFont(Ui_MainWindow.font, 12))
        self.console = QTextEdit(self.frame_of_console_output)
        self.console.setReadOnly(True)
        self.console.ensureCursorVisible()
        self.console.setLineWrapColumnOrWidth(606)
        self.console.setLineWrapMode(QTextEdit.FixedPixelWidth)
        self.console.setWordWrapMode(QTextOption.NoWrap)
        self.console.setFixedWidth(606)
        self.console.setFixedHeight(213)
        self.console.move(2,30)
        self.console.setFont(QFont(Ui_MainWindow.font, 12))
        self.console.setStyleSheet('background-color:lightGray')


    # 展示视频函数
    def show_video(self):
        # 实时模式
        if self.video_play_flag is False:
            flag, self.image = self.cap.read()
            if gloVar.save_pic_status == True:
                cv2.imencode('.jpg', self.image.copy())[1].tofile('mask.jpg')
                gloVar.save_pic_status = False
            if flag == True:
                show = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
                show_image = QtGui.QImage(show.data, show.shape[1], show.shape[0], QtGui.QImage.Format_RGB888)
                self.label_video.setPixmap(QtGui.QPixmap.fromImage(show_image))
            else:
                self.cap.release()
                self.video_status = Ui_MainWindow.STATUS_STOP
                self.timer_video.stop()
                self.status_video_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        # 录播模式(可以数帧)
        else:
            if self.current_frame < self.frame_count:
                self.current_frame += 1
                flag, self.image = self.cap.read()
                if flag is True:
                    show = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
                    show_image = QtGui.QImage(show.data, show.shape[1], show.shape[0], QtGui.QImage.Format_RGB888)
                    self.label_video.setPixmap(QtGui.QPixmap.fromImage(show_image))
                    self.label_frame_show.setText(str(self.current_frame+1)+'F/'+str(self.frame_count))
                    self.label_frame_show.setStyleSheet('color:white')
                    self.video_progress_bar.setValue(self.current_frame)
                else:
                    self.cap.release()
                    self.video_status = Ui_MainWindow.STATUS_STOP
                    self.timer_video.stop()
                    self.status_video_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
                    self.video_progress_bar.setValue(self.frame_count-1)
                    self.last_video_button.setEnabled(True)
                    self.next_video_button.setEnabled(True)
            else:
                self.video_status = Ui_MainWindow.STATUS_STOP
                self.timer_video.stop()
                self.status_video_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        QApplication.processEvents() # 界面刷新


# 暂停视频
    def template_label(self):
        time.sleep(0.3)
        Ui_MainWindow.IMAGE = self.image
        # # 数据处理调用
        # if Ui_MainWindow.FLAG_DATA_PROCESS is True:
        #     maskImage_path = os.path.join(self.get_path, 'mask')
        # else:
        #     maskImage_path = None
        maskImage_path = r'D:\Work\Performance\picture'
        Ui_MainWindow.MASK_PATH = maskImage_path

    # 空格键 播放/暂停/重播
    def switch_video(self):
        # 按钮防抖
        self.status_video_button.setEnabled(False)
        # 如果是实时模式
        if self.video_play_flag is False:
            if self.video_status is Ui_MainWindow.STATUS_INIT:
                self.timer_video.start()
                self.label_video_title.setStyleSheet('color:white')
                self.video_status = Ui_MainWindow.STATUS_PLAYING
                Ui_MainWindow.STATUS_SAVE_TEMPLATE = False
                self.status_video_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            elif self.video_status is Ui_MainWindow.STATUS_PLAYING:
                self.timer_video.stop()
                self.video_status = Ui_MainWindow.STATUS_PAUSE
                Ui_MainWindow.STATUS_SAVE_TEMPLATE = True
                self.status_video_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
                self.template_label()
            elif self.video_status is Ui_MainWindow.STATUS_PAUSE:
                self.timer_video.start()
                self.label_video_title.setStyleSheet('color:white')
                self.video_status = Ui_MainWindow.STATUS_PLAYING
                Ui_MainWindow.STATUS_SAVE_TEMPLATE = False
                self.status_video_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            elif self.video_status is Ui_MainWindow.STATUS_STOP:
                if self.video_play_flag is False:
                    self.cap = cv2.VideoCapture(0)
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1024)
                else:
                    self.cap = cv2.VideoCapture(self.videos[self.current_video])
                self.timer_video.start()
                self.label_video_title.setStyleSheet('color:white')
                self.video_status = Ui_MainWindow.STATUS_PLAYING
                self.status_video_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else: # 如果是录播模式
            if self.video_status is Ui_MainWindow.STATUS_INIT:
                self.timer_video.start()
                self.last_frame_button.setEnabled(False)
                self.next_frame_button.setEnabled(False)
                self.last_video_button.setEnabled(False)
                self.next_video_button.setEnabled(False)
                self.label_video_title.setStyleSheet('color:white')
                self.video_status = Ui_MainWindow.STATUS_PLAYING
                self.status_video_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
                Ui_MainWindow.STATUS_SAVE_TEMPLATE = False
            elif self.video_status is Ui_MainWindow.STATUS_PLAYING:
                self.timer_video.stop()
                # 暂停后/使能上下一帧
                self.last_frame_button.setEnabled(True)
                self.next_frame_button.setEnabled(True)
                self.last_video_button.setEnabled(True)
                self.next_video_button.setEnabled(True)
                self.video_status = Ui_MainWindow.STATUS_PAUSE
                self.status_video_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
                Ui_MainWindow.STATUS_SAVE_TEMPLATE = True
                self.template_label()
            elif self.video_status is Ui_MainWindow.STATUS_PAUSE:
                self.timer_video.start()
                self.last_frame_button.setEnabled(False)
                self.next_frame_button.setEnabled(False)
                self.last_video_button.setEnabled(False)
                self.next_video_button.setEnabled(False)
                self.label_video_title.setStyleSheet('color:white')
                self.video_status = Ui_MainWindow.STATUS_PLAYING
                self.status_video_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
                Ui_MainWindow.STATUS_SAVE_TEMPLATE = False
            elif self.video_status is Ui_MainWindow.STATUS_STOP:
                self.current_frame = 0
                self.cap = cv2.VideoCapture(self.videos[self.current_video]) # 重新加载这个视频
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
                # 获取视频总帧数
                self.frame_count = int(self.cap.get(7))
                _, self.image = self.cap.read()
                show = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
                show_image = QtGui.QImage(show.data, show.shape[1], show.shape[0], QtGui.QImage.Format_RGB888)
                self.label_video.setPixmap(QtGui.QPixmap.fromImage(show_image))
                self.label_video_title.setStyleSheet('color:white')
                self.label_frame_show.setText(str(self.current_frame+1)+'F/'+str(self.frame_count))
                self.label_frame_show.setStyleSheet('color:white')
                # 设置视频进度滑动条范围
                self.video_progress_bar.setRange(0, self.frame_count-1)
                # 开启视频流
                self.timer_video.start()
                self.last_video_button.setEnabled(False)
                self.next_video_button.setEnabled(False)
                self.last_frame_button.setEnabled(False)
                self.next_frame_button.setEnabled(False)
                self.video_status = Ui_MainWindow.STATUS_PLAYING
                self.status_video_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        self.status_video_button.setEnabled(True)



    # 切换到上个视频
    def last_video(self):
        # 防抖
        self.last_video_button.setEnabled(False)
        if self.video_play_flag is True:
            self.timer_video.stop()
            self.video_status = Ui_MainWindow.STATUS_STOP
            self.status_video_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            if self.current_video > 0:
                self.current_video = self.current_video - 1
            else:
                self.current_video = len(self.videos) - 1
            self.cap = self.videos[self.current_video]
            self.label_video_title.setText('['+str(self.current_video+1)+'/'+str(len(self.videos))+']'
                                           +self.videos_title[self.current_video])
            self.label_video_title.setStyleSheet('color:black')
            self.label_video.setPixmap(QtGui.QPixmap(self.background_file))
            self.last_frame_button.setEnabled(False)
            self.next_frame_button.setEnabled(False)
        self.last_video_button.setEnabled(True)
        self.next_video_button.setEnabled(True)
        self.status_video_button.setEnabled(True)
        # 重置帧数显示位置
        self.current_frame = 0
        self.video_progress_bar.setValue(0)
        self.label_frame_show.setText('')
        self.label_frame_show.setStyleSheet('color:white')
        self.last_video_button.setEnabled(True)

    # 切换到下个视频
    def next_video(self):
        # 防抖
        self.next_video_button.setEnabled(False)
        if self.video_play_flag is True:
            self.timer_video.stop()
            self.video_status = Ui_MainWindow.STATUS_STOP
            self.status_video_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            if self.current_video < len(self.videos) - 1:
                self.current_video = self.current_video + 1
            else:
                self.current_video = 0
            self.cap = self.videos[self.current_video]
            self.label_video_title.setText('['+str(self.current_video+1)+'/'+str(len(self.videos))+']'
                                           +self.videos_title[self.current_video])
            self.label_video_title.setStyleSheet('color:black')
            self.label_video.setPixmap(QtGui.QPixmap(self.background_file))
            self.last_frame_button.setEnabled(False)
            self.next_frame_button.setEnabled(False)
        self.last_video_button.setEnabled(True)
        self.next_video_button.setEnabled(True)
        self.status_video_button.setEnabled(True)
        # 重置帧数显示位置
        self.current_frame = 0
        self.video_progress_bar.setValue(0)
        self.label_frame_show.setText('')
        self.label_frame_show.setStyleSheet('color:white')
        self.next_video_button.setEnabled(True)

    # 切换到上一帧
    def last_frame(self):
        # self.last_frame_button.setEnabled(False)
        if self.current_frame > 0:
            self.current_frame = self.current_frame - 1
        else:
            self.current_frame = 0
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        flag, self.image = self.cap.read()
        if flag is True:
            show = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
            show_image = QtGui.QImage(show.data, show.shape[1], show.shape[0], QtGui.QImage.Format_RGB888)
            self.label_video.setPixmap(QtGui.QPixmap.fromImage(show_image))
            self.label_frame_show.setText(str(self.current_frame+1)+'F/'+str(self.frame_count))
            self.label_frame_show.setStyleSheet('color:white')
            self.video_progress_bar.setValue(self.current_frame)
        else:
            self.cap.release()
            self.video_status = Ui_MainWindow.STATUS_STOP
            self.timer_video.stop()
            self.status_video_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
            self.video_progress_bar.setValue(self.frame_count-1)
        # self.last_frame_button.setEnabled(True)

    # 切换到下一帧
    def next_frame(self):
        # self.next_frame_button.setEnabled(False)
        if self.current_frame < self.frame_count - 1:
            self.current_frame = self.current_frame + 1
        else:
            self.current_frame = self.frame_count - 1
        flag, self.image = self.cap.read()
        if flag is True:
            show = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
            show_image = QtGui.QImage(show.data, show.shape[1], show.shape[0], QtGui.QImage.Format_RGB888)
            self.label_video.setPixmap(QtGui.QPixmap.fromImage(show_image))
            self.label_frame_show.setText(str(self.current_frame+1)+'F/'+str(self.frame_count))
            self.label_frame_show.setStyleSheet('color:white')
            self.video_progress_bar.setValue(self.current_frame)
        else:
            self.cap.release()
            self.video_status = Ui_MainWindow.STATUS_STOP
            self.timer_video.stop()
            self.status_video_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
            self.video_progress_bar.setValue(self.frame_count-1)
        # self.next_frame_button.setEnabled(True)

    # 连接到视频进度栏
    def connect_video_progress_bar(self):
        self.current_frame = self.video_progress_bar.value()
        self.label_frame_show.setText(str(self.current_frame + 1) + 'F/' + str(self.frame_count))
        self.label_frame_show.setStyleSheet('color:white')
        self.slider_flag = True


# 重写窗口关闭
class MainWindow(QMainWindow):
    # 窗口关闭事件
    def closeEvent(self, event):
        reply = QMessageBox.question(self, '本程序', '是否要退出程序?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            cap = cv2.VideoCapture(0)
            cap.release()
            event.accept()
        else:
            event.ignore()


# 视频展示标签
class Video_Label(QLabel):
    x0, y0, x1, y1 = 0, 0, 0, 0
    flag = False
    # 是否右拖动动作标志
    mouseMoveFlag = False

    #鼠标点击事件
    def mousePressEvent(self,event):
        self.flag = True
        self.x0 = event.x()
        self.y0 = event.y()

    #鼠标释放事件
    def mouseReleaseEvent(self,event):
        self.flag = False
        if self.mouseMoveFlag is True:
            self.save_template()
        self.mouseMoveFlag = False


    #鼠标移动事件
    def mouseMoveEvent(self,event):
        if self.flag:
            self.mouseMoveFlag = True
            self.x1 = event.x()
            self.y1 = event.y()
            self.update()

    #绘制事件
    def paintEvent(self, event):
        super().paintEvent(event)
        rect = QRect(self.x0, self.y0, abs(self.x1 - self.x0), abs(self.y1 - self.y0))
        painter = QPainter(self)
        painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
        painter.drawRect(rect)
        # # 如果正常情况下
        # if robotControl.control_robot_flag is False:
        #     rect = QRect(self.x0, self.y0, abs(self.x1 - self.x0), abs(self.y1 - self.y0))
        #     painter = QPainter(self)
        #     painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
        #     painter.drawRect(rect)
        # # 如果控制机械臂情况下
        # else:
        #     if self.mouseMoveFlag is True:
        #         rect = QRect(self.x0, self.y0, abs(self.x1 - self.x0), abs(self.y1 - self.y0))
        #         painter = QPainter(self)
        #         painter.setPen(QPen(Qt.red, 2, Qt.SolidLine))
        #         painter.drawRect(rect)
        #     else:
        #         painter = QPainter(self)
        #         painter.setPen(QPen(Qt.red, 5, Qt.SolidLine))
        #         painter.drawEllipse(self.x0-5, self.y0-5, 10, 10)

    # 保存模板
    def save_template(self):
        if Ui_MainWindow.STATUS_SAVE_TEMPLATE is True:
            x_unit, y_unit = 1280 / 1280, 1024 / 1024
            x0, y0, x1, y1 = int(self.x0 * x_unit), int(self.y0 * y_unit), int(self.x1 * x_unit), int(self.y1 * y_unit)
            cut_img = Ui_MainWindow.IMAGE[y0:y1, x0:x1]
            # 接收模板路径
            mask_path = Ui_MainWindow.MASK_PATH
            # 如果模板路径为None(说明不允许框选模板)
            if mask_path is not None:
                value, ok = QInputDialog.getText(self, '标注输入框', '请输入文本', QLineEdit.Normal, '应用')
                # 如果输入有效值
                if ok:
                    print('框选的模板为: ', value)
                    # 如果是数据处理(需要对图像特殊处理)
                    if Ui_MainWindow.FLAG_DATA_PROCESS is True:
                        # 将模板灰度化/并在模板起始位置打标记
                        rectImage = cv2.cvtColor(cut_img, cv2.COLOR_BGR2GRAY)  # ##灰度化
                        # 在模板起始位置打标记(以便于模板匹配时快速找到模板位置)
                        rectImage[0][0] = y0 // 10
                        rectImage[0][1] = y1 // 10
                        rectImage[0][2] = x0 // 10
                        rectImage[0][3] = x1 // 10
                        cut_img = rectImage
                        # 模板存放位置
                        mask_path = mask_path
                        if os.path.exists(mask_path) is False:
                            os.makedirs(mask_path)
                        cv2.imencode('.jpg', cut_img)[1].tofile(os.path.join(mask_path, value + '.jpg'))
                    # 非数据处理情况
                    else:
                        if '-' in value:
                            folder_layer_count = len(value.split('-')) - 1
                            if folder_layer_count == 1:
                                mask_path = os.path.join(mask_path, value.split('-')[0])
                            elif folder_layer_count == 2:
                                mask_path = os.path.join(mask_path, value.split('-')[0], value.split('-')[1])
                            else:
                                print('[输入的模板名称错误!]')
                                return
                            if os.path.exists(mask_path) is False:
                                os.makedirs(mask_path)
                            if len(value.split('-')[1])==1 and value.split('-')[1].isupper(): # windows文件名大小写一样,此处需要区分(大写如A1.jpg, 小写如a.jpg)
                                cv2.imencode('.jpg', cut_img)[1].tofile(os.path.join(mask_path, value.split('-')[-1] + '1.jpg'))
                            else:
                                cv2.imencode('.jpg', cut_img)[1].tofile(os.path.join(mask_path, value.split('-')[-1] + '.jpg'))
                        else:
                            mask_path = os.path.join(mask_path, '其他')
                            if os.path.exists(mask_path) is False:
                                os.makedirs(mask_path)
                            cv2.imencode('.jpg', cut_img)[1].tofile(os.path.join(mask_path, value + '.jpg'))
                else:
                    print('框选动作取消!')

# 视频显示调用的定时线程
class Communicate(QObject):
    signal = pyqtSignal(str)

# 定时器
class Timer(QThread):
    def __init__(self, frequent=10):
        QThread.__init__(self)
        self.stopped = False
        self.frequent = frequent
        self.timeSignal = Communicate()
        self.mutex = QMutex()
    def run(self):
        with QMutexLocker(self.mutex):
            self.stopped = False
        while True:
            if self.stopped:
                return
            self.timeSignal.signal.emit("1")
            time.sleep(1 / self.frequent)
    def stop(self):
        with QMutexLocker(self.mutex):
            self.stopped = True
    def is_stopped(self):
        with QMutexLocker(self.mutex):
            return self.stopped
    def set_fps(self, fps):
        self.frequent = fps

# 发射控制台内容
class Stream(QObject):
    newText = pyqtSignal(str)
    def write(self, text):
        self.newText.emit(str(text))

if __name__ == "__main__":
    try:
        app = QtWidgets.QApplication(sys.argv)
        # # 默认窗口事件
        # MainWindow = QtWidgets.QMainWindow()
        # # 重写窗口事件
        MainWindow = MainWindow()
        ui = Ui_MainWindow()
        ui.setupUi(MainWindow)
        MainWindow.show()
        # 初始为全屏
        # MainWindow.showMaximized()
        sys.exit(app.exec_())
    except Exception as e:
        print(e)
        time.sleep(600)