# 微信收藏解析工具

一个使用Python和PyQt5开发的图形界面工具，用于解析微信缓存中的收藏图片和视频资源，以及压缩包中的媒体文件，并保存到本地。

## 功能特点

- 美观的图形用户界面
- 支持选择微信缓存文件夹路径
- 支持解析ZIP格式压缩包中的媒体文件
- 支持选择输出保存路径
- 自动创建以当前日期命名的文件夹
- 支持自定义保存文件夹名称
- 实时显示解析进度
- 多线程解析，不阻塞界面
- 智能排序，尽可能保持与微信收藏笔记中相同的图片顺序

## 使用方法

### 解析微信收藏

1. 运行程序：`python main.py`
2. 在"设置"页面：
   - 点击"选择路径"按钮，选择微信缓存文件夹路径
     - 通常在 `C:\Users\用户名\Documents\WeChat Files\微信号\FileStorage\Favorites`
     - 或 `C:\Users\用户名\AppData\Roaming\Tencent\WeChat\FileStorage\Favorites`
   - 点击"选择路径"按钮，选择输出保存文件夹路径
   - 点击"保存设置"按钮
3. 在"主页"页面：
   - 点击"解析微信缓存"按钮
   - 等待解析完成，查看预览
   - 点击"保存文件"按钮
   - 输入自定义文件夹名称
   - 等待保存完成

### 解析压缩包

1. 在"主页"页面：
   - 点击"选择压缩包"按钮
   - 选择要解析的ZIP格式压缩包
   - 等待解析完成，查看预览
   - 点击"保存文件"按钮
   - 输入自定义文件夹名称
   - 等待保存完成

## 系统要求

- Python 3.6+
- PyQt5

## 安装依赖

```bash
pip install PyQt5
```

## 项目结构

```
微信收藏解析工具/
├── main.py              # 主程序入口
├── ui/                  # 界面相关代码
│   ├── __init__.py
│   ├── main_window.py   # 主窗口界面
│   └── custom_dialog.py # 自定义对话框
├── utils/               # 工具类
│   ├── __init__.py
│   ├── wechat_parser.py # 微信解析工具类
│   └── archive_parser.py # 压缩包解析工具类
└── resources/           # 资源文件夹
``` 