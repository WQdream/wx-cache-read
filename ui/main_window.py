#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import datetime
import logging
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QPushButton, QFileDialog, QLineEdit, 
                           QProgressBar, QMessageBox, QInputDialog, QApplication,
                           QTextEdit, QTabWidget, QSplitter, QStackedWidget, 
                           QListWidget, QListWidgetItem, QFrame, QGridLayout,
                           QGroupBox, QFormLayout, QScrollArea, QListView,
                           QCheckBox)
from PyQt5.QtGui import (QIcon, QFont, QPixmap, QTextCursor, QColor, QStandardItemModel, 
                       QStandardItem, QImage, QPainter, QBrush, QPen, QPainterPath)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QByteArray

from utils.wechat_parser import WeChatParser
from ui.custom_dialog import CustomInputDialog, CustomMessageBox

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 应用程序配置文件路径
def get_config_path():
    """获取配置文件路径，存储在用户的AppData目录中"""
    app_name = "微信收藏解析助手"
    if sys.platform == 'win32':
        app_data = os.environ.get('APPDATA', '')
        if not app_data:
            # 如果无法获取APPDATA环境变量，则使用用户目录
            app_data = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Roaming')
        config_dir = os.path.join(app_data, app_name)
    elif sys.platform == 'darwin':  # macOS
        config_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', app_name)
    else:  # Linux和其他Unix系统
        config_dir = os.path.join(os.path.expanduser('~'), '.config', app_name)
    
    # 确保配置目录存在
    if not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir)
        except Exception as e:
            logger.error(f"创建配置目录失败: {str(e)}")
            # 如果无法创建目录，回退到程序运行目录
            return "config.json"
    
    return os.path.join(config_dir, "config.json")

CONFIG_FILE = get_config_path()

# 默认配置
DEFAULT_CONFIG = {
    "cache_path": "",
    "output_path": "",
    "auto_clear_cache": False  # 默认不自动清除缓存
}

class QTextEditLogger(logging.Handler):
    """将日志重定向到QTextEdit的处理器"""
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.widget.setReadOnly(True)
        
    def emit(self, record):
        msg = self.format(record)
        self.widget.append(msg)
        self.widget.moveCursor(QTextCursor.End)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("微信收藏解析工具")
        self.setMinimumSize(1200, 800)  # 增加窗口尺寸
        
        # 加载配置
        self.config = self.load_config()
        
        # 如果配置中没有缓存路径，尝试自动获取
        if not self.config.get("cache_path"):
            self.auto_detect_cache_path()
        
        # 设置样式
        self.setup_style()
        
        # 初始化UI
        self.init_ui()
        
        logger.info("程序启动成功")
        
    def setup_style(self):
        """设置应用程序样式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f7fa;
                color: #333333;
            }
            QLabel {
                font-size: 14px;
                color: #333333;
            }
            QPushButton {
                background-color: #4d8bf0;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                border-radius: 6px;
                min-height: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a7bd5;
            }
            QPushButton:pressed {
                background-color: #2a5db0;
            }
            QPushButton:disabled {
                background-color: #b0b0b0;
                color: #e0e0e0;
            }
            QLineEdit {
                padding: 0px 10px;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                background-color: white;
                color: #333333;
                font-size: 14px;
                min-height: 35px;
                qproperty-alignment: AlignCenter;
            }
            QLineEdit:focus {
                border: 1px solid #4d8bf0;
            }
            QProgressBar {
                border: none;
                border-radius: 6px;
                background-color: #e8e8e8;
                text-align: center;
                min-height: 12px;
                color: #333333;
            }
            QProgressBar::chunk {
                background-color: #4d8bf0;
                border-radius: 6px;
            }
            QListWidget {
                background-color: #3a7bd5;
                border: none;
                outline: none;
                font-size: 15px;
                padding: 10px 0;
                border-radius: 0px 10px 10px 0px;
            }
            QListWidget::item {
                color: white;
                padding: 15px 24px;
                border-left: 3px solid transparent;
                margin-bottom: 5px;
            }
            QListWidget::item:selected {
                background-color: #2a5db0;
                color: white;
                border-left: 3px solid white;
                font-weight: bold;
            }
            QListWidget::item:hover {
                background-color: #4d8bf0;
            }
            QFrame#content {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
                border: 1px solid #e0e0e0;
            }
            QTextEdit {
                font-family: Consolas, Monaco, monospace;
                font-size: 12px;
                padding: 8px;
                background-color: white;
                color: #333333;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
                color: #333333;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QTabWidget::pane {
                border: 1px solid #d0d0d0;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                color: #333333;
                padding: 8px 12px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #4d8bf0;
                color: white;
                font-weight: bold;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #f0f0f0;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
    def init_ui(self):
        """初始化用户界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 左侧菜单
        self.menu_list = QListWidget()
        self.menu_list.setFixedWidth(180)
        self.menu_list.setIconSize(QSize(24, 24))
        
        # 添加菜单项
        menu_items = [
            {"name": "主页", "icon": "home"},
            {"name": "设置", "icon": "settings"},
            {"name": "日志", "icon": "log"},
            {"name": "关于", "icon": "about"}
        ]
        
        for item in menu_items:
            list_item = QListWidgetItem(item["name"])
            self.menu_list.addItem(list_item)
        
        self.menu_list.setCurrentRow(0)
        self.menu_list.currentRowChanged.connect(self.change_page)
        
        # 右侧内容区域
        self.content_stack = QStackedWidget()
        
        # 创建各个页面
        self.create_home_page()
        self.create_settings_page()
        self.create_log_page()
        self.create_about_page()
        
        # 添加到主布局
        main_layout.addWidget(self.menu_list)
        main_layout.addWidget(self.content_stack)
        
    def create_home_page(self):
        """创建主页"""
        home_page = QWidget()
        layout = QVBoxLayout(home_page)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 内容框
        content_frame = QFrame()
        content_frame.setObjectName("content")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(30, 30, 30, 30)  # 减少内边距
        content_layout.setSpacing(15)  # 减少间距
        
        # 标题
        title_label = QLabel("微信收藏解析工具")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 26px; font-weight: bold; color: #4d8bf0; margin-bottom: 5px;")
        content_layout.addWidget(title_label)
        
        # 创建主区域（预览和进度）
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)
        
        # 预览区域标题
        preview_title = QHBoxLayout()
        preview_label = QLabel("文件预览")
        preview_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333333;")
        preview_title.addWidget(preview_label)
        
        # 添加排序说明标签
        self.sort_info_label = QLabel("排序: 等待解析...")
        self.sort_info_label.setStyleSheet("font-size: 12px; color: #666666; margin-left: 10px;")
        preview_title.addWidget(self.sort_info_label)
        
        preview_title.addStretch()

        # 添加排序按钮
        sort_by_time_btn = QPushButton("按时间排序")
        sort_by_time_btn.setFixedWidth(100)
        sort_by_time_btn.clicked.connect(self.sort_by_time)
        sort_by_time_btn.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                border: none;
                padding: 6px 12px;
                font-size: 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4cae4c;
            }
            QPushButton:pressed {
                background-color: #3c8b3c;
            }
        """)
        preview_title.addWidget(sort_by_time_btn)

        # 始终显示清除缓存按钮，不管是否设置了自动清除缓存
        clear_cache_btn = QPushButton("清除缓存")
        clear_cache_btn.setFixedWidth(100)
        clear_cache_btn.clicked.connect(self.clear_cache)
        preview_title.addWidget(clear_cache_btn)

        main_layout.addLayout(preview_title)
        
        # 预览区域（带边框）
        preview_frame = QFrame()
        preview_frame.setFrameShape(QFrame.StyledPanel)
        preview_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                background-color: white;
            }
        """)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(5, 5, 5, 5)  # 减少内边距
        
        # 使用QListWidget显示图片预览
        self.preview_list = QListWidget()
        self.preview_list.setMinimumHeight(300)
        self.preview_list.setIconSize(QSize(130, 130))  # 减小图标尺寸
        self.preview_list.setResizeMode(QListWidget.Adjust)
        self.preview_list.setViewMode(QListWidget.IconMode)  # 使用图标模式
        self.preview_list.setMovement(QListWidget.Static)  # 禁止拖动
        self.preview_list.setWrapping(True)  # 允许换行
        self.preview_list.setSpacing(10)  # 减少图标间距
        self.preview_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: white;
                padding: 2px;
            }
            QListWidget::item {
                background-color: #f9f9f9;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 5px;
                margin: 5px;
                color: black;
            }
            QListWidget::item:hover {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
            }
            QListWidget::item:selected {
                background-color: #e5f1fb;
                border: 1px solid #99c9ef;
            }
        """)
        
        preview_layout.addWidget(self.preview_list)
        main_layout.addWidget(preview_frame, 10)  # 增加权重，使预览区域占据更多空间
        
        # 进度区域
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(5)
        
        # 简化进度区域，减少高度
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(15)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 6px;
                background-color: #e8e8e8;
                text-align: center;
                color: #333333;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #4d8bf0;
                border-radius: 6px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("准备就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #4d8bf0; font-size: 14px;")
        progress_layout.addWidget(self.status_label)
        
        main_layout.addWidget(progress_widget, 1)  # 设置较小的权重
        content_layout.addWidget(main_widget)
        
        # 按钮区域
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 5, 0, 0)
        btn_layout.setSpacing(20)
        
        # 解析按钮
        self.parse_btn = QPushButton("开始解析")
        self.parse_btn.setMinimumHeight(35)
        self.parse_btn.setFixedWidth(150)
        self.parse_btn.clicked.connect(self.start_parsing)
        
        # 保存按钮
        self.save_btn = QPushButton("保存文件")
        self.save_btn.setMinimumHeight(35)
        self.save_btn.setFixedWidth(150)
        self.save_btn.clicked.connect(self.save_parsed_files)
        self.save_btn.setEnabled(False)  # 初始状态为禁用
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.parse_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addStretch()
        
        content_layout.addWidget(btn_widget)
        layout.addWidget(content_frame)
        self.content_stack.addWidget(home_page)
        
    def create_settings_page(self):
        """创建设置页面"""
        settings_page = QWidget()
        layout = QVBoxLayout(settings_page)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 内容框
        content_frame = QFrame()
        content_frame.setObjectName("content")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(30)
        
        # 标题
        title_label = QLabel("设置")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #4d8bf0; margin: 30px 0;")
        content_layout.addWidget(title_label)
        
        # 添加一些空间
        content_layout.addSpacing(30)
        
        # 微信缓存路径设置
        cache_group = QGroupBox("微信缓存路径")
        cache_group.setStyleSheet("QGroupBox { font-size: 16px; margin-top: 30px; }")
        cache_layout = QVBoxLayout(cache_group)
        cache_layout.setContentsMargins(0, 0, 0, 10)
        cache_layout.setAlignment(Qt.AlignCenter)
        
        # 创建水平布局用于输入框和按钮
        cache_input_layout = QHBoxLayout()
        cache_input_layout.setContentsMargins(0, 0, 0, 0)
        cache_input_layout.setSpacing(10)
        
        self.cache_path_edit = QLineEdit()
        self.cache_path_edit.setFixedWidth(400)  # 减小宽度，为自动检测按钮腾出空间
        self.cache_path_edit.setMinimumHeight(35)
        self.cache_path_edit.setPlaceholderText("请选择微信缓存文件夹路径")
        if self.config.get("cache_path"):
            self.cache_path_edit.setText(self.config["cache_path"])
            
        cache_btn = QPushButton("选择路径")
        cache_btn.setMinimumHeight(35)
        cache_btn.setFixedWidth(100)
        cache_btn.clicked.connect(self.select_cache_path)
        
        # 添加自动检测按钮
        auto_detect_btn = QPushButton("自动检测")
        auto_detect_btn.setMinimumHeight(35)
        auto_detect_btn.setFixedWidth(100)
        auto_detect_btn.clicked.connect(self.auto_detect_and_fill)
        auto_detect_btn.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                border: none;
                padding: 8px 16px;
                font-size: 14px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4cae4c;
            }
            QPushButton:pressed {
                background-color: #3c8b3c;
            }
        """)
        
        cache_input_layout.addWidget(self.cache_path_edit)
        cache_input_layout.addWidget(cache_btn)
        cache_input_layout.addWidget(auto_detect_btn)
        
        # 添加到主布局并居中
        cache_center_layout = QHBoxLayout()
        cache_center_layout.addStretch()
        cache_center_layout.addLayout(cache_input_layout)
        cache_center_layout.addStretch()
        
        # 显示当前登录的微信ID
        wxid_layout = QHBoxLayout()
        wxid_label = QLabel("当前登录的微信ID:")
        wxid_label.setStyleSheet("color: #666666; font-size: 12px;")
        
        self.wxid_value = QLabel()
        self.wxid_value.setStyleSheet("color: #333333; font-size: 12px; font-weight: bold;")
        
        # 尝试获取并显示当前登录的wxid
        try:
            wxid = WeChatParser.get_current_wxid()
            if wxid:
                self.wxid_value.setText(wxid)
            else:
                self.wxid_value.setText("未检测到")
        except Exception as e:
            self.wxid_value.setText("检测失败")
            logger.error(f"获取wxid失败: {str(e)}")
        
        wxid_layout.addStretch()
        wxid_layout.addWidget(wxid_label)
        wxid_layout.addWidget(self.wxid_value)
        wxid_layout.addStretch()
        
        cache_layout.addLayout(cache_center_layout)
        cache_layout.addLayout(wxid_layout)
        content_layout.addWidget(cache_group)
        
        # 输出保存路径设置
        output_group = QGroupBox("输出保存路径")
        output_group.setStyleSheet("QGroupBox { font-size: 16px; margin-top: 30px; }")
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(0, 0, 0, 10)
        output_layout.setAlignment(Qt.AlignCenter)
        
        # 创建水平布局用于输入框和按钮
        output_input_layout = QHBoxLayout()
        output_input_layout.setContentsMargins(0, 0, 0, 0)
        output_input_layout.setSpacing(10)
        
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setFixedWidth(500)
        self.output_path_edit.setMinimumHeight(35)
        self.output_path_edit.setPlaceholderText("请选择输出保存文件夹路径")
        if self.config.get("output_path"):
            self.output_path_edit.setText(self.config["output_path"])
            
        output_btn = QPushButton("选择路径")
        output_btn.setMinimumHeight(35)
        output_btn.setFixedWidth(100)
        output_btn.clicked.connect(self.select_output_path)
        
        output_input_layout.addWidget(self.output_path_edit)
        output_input_layout.addWidget(output_btn)
        
        # 添加到主布局并居中
        output_center_layout = QHBoxLayout()
        output_center_layout.addStretch()
        output_center_layout.addLayout(output_input_layout)
        output_center_layout.addStretch()
        
        output_layout.addLayout(output_center_layout)
        content_layout.addWidget(output_group)
        
        # 缓存设置
        cache_settings_group = QGroupBox("缓存设置")
        cache_settings_group.setStyleSheet("QGroupBox { font-size: 16px; margin-top: 30px; }")
        cache_settings_layout = QVBoxLayout(cache_settings_group)
        cache_settings_layout.setContentsMargins(0, 0, 0, 10)
        cache_settings_layout.setAlignment(Qt.AlignCenter)

        # 创建水平布局用于复选框
        cache_settings_input_layout = QHBoxLayout()
        cache_settings_input_layout.setContentsMargins(0, 0, 0, 0)
        cache_settings_input_layout.setSpacing(10)

        # 创建复选框
        self.auto_clear_checkbox = QCheckBox("保存文件后自动清除缓存")
        self.auto_clear_checkbox.setStyleSheet("font-size: 14px;")
        self.auto_clear_checkbox.setMinimumHeight(35)  # 与其他输入框保持一致的高度
        self.auto_clear_checkbox.setChecked(self.config.get("auto_clear_cache", False))

        cache_settings_input_layout.addWidget(self.auto_clear_checkbox)
        cache_settings_input_layout.addStretch()

        # 添加到主布局并居中
        cache_settings_center_layout = QHBoxLayout()
        cache_settings_center_layout.addStretch()
        cache_settings_center_layout.addLayout(cache_settings_input_layout)
        cache_settings_center_layout.addStretch()

        # 添加描述文本
        cache_settings_desc = QLabel("开启后，每次保存文件完成将自动清除微信缓存文件并清空预览列表")
        cache_settings_desc.setStyleSheet("color: #666666; font-size: 12px;")
        cache_settings_desc.setAlignment(Qt.AlignCenter)

        # 描述文本居中布局
        desc_center_layout = QHBoxLayout()
        desc_center_layout.addStretch()
        desc_center_layout.addWidget(cache_settings_desc)
        desc_center_layout.addStretch()

        cache_settings_layout.addLayout(cache_settings_center_layout)
        cache_settings_layout.addLayout(desc_center_layout)
        content_layout.addWidget(cache_settings_group)
        
        # 添加一些空间
        content_layout.addSpacing(30)
        
        # 保存设置按钮
        save_btn = QPushButton("保存设置")
        save_btn.setMinimumHeight(50)
        save_btn.setFixedWidth(200)
        save_btn.clicked.connect(self.save_settings)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        
        content_layout.addLayout(btn_layout)
        content_layout.addStretch()
        
        layout.addWidget(content_frame)
        self.content_stack.addWidget(settings_page)
        
    def create_log_page(self):
        """创建日志页面"""
        log_page = QWidget()
        layout = QVBoxLayout(log_page)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 内容框
        content_frame = QFrame()
        content_frame.setObjectName("content")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(30)
        
        # 标题
        title_label = QLabel("运行日志")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #4d8bf0; margin: 30px 0;")
        content_layout.addWidget(title_label)
        
        # 添加一些空间
        content_layout.addSpacing(30)
        
        # 日志显示区域
        self.log_text = QTextEdit()
        self.log_text.setMinimumHeight(350)
        content_layout.addWidget(self.log_text)
        
        # 设置日志处理器
        log_handler = QTextEditLogger(self.log_text)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(log_handler)
        
        # 添加一些空间
        content_layout.addSpacing(20)
        
        # 清除日志按钮
        clear_btn = QPushButton("清除日志")
        clear_btn.setMinimumHeight(40)
        clear_btn.setFixedWidth(150)
        clear_btn.clicked.connect(self.log_text.clear)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(clear_btn)
        
        content_layout.addLayout(btn_layout)
        
        layout.addWidget(content_frame)
        self.content_stack.addWidget(log_page)
    
    def create_about_page(self):
        """创建关于页面"""
        about_page = QWidget()
        layout = QVBoxLayout(about_page)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # 内容框
        content_frame = QFrame()
        content_frame.setObjectName("content")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(30)
        
        # 标题
        title_label = QLabel("关于")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #4d8bf0;")
        content_layout.addWidget(title_label)
        
        # 添加一些空间
        content_layout.addSpacing(20)
        
        # 关于文本
        about_text = """
        <h2 style="color: #333333; text-align: center;">微信收藏解析工具</h2>
        <p style="font-size: 16px; line-height: 1.6; color: #333333; text-align: center;">
        一款简单易用的工具，帮助ymh摸鱼
        </p>
        
        <h3 style="color: #4d8bf0; margin-top: 25px;">软件特点</h3>
        <ul style="font-size: 15px; line-height: 1.6; color: #333333;">
            <li><b>自动检测</b> - 智能识别当前登录微信用户的收藏路径</li>
            <li><b>批量解析</b> - 一键解析微信收藏中的图片和视频资源</li>
            <li><b>智能排序</b> - 尽可能保持与微信收藏笔记中相同的图片顺序</li>
            <li><b>预览功能</b> - 直观展示解析出的文件，方便筛选</li>
            <li><b>手动排序</b> - 支持按时间重新排序，调整文件顺序</li>
            <li><b>自定义保存</b> - 可自定义保存路径和文件夹名称</li>
            <li><b>缓存管理</b> - 可选择是否在保存后自动清除缓存</li>
            <li><b>日志记录</b> - 详细记录运行过程，便于排查问题</li>
        </ul>
        
        <h3 style="color: #4d8bf0; margin-top: 25px;">使用步骤</h3>
        <ol style="font-size: 15px; line-height: 1.6; color: #333333;">
            <li>在<b>设置</b>页面配置微信缓存路径（可点击"自动检测"按钮）</li>
            <li>设置输出保存路径，选择文件保存的位置</li>
            <li>选择是否在保存后自动清除缓存</li>
            <li>保存设置后，返回<b>主页</b></li>
            <li>点击"开始解析"按钮，解析缓存中的文件</li>
            <li>在预览列表中查看解析出的文件</li>
            <li>点击"保存文件"按钮将文件保存到指定位置</li>
            <li>输入自定义文件夹名称（留空则自动使用数字命名）</li>
            <li>等待保存完成</li>
            <li>如需清除缓存，可点击"清除缓存"按钮</li>
        </ol>
        
        <h3 style="color: #4d8bf0; margin-top: 25px;">🎯 图片排序功能</h3>
        <p style="font-size: 14px; line-height: 1.5; color: #333333;">
        为了解决图片顺序与微信收藏笔记不一致的问题，软件实现了智能排序功能：
        </p>
        
        <h4 style="color: #5cb85c; margin-top: 15px; margin-bottom: 10px;">排序策略（按优先级）</h4>
        <ul style="font-size: 14px; line-height: 1.5; color: #333333; margin-left: 20px;">
            <li><b style="color: #5cb85c;">数据库排序（最佳）</b> - 从微信数据库获取原始顺序信息，最接近收藏笔记顺序</li>
            <li><b style="color: #f0ad4e;">时间排序（良好）</b> - 基于文件修改时间排序，通常反映添加到收藏的顺序</li>
            <li><b style="color: #d9534f;">默认排序（一般）</b> - 使用文件系统默认遍历顺序</li>
        </ul>
        
        <h4 style="color: #5cb85c; margin-top: 15px; margin-bottom: 10px;">使用方法</h4>
        <ol style="font-size: 14px; line-height: 1.5; color: #333333; margin-left: 20px;">
            <li>解析完成后，查看预览区域的排序状态标签</li>
            <li>绿色表示最佳排序，橙色表示良好排序，红色表示一般排序</li>
            <li>如果排序效果不理想，可点击"按时间排序"按钮手动调整</li>
            <li>保存文件时会保持当前的排序顺序</li>
        </ol>
        
        <h3 style="color: #4d8bf0; margin-top: 25px;">常见问题</h3>
        <p style="font-size: 15px; font-weight: bold; color: #333333;">1. 如何找到微信缓存路径？</p>
        <p style="font-size: 14px; line-height: 1.5; color: #333333; margin-left: 20px;">
        点击"自动检测"按钮，软件会自动查找当前登录微信用户的收藏路径。<br>
        如果自动检测失败，通常可以在以下位置找到：<br>
        - C:\\Users\\用户名\\Documents\\WeChat Files\\微信号\\FileStorage\\Favorites<br>
        - C:\\Users\\用户名\\Documents\\WeChat Files\\微信号\\FileStorage\\Fav
        </p>
        
        <p style="font-size: 15px; font-weight: bold; color: #333333;">2. 图片顺序是如何确定的？</p>
        <p style="font-size: 14px; line-height: 1.5; color: #333333; margin-left: 20px;">
        软件会尝试多种方式来保持与微信收藏笔记中相同的图片顺序：<br>
        - <b style="color: #5cb85c;">数据库排序（最佳）</b>：从微信数据库中获取原始顺序信息<br>
        - <b style="color: #f0ad4e;">时间排序（良好）</b>：按文件修改时间排序，通常反映添加到收藏的顺序<br>
        - <b style="color: #d9534f;">默认排序（一般）</b>：按文件系统顺序排列<br>
        解析完成后，状态栏会显示当前使用的排序方式。如果顺序不理想，可以点击"按时间排序"按钮重新排序。
        </p>
        
        <p style="font-size: 15px; font-weight: bold; color: #333333;">3. 为什么有些文件无法解析？</p>
        <p style="font-size: 14px; line-height: 1.5; color: #333333; margin-left: 20px;">
        目前支持解析的文件类型包括：jpg、jpeg、png、gif、bmp、webp、mp4、mov、avi、mkv、wmv、flv。<br>
        其他类型的文件可能无法正确解析和预览。
        </p>
        
        <p style="font-size: 15px; font-weight: bold; color: #333333;">4. 清除缓存会删除哪些文件？</p>
        <p style="font-size: 14px; line-height: 1.5; color: #333333; margin-left: 20px;">
        清除缓存只会删除微信缓存路径下的图片和视频文件，不会影响微信的正常使用。<br>
        建议在确认文件已成功保存后再清除缓存。
        </p>
        
        <h3 style="color: #4d8bf0; margin-top: 25px;">技术支持</h3>
        <p style="font-size: 14px; line-height: 1.5; color: #333333;">
        如果您在使用过程中遇到任何问题，可以查看<b>日志</b>页面获取详细信息，或联系开发者获取支持。
        </p>
        
        <h3 style="color: #4d8bf0; margin-top: 25px;">更新日志</h3>
        <p style="font-size: 14px; line-height: 1.5; color: #333333;">
        <b>v1.2.0 (2025年7月)</b><br>
        ✨ 新增智能图片排序功能，尽可能保持与微信收藏笔记中相同的顺序<br>
        ✨ 新增手动排序功能，支持按时间重新排序<br>
        ✨ 新增排序状态显示，实时反馈当前排序策略<br>
        🔧 优化数据库查询，支持多种排序字段<br>
        🔧 改进文件系统排序，基于修改时间精确排序<br>
        📝 完善日志记录，详细显示排序过程信息
        </p>
        
        <p style="font-size: 14px; line-height: 1.6; color: #333333; margin-top: 30px; text-align: center;">
        版本：1.2.0<br>
        开发者：小新<br>
        最后更新：2025年7月
        </p>
        """
        
        # 使用QTextEdit显示关于文本
        about_textEdit = QTextEdit()
        about_textEdit.setHtml(about_text)
        about_textEdit.setReadOnly(True)
        about_textEdit.setStyleSheet("border: none; background-color: transparent;")
        
        # 设置更大的高度以显示更多内容
        about_textEdit.setMinimumHeight(500)
        
        # 滚动到顶部
        about_textEdit.moveCursor(QTextCursor.Start)
        
        content_layout.addWidget(about_textEdit)
        
        layout.addWidget(content_frame)
        self.content_stack.addWidget(about_page)
    
    def change_page(self, index):
        """切换页面"""
        self.content_stack.setCurrentIndex(index)
        
    def select_cache_path(self):
        """选择微信缓存路径"""
        path = QFileDialog.getExistingDirectory(self, "选择微信缓存文件夹")
        if path:
            self.cache_path_edit.setText(path)
            logger.info(f"已选择微信缓存路径: {path}")
    
    def select_output_path(self):
        """选择输出保存路径"""
        path = QFileDialog.getExistingDirectory(self, "选择输出保存文件夹")
        if path:
            self.output_path_edit.setText(path)
            logger.info(f"已选择输出保存路径: {path}")
    
    def save_settings(self):
        """保存设置"""
        cache_path = self.cache_path_edit.text()
        output_path = self.output_path_edit.text()
        auto_clear_cache = self.auto_clear_checkbox.isChecked()
        
        if not cache_path:
            CustomMessageBox.warning(self, "警告", "请选择微信缓存文件夹路径")
            return
        
        if not output_path:
            CustomMessageBox.warning(self, "警告", "请选择输出保存文件夹路径")
            return
        
        # 更新配置
        self.config["cache_path"] = cache_path
        self.config["output_path"] = output_path
        self.config["auto_clear_cache"] = auto_clear_cache
        
        # 保存配置到文件
        self.save_config()
        
        CustomMessageBox.information(self, "成功", "设置已保存")
        logger.info("设置已保存")
    
    def start_parsing(self):
        """开始解析微信收藏"""
        cache_path = self.config.get("cache_path", "")
        
        if not cache_path:
            CustomMessageBox.warning(self, "警告", "请先在设置页面配置微信缓存路径")
            self.menu_list.setCurrentRow(1)  # 切换到设置页面
            return
        
        # 检查缓存路径是否存在
        if not os.path.exists(cache_path):
            CustomMessageBox.critical(self, "错误", f"微信缓存路径不存在: {cache_path}")
            return
        
        # 清空预览列表
        self.preview_list.clear()
        # 禁用保存按钮
        self.save_btn.setEnabled(False)
        # 重置进度条
        self.progress_bar.setValue(0)
        
        # 创建解析线程
        try:
            self.parser_thread = ParserThread(cache_path, None, preview_only=True)
            self.parser_thread.progress_updated.connect(self.update_progress)
            self.parser_thread.status_updated.connect(self.update_status)
            self.parser_thread.error_occurred.connect(self.show_error)
            self.parser_thread.finished.connect(self.parsing_finished)
            self.parser_thread.file_found.connect(self.add_file_to_preview)
            
            # 禁用按钮
            self.parse_btn.setEnabled(False)
            self.status_label.setText("正在解析中...")
            
            # 启动线程
            self.parser_thread.start()
            logger.info("解析线程已启动")
            
        except Exception as e:
            CustomMessageBox.critical(self, "错误", f"启动解析线程失败: {str(e)}")
            logger.error(f"启动解析线程失败: {str(e)}")
            
    def parsing_finished(self):
        """解析完成"""
        self.parse_btn.setEnabled(True)
        # 如果有文件被解析，启用保存按钮
        if self.preview_list.count() > 0:
            self.save_btn.setEnabled(True)
            
            # 获取排序策略信息
            try:
                cache_path = self.config.get("cache_path", "")
                if cache_path:
                    parser = WeChatParser(cache_path)
                    sort_info = parser.get_sorting_strategy_info()
                    self.status_label.setText(f"解析完成，找到 {self.preview_list.count()} 个文件")
                    
                    # 更新排序信息标签
                    if "数据库排序" in sort_info:
                        self.sort_info_label.setText("排序: 数据库顺序（最佳）")
                        self.sort_info_label.setStyleSheet("font-size: 12px; color: #5cb85c; margin-left: 10px; font-weight: bold;")
                    elif "时间排序" in sort_info:
                        self.sort_info_label.setText("排序: 时间顺序（良好）")
                        self.sort_info_label.setStyleSheet("font-size: 12px; color: #f0ad4e; margin-left: 10px; font-weight: bold;")
                    else:
                        self.sort_info_label.setText("排序: 默认顺序（一般）")
                        self.sort_info_label.setStyleSheet("font-size: 12px; color: #d9534f; margin-left: 10px; font-weight: bold;")
                else:
                    self.status_label.setText(f"解析完成，找到 {self.preview_list.count()} 个文件")
                    self.sort_info_label.setText("排序: 未知")
            except Exception as e:
                logger.warning(f"获取排序信息失败: {str(e)}")
                self.status_label.setText(f"解析完成，找到 {self.preview_list.count()} 个文件")
                self.sort_info_label.setText("排序: 未知")
        else:
            self.status_label.setText("解析完成，未找到文件")
            self.sort_info_label.setText("排序: 无文件")
        logger.info("解析完成")
        
    def saving_finished(self):
        """保存完成"""
        self.parse_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.status_label.setText("文件保存完成")
        CustomMessageBox.information(self, "完成", "文件保存完成！")
        logger.info("保存完成")
        
        # 如果配置了自动清除缓存，则在保存完成后清除缓存
        if self.config.get("auto_clear_cache", False):
            self.clear_cache(auto_mode=True)
    
    def add_file_to_preview(self, file_info):
        """将文件添加到预览列表，显示图片预览"""
        try:
            # 创建一个列表项
            item = QListWidgetItem()
            item.setData(Qt.UserRole, file_info)  # 存储文件信息
            
            # 根据文件类型加载预览
            file_path = file_info['path']
            file_name = file_info['name']
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # 图片文件预览
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    item.setIcon(QIcon(pixmap))
                    # 只显示文件名，不显示类型标识
                    item.setText(file_name)
                else:
                    # 如果无法加载图片，使用默认文本
                    item.setText(f"{file_name}\n[图片]")
            # 视频文件预览
            elif file_ext in ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv']:
                item.setText(f"{file_name}\n[视频]")
            # 其他文件预览
            else:
                item.setText(f"{file_name}\n[文件]")
            
            # 设置文本对齐
            item.setTextAlignment(Qt.AlignCenter)
            # 设置项目大小 - 为图片和文本预留足够空间
            item.setSizeHint(QSize(190, 210))
            
            # 添加到列表
            self.preview_list.addItem(item)
            
        except Exception as e:
            logger.error(f"添加预览时出错: {str(e)}")
            # 如果出错，仍然添加一个简单的项目
            simple_item = QListWidgetItem(file_info['name'])
            simple_item.setData(Qt.UserRole, file_info)
            self.preview_list.addItem(simple_item)

            
    
    def save_parsed_files(self):
        """保存已解析的文件"""
        # 检查是否有文件可供保存
        if self.preview_list.count() == 0:
            CustomMessageBox.information(self, "提示", "没有可保存的文件")
            return
        
        output_path = self.config.get("output_path", "")
        if not output_path:
            CustomMessageBox.warning(self, "警告", "请先在设置页面配置输出保存路径")
            self.menu_list.setCurrentRow(1)  # 切换到设置页面
            return
            
        # 检查输出路径是否存在
        if not os.path.exists(output_path):
            try:
                os.makedirs(output_path)
                logger.info(f"创建输出路径: {output_path}")
            except Exception as e:
                CustomMessageBox.critical(self, "错误", f"无法创建输出路径: {str(e)}")
                return
        
        # 获取用户输入的文件夹名称或使用递增数字
        folder_name, ok = CustomInputDialog.get_text_input(self, "文件夹命名", "请输入保存文件夹名称:")
        
        # 用户点击了关闭按钮或取消按钮，直接取消保存操作
        if not ok:
            logger.info("用户取消了文件夹命名，取消保存操作")
            return
        
        # 创建当前日期的文件夹
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        date_folder = os.path.join(output_path, today)
        
        # 如果用户输入为空，使用自动递增的数字
        if not folder_name.strip():
            # 获取现有文件夹中的数字命名文件夹
            folder_name = self.get_next_folder_number(date_folder)
            logger.info(f"用户输入为空，将使用自动编号: {folder_name}")
            
            # 输出更详细的日志，帮助调试
            if not os.path.exists(date_folder):
                logger.info(f"日期文件夹不存在，将创建: {date_folder}")
            else:
                existing_folders = [f for f in os.listdir(date_folder) 
                               if os.path.isdir(os.path.join(date_folder, f))]
                logger.info(f"日期文件夹已存在，包含以下子文件夹: {existing_folders}")
        
        # 确定最终保存路径
        save_folder = os.path.join(date_folder, folder_name)
        
        # 如果文件夹已存在，询问用户
        if os.path.exists(save_folder):
            reply = CustomMessageBox.question(
                self, 
                "文件夹已存在", 
                f"文件夹 '{folder_name}' 已存在。\n是否使用新的名称？"
            )
            
            if reply == CustomMessageBox.Yes:
                # 用户选择使用新名称，递归调用本方法
                self.save_parsed_files()
                return
            elif reply == CustomMessageBox.Cancel:
                # 用户取消操作
                return
            # 如果选择No，继续使用已有文件夹
        
        # 创建当前日期的文件夹
        try:
            if not os.path.exists(date_folder):
                os.makedirs(date_folder)
                logger.info(f"创建日期文件夹: {date_folder}")
        except Exception as e:
            CustomMessageBox.critical(self, "错误", f"无法创建日期文件夹: {str(e)}")
            return
        
        # 创建用户命名的文件夹（如果不存在）
        try:
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)
                logger.info(f"创建保存文件夹: {save_folder}")
        except Exception as e:
            CustomMessageBox.critical(self, "错误", f"无法创建保存文件夹: {str(e)}")
            return
        
        # 创建保存线程
        try:
            # 获取所有文件信息
            files_to_save = []
            for i in range(self.preview_list.count()):
                item = self.preview_list.item(i)
                file_info = item.data(Qt.UserRole)
                files_to_save.append(file_info)
            
            self.save_thread = SaveThread(files_to_save, save_folder)
            self.save_thread.progress_updated.connect(self.update_progress)
            self.save_thread.status_updated.connect(self.update_status)
            self.save_thread.error_occurred.connect(self.show_error)
            self.save_thread.finished.connect(self.saving_finished)
            
            # 禁用按钮
            self.parse_btn.setEnabled(False)
            self.save_btn.setEnabled(False)
            self.status_label.setText("正在保存文件...")
            self.progress_bar.setValue(0)
            
            # 启动线程
            self.save_thread.start()
            logger.info("保存线程已启动")
            
            # 不再切换到日志页面
        except Exception as e:
            CustomMessageBox.critical(self, "错误", f"启动保存线程失败: {str(e)}")
            logger.error(f"启动保存线程失败: {str(e)}")
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def update_status(self, message):
        """更新状态信息"""
        self.status_label.setText(message)
        logger.info(message)
    
    def show_error(self, message):
        """显示错误信息"""
        CustomMessageBox.critical(self, "错误", message)
        logger.error(message)
        self.parse_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
    
    def load_config(self):
        """加载配置"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # 使用默认配置补充缺失的配置项
                    for key, value in DEFAULT_CONFIG.items():
                        if key not in config:
                            config[key] = value
                    return config
            except Exception as e:
                logger.error(f"加载配置文件失败: {str(e)}")
        return DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """保存配置"""
        try:
            # 确保配置文件目录存在
            config_dir = os.path.dirname(CONFIG_FILE)
            if not os.path.exists(config_dir) and config_dir:  # 确保config_dir不为空
                os.makedirs(config_dir)
                
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            logger.info(f"配置已保存到: {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
            CustomMessageBox.warning(self, "警告", f"保存配置文件失败: {str(e)}")
            
    def get_next_folder_number(self, parent_folder):
        """获取下一个可用的数字文件夹名"""
        # 确保父文件夹存在
        if not os.path.exists(parent_folder):
            os.makedirs(parent_folder)
            return "1"
        
        # 获取所有文件夹
        folders = [f for f in os.listdir(parent_folder) 
                  if os.path.isdir(os.path.join(parent_folder, f))]
        
        # 筛选出纯数字命名的文件夹
        number_folders = []
        for folder in folders:
            if folder.isdigit():
                number_folders.append(int(folder))
        
        # 如果没有数字文件夹，返回"1"
        if not number_folders:
            return "1"
        
        # 否则返回最大数字+1
        return str(max(number_folders) + 1)

    def clear_cache(self, auto_mode=False):
        """清除缓存"""
        # 如果不是自动模式，则显示确认对话框
        if not auto_mode:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("清除缓存")
            msg_box.setText("确定要清除所有缓存吗？这将删除微信缓存中的图片和视频，并清空预览。")
            msg_box.setIcon(QMessageBox.Question)
            
            # 只添加"是"和"否"按钮
            yes_btn = msg_box.addButton("是", QMessageBox.YesRole)
            no_btn = msg_box.addButton("否", QMessageBox.NoRole)
            
            # 设置按钮样式
            yes_btn.setMinimumWidth(100)
            yes_btn.setMinimumHeight(35)
            yes_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4d8bf0;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    font-size: 14px;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #3a7bd5;
                }
                QPushButton:pressed {
                    background-color: #2a5db0;
                }
            """)
            
            no_btn.setMinimumWidth(100)
            no_btn.setMinimumHeight(35)
            no_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    color: #333333;
                    border: 1px solid #d0d0d0;
                    padding: 8px 16px;
                    font-size: 14px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
                QPushButton:pressed {
                    background-color: #d0d0d0;
                }
            """)
            
            # 显示对话框
            msg_box.exec_()
            
            # 如果点击的是"否"按钮，则返回
            if msg_box.clickedButton() == no_btn:
                return
        
        # 清空预览列表
        self.preview_list.clear()
        self.save_btn.setEnabled(False)
        
        # 重置进度条和排序信息
        self.progress_bar.setValue(0)
        self.sort_info_label.setText("排序: 等待解析...")
        self.sort_info_label.setStyleSheet("font-size: 12px; color: #666666; margin-left: 10px;")
        
        # 清除微信缓存文件
        cache_path = self.config.get("cache_path", "")
        if cache_path and os.path.exists(cache_path):
            try:
                # 图片和视频文件扩展名
                media_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', 
                                  '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv']
                
                # 查找要删除的文件
                files_to_delete = []
                for root, _, files in os.walk(cache_path):
                    for file in files:
                        file_ext = os.path.splitext(file)[1].lower()
                        if file_ext in media_extensions:
                            files_to_delete.append(os.path.join(root, file))
                
                if not files_to_delete:
                    self.status_label.setText("没有找到可删除的缓存文件")
                    logger.info("没有找到可删除的缓存文件")
                    return
                
                # 删除文件
                deleted_count = 0
                for file_path in files_to_delete:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            deleted_count += 1
                    except Exception as e:
                        logger.warning(f"删除文件失败: {file_path}, 错误: {str(e)}")
                
                self.status_label.setText(f"缓存清除完成，已删除 {deleted_count} 个文件")
                logger.info(f"缓存清除完成，已删除 {deleted_count} 个文件")
                
            except Exception as e:
                error_msg = f"清除缓存出错: {str(e)}"
                if not auto_mode:  # 自动模式下不显示错误提示
                    CustomMessageBox.critical(self, "错误", error_msg)
                logger.error(error_msg)
        else:
            self.status_label.setText("缓存已清除")
            logger.info("缓存已清除")

    def auto_detect_cache_path(self):
        """自动检测微信缓存路径"""
        try:
            # 获取微信收藏路径
            favorites_path = WeChatParser.get_favorites_path()
            if favorites_path:
                self.config["cache_path"] = favorites_path
                logger.info(f"自动检测到微信缓存路径: {favorites_path}")
                self.save_config()
        except Exception as e:
            logger.error(f"自动检测微信缓存路径失败: {str(e)}")

    def auto_detect_and_fill(self):
        """自动检测并填充微信缓存路径"""
        try:
            # 获取微信收藏路径
            favorites_path = WeChatParser.get_favorites_path()
            if favorites_path:
                self.cache_path_edit.setText(favorites_path)
                CustomMessageBox.information(self, "成功", f"已自动检测到微信缓存路径:\n{favorites_path}")
                logger.info(f"自动检测到微信缓存路径: {favorites_path}")
            else:
                CustomMessageBox.warning(self, "警告", "无法自动检测到微信缓存路径，请手动选择")
                logger.warning("无法自动检测到微信缓存路径")
        except Exception as e:
            CustomMessageBox.critical(self, "错误", f"自动检测微信缓存路径失败: {str(e)}")
            logger.error(f"自动检测微信缓存路径失败: {str(e)}")
    
    def sort_by_time(self):
        """按时间重新排序预览列表"""
        if self.preview_list.count() == 0:
            CustomMessageBox.information(self, "提示", "没有可排序的文件")
            return
        
        try:
            # 获取所有文件信息
            files_with_time = []
            for i in range(self.preview_list.count()):
                item = self.preview_list.item(i)
                file_info = item.data(Qt.UserRole)
                
                # 获取文件修改时间
                try:
                    mtime = os.path.getmtime(file_info['path'])
                except:
                    mtime = 0
                
                # 保存必要的显示信息，而不是保存item对象
                files_with_time.append({
                    'file_info': file_info,
                    'mtime': mtime,
                    'text': item.text(),
                    'icon': item.icon(),
                    'size_hint': item.sizeHint()
                })
            
            # 按修改时间排序
            files_with_time.sort(key=lambda x: x['mtime'])
            
            # 清空列表并重新添加
            self.preview_list.clear()
            for file_data in files_with_time:
                # 重新创建列表项
                item = QListWidgetItem()
                item.setData(Qt.UserRole, file_data['file_info'])
                item.setText(file_data['text'])
                item.setIcon(file_data['icon'])
                item.setTextAlignment(Qt.AlignCenter)
                item.setSizeHint(file_data['size_hint'])
                
                self.preview_list.addItem(item)
            
            # 更新排序信息
            self.sort_info_label.setText("排序: 按时间排序（手动）")
            self.sort_info_label.setStyleSheet("font-size: 12px; color: #f0ad4e; margin-left: 10px; font-weight: bold;")
            self.status_label.setText(f"已按时间重新排序 {self.preview_list.count()} 个文件")
            logger.info("手动按时间排序完成")
            
        except Exception as e:
            CustomMessageBox.critical(self, "错误", f"排序失败: {str(e)}")
            logger.error(f"排序失败: {str(e)}")


class ParserThread(QThread):
    """解析线程"""
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    file_found = pyqtSignal(dict)
    
    def __init__(self, cache_path, save_folder, preview_only=False):
        super().__init__()
        self.cache_path = cache_path
        self.save_folder = save_folder
        self.preview_only = preview_only
        self.parsed_files = []
        
    def run(self):
        """执行解析任务"""
        try:
            # 初始化解析器
            self.status_updated.emit("正在初始化解析器...")
            parser = WeChatParser(self.cache_path)
            
            # 获取文件总数
            self.status_updated.emit("正在获取文件列表...")
            total_files = parser.get_total_files()
            
            if total_files == 0:
                self.status_updated.emit("未找到可解析的文件")
                self.error_occurred.emit("未找到可解析的文件，请检查微信缓存路径是否正确")
                return
            
            self.status_updated.emit(f"找到 {total_files} 个文件，开始解析...")
            
            # 解析文件
            saved_count = 0
            for i, file_info in enumerate(parser.parse_favorites()):
                progress = int((i + 1) / total_files * 100)
                self.progress_updated.emit(progress)
                
                if self.preview_only:
                    self.status_updated.emit(f"正在解析: {file_info['name']} ({i+1}/{total_files})")
                    # 发送文件信息信号
                    self.file_found.emit(file_info)
                    self.parsed_files.append(file_info)
                else:
                    self.status_updated.emit(f"正在保存: {file_info['name']} ({i+1}/{total_files})")
                    # 保存文件
                    if parser.save_file(file_info, self.save_folder):
                        saved_count += 1
            
            if self.preview_only:
                self.status_updated.emit(f"解析完成，已找到 {len(self.parsed_files)} 个文件")
            else:
                self.status_updated.emit(f"解析完成，已保存 {saved_count}/{total_files} 个文件")
            
        except Exception as e:
            import traceback
            error_msg = f"解析出错: {str(e)}\n{traceback.format_exc()}"
            self.error_occurred.emit(error_msg)
            logger.error(error_msg)


class SaveThread(QThread):
    """保存文件线程"""
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, files, save_folder):
        super().__init__()
        self.files = files
        self.save_folder = save_folder
        self.cache_path = ""  # 存储缓存路径
        if files and len(files) > 0:
            # 从文件路径中提取缓存根目录，而不是使用完整文件路径
            file_path = files[0]['path']
            # 查找FileStorage/Fav或者Favorites目录
            if "FileStorage/Fav" in file_path.replace("\\", "/"):
                parts = file_path.replace("\\", "/").split("FileStorage/Fav")
                self.cache_path = parts[0] + "FileStorage/Fav"
            elif "Favorites" in file_path.replace("\\", "/"):
                parts = file_path.replace("\\", "/").split("Favorites")
                self.cache_path = parts[0] + "Favorites"
            else:
                # 如果无法找到明确的路径，使用文件所在目录
                self.cache_path = os.path.dirname(file_path)
        
    def run(self):
        """执行保存任务"""
        try:
            # 如果没有缓存路径，直接复制文件方式保存
            if not self.cache_path:
                self.save_files_directly()
                return
                
            # 初始化解析器 - 传入缓存路径而不是文件路径
            self.status_updated.emit("正在初始化...")
            try:
                parser = WeChatParser(self.cache_path)
                self.save_files_with_parser(parser)
            except Exception as e:
                # 如果使用解析器失败，回退到直接复制文件
                self.status_updated.emit(f"初始化解析器失败，使用直接复制方式: {str(e)}")
                self.save_files_directly()
            
        except Exception as e:
            import traceback
            error_msg = f"保存出错: {str(e)}\n{traceback.format_exc()}"
            self.error_occurred.emit(error_msg)
            logger.error(error_msg)
            
    def save_files_with_parser(self, parser):
        """使用解析器保存文件"""
        total_files = len(self.files)
        if total_files == 0:
            self.status_updated.emit("没有可保存的文件")
            return
        
        self.status_updated.emit(f"开始保存 {total_files} 个文件...")
        
        # 计算序号的位数，确保排序正确
        num_digits = len(str(total_files))
        
        # 保存文件
        saved_count = 0
        for i, file_info in enumerate(self.files):
            progress = int((i + 1) / total_files * 100)
            self.progress_updated.emit(progress)
            self.status_updated.emit(f"正在保存: {file_info['name']} ({i+1}/{total_files})")
            
            # 添加序号信息到文件信息中
            sequence_number = str(i + 1).zfill(num_digits)
            file_info_with_sequence = file_info.copy()
            file_info_with_sequence['sequence'] = sequence_number
            
            # 保存文件
            if parser.save_file_with_sequence(file_info_with_sequence, self.save_folder):
                saved_count += 1
        
        self.status_updated.emit(f"保存完成，已保存 {saved_count}/{total_files} 个文件")
    
    def save_files_directly(self):
        """直接复制文件保存"""
        total_files = len(self.files)
        if total_files == 0:
            self.status_updated.emit("没有可保存的文件")
            return
        
        self.status_updated.emit(f"开始保存 {total_files} 个文件...")
        
        # 计算序号的位数，确保排序正确
        num_digits = len(str(total_files))
        
        # 保存文件
        saved_count = 0
        for i, file_info in enumerate(self.files):
            progress = int((i + 1) / total_files * 100)
            self.progress_updated.emit(progress)
            
            file_path = file_info['path']
            file_name = file_info['name']
            
            self.status_updated.emit(f"正在保存: {file_name} ({i+1}/{total_files})")
            
            try:
                # 确保文件名合法
                safe_name = self.get_safe_filename(file_name)
                
                # 添加序号前缀，确保排序正确
                base_name, ext = os.path.splitext(safe_name)
                sequence_number = str(i + 1).zfill(num_digits)  # 补零确保排序
                prefixed_name = f"{sequence_number}_{safe_name}"
                
                # 如果文件名已存在，添加额外序号
                target_path = os.path.join(self.save_folder, prefixed_name)
                counter = 1
                
                while os.path.exists(target_path):
                    prefixed_name = f"{sequence_number}_{base_name}_{counter}{ext}"
                    target_path = os.path.join(self.save_folder, prefixed_name)
                    counter += 1
                
                # 复制文件
                if os.path.exists(file_path):
                    import shutil
                    shutil.copy2(file_path, target_path)
                    saved_count += 1
                    logger.info(f"保存文件: {file_name} -> {prefixed_name}")
                else:
                    logger.warning(f"文件不存在: {file_path}")
            except Exception as e:
                logger.error(f"保存文件失败: {str(e)}")
        
        self.status_updated.emit(f"保存完成，已保存 {saved_count}/{total_files} 个文件")
    
    def get_safe_filename(self, filename):
        """获取安全的文件名"""
        # 移除非法字符
        import re
        import hashlib
        safe_name = re.sub(r'[\\/*?:"<>|]', '_', filename)
        
        # 确保文件名不为空
        if not safe_name or safe_name.startswith('.'):
            safe_name = f"file_{hashlib.md5(filename.encode()).hexdigest()[:8]}{os.path.splitext(filename)[1]}"
        
        return safe_name 