#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QDialog, QLineEdit, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QDialogButtonBox, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QIcon, QPixmap

class CustomInputDialog(QDialog):
    """自定义的输入对话框，使用中文按钮"""
    
    def __init__(self, parent=None, title="", label="", default_text=""):
        super().__init__(parent)
        
        self.setWindowTitle(title)
        self.resize(400, 150)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 创建提示标签
        self.label = QLabel(label)
        self.label.setStyleSheet("font-size: 14px; color: #333333;")
        main_layout.addWidget(self.label)
        
        # 创建输入框
        self.line_edit = QLineEdit(default_text)
        self.line_edit.setMinimumHeight(35)
        self.line_edit.setStyleSheet("""
            padding: 0px 10px;
            border: 1px solid #d0d0d0;
            border-radius: 6px;
            background-color: white;
            color: #333333;
            font-size: 14px;
            min-height: 35px;
        """)
        main_layout.addWidget(self.line_edit)
        
        # 添加空间
        main_layout.addSpacing(10)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 创建确定按钮
        self.ok_button = QPushButton("确定")
        self.ok_button.setMinimumWidth(100)
        self.ok_button.setMinimumHeight(35)
        self.ok_button.setStyleSheet("""
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
        self.ok_button.clicked.connect(self.accept)
        
        # 创建取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.setMinimumHeight(35)
        self.cancel_button.setStyleSheet("""
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
        self.cancel_button.clicked.connect(self.reject)
        
        # 添加按钮到布局
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        
        # 将按钮布局添加到主布局
        main_layout.addLayout(button_layout)
        
        # 设置焦点到输入框
        self.line_edit.setFocus()
        
        # 连接回车键事件
        self.line_edit.returnPressed.connect(self.accept)
    
    def get_text(self):
        """获取输入的文本"""
        return self.line_edit.text()
    
    @staticmethod
    def get_text_input(parent=None, title="", label="", default_text=""):
        """静态方法，显示对话框并获取输入文本"""
        dialog = CustomInputDialog(parent, title, label, default_text)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            return dialog.get_text(), True
        else:
            return "", False


class CustomMessageBox(QDialog):
    """自定义的消息对话框，使用中文按钮"""
    
    # 定义消息框类型常量
    Information = 0
    Warning = 1
    Critical = 2
    Question = 3
    
    # 定义按钮类型常量
    Ok = 0
    Cancel = 1
    Yes = 2
    No = 3
    
    def __init__(self, parent=None, title="", text="", msg_type=Information, buttons=Ok):
        super().__init__(parent)
        
        self.setWindowTitle(title)
        self.resize(400, 180)
        self.setModal(True)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 创建消息区域布局
        message_layout = QHBoxLayout()
        
        # 创建图标标签
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(48, 48)
        
        # 设置图标
        if msg_type == CustomMessageBox.Information:
            self.setWindowIcon(QIcon.fromTheme("dialog-information"))
            pixmap = QMessageBox.standardIcon(QMessageBox.Information)
            self.icon_label.setPixmap(pixmap)
        elif msg_type == CustomMessageBox.Warning:
            self.setWindowIcon(QIcon.fromTheme("dialog-warning"))
            pixmap = QMessageBox.standardIcon(QMessageBox.Warning)
            self.icon_label.setPixmap(pixmap)
        elif msg_type == CustomMessageBox.Critical:
            self.setWindowIcon(QIcon.fromTheme("dialog-error"))
            pixmap = QMessageBox.standardIcon(QMessageBox.Critical)
            self.icon_label.setPixmap(pixmap)
        elif msg_type == CustomMessageBox.Question:
            self.setWindowIcon(QIcon.fromTheme("dialog-question"))
            pixmap = QMessageBox.standardIcon(QMessageBox.Question)
            self.icon_label.setPixmap(pixmap)
        
        message_layout.addWidget(self.icon_label)
        message_layout.addSpacing(15)
        
        # 创建消息文本标签
        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet("font-size: 14px; color: #333333;")
        message_layout.addWidget(self.text_label, 1)
        
        main_layout.addLayout(message_layout)
        main_layout.addSpacing(15)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 记录用户点击的按钮
        self.clicked_button = None
        
        # 添加按钮
        if buttons & CustomMessageBox.Ok:
            self.ok_button = QPushButton("确定")
            self.ok_button.setMinimumWidth(100)
            self.ok_button.setMinimumHeight(35)
            self.ok_button.setStyleSheet("""
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
            self.ok_button.clicked.connect(lambda: self._button_clicked(CustomMessageBox.Ok))
            # 设置为默认按钮，这样回车键会自动触发
            self.ok_button.setDefault(True)
            self.ok_button.setAutoDefault(True)
            button_layout.addWidget(self.ok_button)
        
        if buttons & CustomMessageBox.Cancel:
            self.cancel_button = QPushButton("取消")
            self.cancel_button.setMinimumWidth(100)
            self.cancel_button.setMinimumHeight(35)
            self.cancel_button.setStyleSheet("""
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
            self.cancel_button.clicked.connect(lambda: self._button_clicked(CustomMessageBox.Cancel))
            button_layout.addWidget(self.cancel_button)
        
        if buttons & CustomMessageBox.Yes:
            self.yes_button = QPushButton("是")
            self.yes_button.setMinimumWidth(100)
            self.yes_button.setMinimumHeight(35)
            self.yes_button.setStyleSheet("""
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
            self.yes_button.clicked.connect(lambda: self._button_clicked(CustomMessageBox.Yes))
            # 设置为默认按钮，这样回车键会自动触发
            self.yes_button.setDefault(True)
            self.yes_button.setAutoDefault(True)
            button_layout.addWidget(self.yes_button)
        
        if buttons & CustomMessageBox.No:
            self.no_button = QPushButton("否")
            self.no_button.setMinimumWidth(100)
            self.no_button.setMinimumHeight(35)
            self.no_button.setStyleSheet("""
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
            self.no_button.clicked.connect(lambda: self._button_clicked(CustomMessageBox.No))
            button_layout.addWidget(self.no_button)
        
        main_layout.addLayout(button_layout)
        
        # 设置焦点到第一个按钮
        if hasattr(self, 'ok_button'):
            self.ok_button.setFocus()
        elif hasattr(self, 'yes_button'):
            self.yes_button.setFocus()
        
    def _button_clicked(self, button):
        """记录用户点击的按钮并关闭对话框"""
        self.clicked_button = button
        self.accept()
    
    @staticmethod
    def information(parent, title, text):
        """显示信息对话框"""
        dialog = CustomMessageBox(parent, title, text, CustomMessageBox.Information, CustomMessageBox.Ok)
        dialog.exec_()
    
    @staticmethod
    def warning(parent, title, text):
        """显示警告对话框"""
        dialog = CustomMessageBox(parent, title, text, CustomMessageBox.Warning, CustomMessageBox.Ok)
        dialog.exec_()
    
    @staticmethod
    def critical(parent, title, text):
        """显示错误对话框"""
        dialog = CustomMessageBox(parent, title, text, CustomMessageBox.Critical, CustomMessageBox.Ok)
        dialog.exec_()
    
    @staticmethod
    def question(parent, title, text):
        """显示问题对话框，返回用户选择的按钮"""
        dialog = CustomMessageBox(parent, title, text, CustomMessageBox.Question, 
                                 CustomMessageBox.Yes | CustomMessageBox.No | CustomMessageBox.Cancel)
        dialog.exec_()
        return dialog.clicked_button 