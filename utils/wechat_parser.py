#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import shutil
import sqlite3
import hashlib
import logging
from pathlib import Path
import winreg  # 用于访问Windows注册表

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WeChatParser:
    """微信收藏解析工具类"""
    
    def __init__(self, cache_path):
        """
        初始化解析器
        
        Args:
            cache_path: 微信缓存文件夹路径
        """
        # 处理路径末尾可能的斜杠
        self.cache_path = cache_path.rstrip('\\/')
        logger.info(f"初始化解析器，缓存路径: {self.cache_path}")
        
        try:
            self.favorites_path = self._find_favorites_path()
            logger.info(f"找到收藏路径: {self.favorites_path}")
            self.db_path = self._find_favorites_db()
            if self.db_path:
                logger.info(f"找到收藏数据库: {self.db_path}")
            else:
                logger.warning("未找到收藏数据库，将使用文件系统方式解析")
        except Exception as e:
            logger.error(f"初始化解析器失败: {str(e)}")
            raise
            
        self.media_files = []
    
    @staticmethod
    def get_current_wxid():
        """
        获取当前登录的微信wxid
        
        Returns:
            str: 当前登录的wxid，如果找不到则返回None
        """
        try:
            # 尝试从微信配置文件中获取wxid
            # 微信配置文件路径
            wechat_files_dir = os.path.join(os.environ['USERPROFILE'], 'Documents', 'WeChat Files')
            
            if not os.path.exists(wechat_files_dir):
                # 尝试从注册表获取微信安装路径
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Tencent\WeChat")
                    install_path = winreg.QueryValueEx(key, "InstallPath")[0]
                    wechat_files_dir = os.path.join(os.path.dirname(install_path), 'WeChat Files')
                except Exception as e:
                    logger.warning(f"无法从注册表获取微信安装路径: {str(e)}")
                    
                    # 尝试另一个常见位置
                    alt_path = os.path.join(os.environ['APPDATA'], 'Tencent', 'WeChat')
                    if os.path.exists(alt_path):
                        wechat_files_dir = os.path.join(alt_path, 'WeChat Files')
            
            if not os.path.exists(wechat_files_dir):
                logger.warning("找不到WeChat Files目录")
                return None
            
            # 查找wxid目录
            wxid_pattern = re.compile(r'wxid_.*')
            wxid_dirs = []
            
            for item in os.listdir(wechat_files_dir):
                if wxid_pattern.match(item) and os.path.isdir(os.path.join(wechat_files_dir, item)):
                    wxid_dirs.append(item)
            
            # 如果找到多个wxid，查找最近修改的一个
            if wxid_dirs:
                if len(wxid_dirs) == 1:
                    return wxid_dirs[0]
                else:
                    # 查找最近修改的wxid目录
                    latest_wxid = None
                    latest_time = 0
                    
                    for wxid in wxid_dirs:
                        wxid_path = os.path.join(wechat_files_dir, wxid)
                        mod_time = os.path.getmtime(wxid_path)
                        if mod_time > latest_time:
                            latest_time = mod_time
                            latest_wxid = wxid
                    
                    return latest_wxid
            
            # 如果没有找到wxid目录，尝试查找配置文件
            config_path = os.path.join(wechat_files_dir, 'config.data')
            if os.path.exists(config_path):
                with open(config_path, 'rb') as f:
                    content = f.read()
                    # 在二进制内容中查找wxid
                    matches = re.findall(rb'wxid_[a-zA-Z0-9_-]{10,}', content)
                    if matches:
                        return matches[0].decode('utf-8')
            
            logger.warning("无法找到当前登录的wxid")
            return None
            
        except Exception as e:
            logger.error(f"获取当前登录的wxid时出错: {str(e)}")
            return None
    
    @staticmethod
    def get_wechat_path():
        """
        获取微信文件目录路径
        
        Returns:
            str: 微信文件目录路径，如果找不到则返回None
        """
        try:
            # 尝试常见的微信文件目录路径
            possible_paths = [
                os.path.join(os.environ['USERPROFILE'], 'Documents', 'WeChat Files'),
                os.path.join(os.environ['APPDATA'], 'Tencent', 'WeChat', 'WeChat Files')
            ]
            
            # 尝试从注册表获取微信安装路径
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Tencent\WeChat")
                install_path = winreg.QueryValueEx(key, "InstallPath")[0]
                possible_paths.append(os.path.join(os.path.dirname(install_path), 'WeChat Files'))
            except Exception as e:
                logger.warning(f"无法从注册表获取微信安装路径: {str(e)}")
            
            # 检查路径是否存在
            for path in possible_paths:
                if os.path.exists(path):
                    return path
            
            logger.warning("找不到WeChat Files目录")
            return None
            
        except Exception as e:
            logger.error(f"获取微信文件目录路径时出错: {str(e)}")
            return None
    
    @staticmethod
    def get_favorites_path():
        """
        获取微信收藏文件夹路径
        
        Returns:
            str: 微信收藏文件夹路径，如果找不到则返回None
        """
        try:
            # 获取当前登录的wxid
            wxid = WeChatParser.get_current_wxid()
            if not wxid:
                logger.warning("无法获取当前登录的wxid")
                return None
            
            # 获取微信文件目录路径
            wechat_path = WeChatParser.get_wechat_path()
            if not wechat_path:
                logger.warning("无法获取微信文件目录路径")
                return None
            
            # 构建收藏文件夹路径
            possible_paths = [
                os.path.join(wechat_path, wxid, 'Favorites'),
                os.path.join(wechat_path, wxid, 'FileStorage', 'Favorites'),
                os.path.join(wechat_path, wxid, 'FileStorage', 'Fav')
            ]
            
            # 检查路径是否存在
            for path in possible_paths:
                if os.path.exists(path):
                    return path
            
            logger.warning(f"找不到wxid {wxid} 的收藏文件夹")
            return None
            
        except Exception as e:
            logger.error(f"获取微信收藏文件夹路径时出错: {str(e)}")
            return None
    
    def _find_favorites_path(self):
        """查找收藏文件夹路径"""
        # 检查路径是否存在
        if not os.path.exists(self.cache_path):
            logger.error(f"指定的路径不存在: {self.cache_path}")
            raise FileNotFoundError(f"指定的路径不存在: {self.cache_path}")
            
        # 如果用户直接选择了Favorites或类似名称的文件夹
        base_name = os.path.basename(self.cache_path).lower()
        if base_name == 'favorites' or base_name == 'fav' or base_name.startswith('favorite'):
            logger.info(f"用户直接选择了收藏相关文件夹: {self.cache_path}")
            
            # 如果路径不完整（例如Fav而不是Favorites），尝试找到完整的路径
            if base_name != 'favorites':
                parent_dir = os.path.dirname(self.cache_path)
                for item in os.listdir(parent_dir):
                    item_path = os.path.join(parent_dir, item)
                    if os.path.isdir(item_path) and item.lower() == 'favorites':
                        logger.info(f"找到完整的Favorites文件夹: {item_path}")
                        return item_path
            
            return self.cache_path
            
        # 常见的微信收藏路径
        possible_paths = [
            os.path.join(self.cache_path, 'Favorites'),
            os.path.join(self.cache_path, 'FileStorage', 'Favorites'),
            os.path.join(self.cache_path, 'WeChat Files', 'Favorites'),
            os.path.join(self.cache_path, 'Favorites', 'File'),
            os.path.join(self.cache_path, 'Favorites', 'Images'),
            os.path.join(self.cache_path, 'Favorites', 'Videos')
        ]
        
        # 检查路径是否存在
        for path in possible_paths:
            logger.info(f"检查路径: {path}")
            if os.path.exists(path):
                return path
        
        # 查找包含"Favorites"或"Fav"的目录（不区分大小写）
        fav_pattern = re.compile(r'fav.*', re.IGNORECASE)
        for root, dirs, _ in os.walk(self.cache_path):
            for dir_name in dirs:
                if fav_pattern.match(dir_name):
                    fav_dir = os.path.join(root, dir_name)
                    logger.info(f"找到可能的收藏文件夹: {fav_dir}")
                    return fav_dir
        
        # 查找包含wxid_的目录
        wxid_pattern = re.compile(r'wxid_.*')
        try:
            for item in os.listdir(self.cache_path):
                if wxid_pattern.match(item) and os.path.isdir(os.path.join(self.cache_path, item)):
                    wxid_dir = os.path.join(self.cache_path, item)
                    logger.info(f"找到wxid目录: {wxid_dir}")
                    
                    # 检查wxid目录下的可能路径
                    wxid_paths = [
                        os.path.join(wxid_dir, 'Favorites'),
                        os.path.join(wxid_dir, 'FileStorage', 'Favorites'),
                        os.path.join(wxid_dir, 'Fav')
                    ]
                    
                    for path in wxid_paths:
                        if os.path.exists(path):
                            return path
                    
                    # 在wxid目录下查找包含"Fav"的目录
                    for root, dirs, _ in os.walk(wxid_dir):
                        for dir_name in dirs:
                            if fav_pattern.match(dir_name):
                                fav_dir = os.path.join(root, dir_name)
                                logger.info(f"在wxid目录下找到可能的收藏文件夹: {fav_dir}")
                                return fav_dir
        except Exception as e:
            logger.warning(f"查找wxid目录时出错: {str(e)}")
        
        # 尝试在给定路径下查找
        logger.info("在整个目录树中查找Favorites文件夹")
        for root, dirs, _ in os.walk(self.cache_path):
            for dir_name in dirs:
                if fav_pattern.match(dir_name):
                    fav_dir = os.path.join(root, dir_name)
                    logger.info(f"找到可能的收藏文件夹: {fav_dir}")
                    return fav_dir
        
        # 如果仍然找不到，尝试直接使用输入路径
        if os.path.isdir(self.cache_path) and any(os.path.isfile(os.path.join(self.cache_path, f)) for f in os.listdir(self.cache_path)):
            logger.warning("未找到标准Favorites文件夹，将直接使用输入路径")
            return self.cache_path
            
        # 检查路径是否包含"FileStorage/Fav"，如果是，尝试补全为"FileStorage/Favorites"
        if "FileStorage/Fav" in self.cache_path.replace("\\", "/"):
            complete_path = self.cache_path.replace("FileStorage/Fav", "FileStorage/Favorites").replace("FileStorage\\Fav", "FileStorage\\Favorites")
            if os.path.exists(complete_path):
                logger.info(f"找到完整路径: {complete_path}")
                return complete_path
                
        # 输出目录结构以帮助调试
        logger.error("无法找到微信收藏文件夹，当前路径结构:")
        self._print_directory_structure(self.cache_path)
            
        raise FileNotFoundError(f"无法找到微信收藏文件夹，请确认路径是否正确: {self.cache_path}")
    
    def _print_directory_structure(self, path, level=0, max_level=3):
        """打印目录结构，帮助调试"""
        if level > max_level:
            return
            
        try:
            # 打印当前目录
            logger.info(f"{'  ' * level}[DIR] {os.path.basename(path) or path}")
            
            # 列出子目录和文件
            if os.path.isdir(path):
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        self._print_directory_structure(item_path, level + 1, max_level)
                    else:
                        logger.info(f"{'  ' * (level + 1)}[FILE] {item}")
        except Exception as e:
            logger.error(f"打印目录结构时出错: {str(e)}")
    
    def _find_favorites_db(self):
        """查找收藏数据库文件"""
        # 常见的数据库文件名
        db_names = [
            'favorite.db', 'favorites.db', 'FavoritesItem.db', 'Favorites.db', 
            'favoriteItem.db', 'FavoriteStorage.db', 'FavStorage.db',
            'WxFavorite.db', 'wxfavorite.db', 'fav.db', 'Fav.db'
        ]
        
        # 在收藏文件夹中查找数据库
        for db_name in db_names:
            db_path = os.path.join(self.favorites_path, db_name)
            if os.path.exists(db_path):
                logger.info(f"在收藏文件夹中找到数据库: {db_path}")
                return db_path
        
        # 在收藏文件夹的父目录中查找数据库
        parent_dir = os.path.dirname(self.favorites_path)
        for db_name in db_names:
            db_path = os.path.join(parent_dir, db_name)
            if os.path.exists(db_path):
                logger.info(f"在父目录中找到数据库: {db_path}")
                return db_path
        
        # 在更上级目录中查找（例如FileStorage目录）
        if "FileStorage" in self.favorites_path:
            file_storage_dir = self.favorites_path.split("FileStorage")[0] + "FileStorage"
            for db_name in db_names:
                db_path = os.path.join(file_storage_dir, db_name)
                if os.path.exists(db_path):
                    logger.info(f"在FileStorage目录中找到数据库: {db_path}")
                    return db_path
        
        # 在微信用户目录中查找数据库
        if "wxid_" in self.favorites_path:
            # 提取wxid目录
            parts = self.favorites_path.split(os.sep)
            wxid_index = -1
            for i, part in enumerate(parts):
                if part.startswith("wxid_"):
                    wxid_index = i
                    break
            
            if wxid_index >= 0:
                wxid_dir = os.sep.join(parts[:wxid_index+1])
                for db_name in db_names:
                    db_path = os.path.join(wxid_dir, db_name)
                    if os.path.exists(db_path):
                        logger.info(f"在wxid目录中找到数据库: {db_path}")
                        return db_path
                
                # 在wxid目录的子目录中查找
                for root, _, files in os.walk(wxid_dir):
                    for file in files:
                        if file.lower().endswith('.db') and any(keyword in file.lower() for keyword in ['fav', 'favorite']):
                            db_path = os.path.join(root, file)
                            logger.info(f"在wxid子目录中找到相关数据库: {db_path}")
                            return db_path
        
        # 递归查找数据库文件
        logger.info("递归查找数据库文件...")
        for root, _, files in os.walk(self.favorites_path):
            for file in files:
                if file.lower().endswith('.db'):
                    db_path = os.path.join(root, file)
                    logger.info(f"找到数据库文件: {db_path}")
                    return db_path
   
    
    def get_total_files(self):
        """获取可解析的文件总数"""
        if self.media_files:
            return len(self.media_files)
            
        self.media_files = self._find_media_files()
        return len(self.media_files)
    
    def _find_media_files(self):
        """查找媒体文件"""
        media_files = []
        
        # 如果找到了数据库，尝试从数据库中获取文件信息
        if self.db_path and os.path.exists(self.db_path):
            try:
                logger.info(f"尝试从数据库获取文件信息: {self.db_path}")
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 首先获取所有表结构，了解数据库结构
                cursor.execute("SELECT * FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                logger.info("数据库表结构:")
                for table_info in tables:
                    logger.info(f"表名: {table_info[1]}, 创建语句: {table_info[4]}")
                
                # 尝试不同的表名和列名，包含排序信息
                tables_to_try = [
                    # 尝试获取带有时间戳或序号的查询，用于排序
                    ("SELECT localId, fileName, createTime FROM FavoritesItem ORDER BY createTime ASC", 
                     lambda row: (row[0], row[1], row[2] if len(row) > 2 else None)),
                    ("SELECT localId, fileName, updateTime FROM FavoritesItem ORDER BY updateTime ASC", 
                     lambda row: (row[0], row[1], row[2] if len(row) > 2 else None)),
                    ("SELECT localId, fileName, seq FROM FavoritesItem ORDER BY seq ASC", 
                     lambda row: (row[0], row[1], row[2] if len(row) > 2 else None)),
                    ("SELECT localId, fileName, id FROM FavoritesItem ORDER BY id ASC", 
                     lambda row: (row[0], row[1], row[2] if len(row) > 2 else None)),
                    ("SELECT itemId, fileName, createTime FROM favorites ORDER BY createTime ASC", 
                     lambda row: (row[0], row[1], row[2] if len(row) > 2 else None)),
                    ("SELECT id, fileName, createTime FROM favoriteItem ORDER BY createTime ASC", 
                     lambda row: (row[0], row[1], row[2] if len(row) > 2 else None)),
                    # 如果没有时间字段，按ID排序
                    ("SELECT localId, fileName FROM FavoritesItem ORDER BY localId ASC", 
                     lambda row: (row[0], row[1], None)),
                    ("SELECT itemId, fileName FROM favorites ORDER BY itemId ASC", 
                     lambda row: (row[0], row[1], None)),
                    ("SELECT id, fileName FROM favoriteItem ORDER BY id ASC", 
                     lambda row: (row[0], row[1], None)),
                ]
                
                for query, row_parser in tables_to_try:
                    try:
                        cursor.execute(query)
                        results = cursor.fetchall()
                        
                        logger.info(f"查询成功: {query}, 找到 {len(results)} 条记录")
                        for row in results:
                            item_id, file_name, sort_key = row_parser(row)
                            file_path = self._find_file_by_id(item_id)
                            if file_path:
                                media_files.append({
                                    'id': item_id,
                                    'name': file_name or f"file_{item_id}",
                                    'path': file_path,
                                    'sort_key': sort_key  # 添加排序键
                                })
                        # 如果找到了文件，就不再尝试其他查询
                        if media_files:
                            logger.info(f"从数据库获取到 {len(media_files)} 个文件，已按顺序排列")
                            break
                    except sqlite3.OperationalError as e:
                        logger.warning(f"SQL查询失败: {query}, 错误: {str(e)}")
                
                conn.close()
            except Exception as e:
                logger.error(f"数据库访问出错: {str(e)}")
        
        # 如果数据库方式没有找到文件，直接扫描文件夹
        if not media_files:
            logger.info("使用文件系统方式查找媒体文件")
            # 图片和视频文件扩展名
            media_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', 
                               '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv']
            
            file_count = 0
            temp_files = []
            for root, _, files in os.walk(self.favorites_path):
                for file in files:
                    file_ext = os.path.splitext(file)[1].lower()
                    if file_ext in media_extensions:
                        # 跳过视频封面图片（通常以_th.jpg结尾）
                        file_path = os.path.join(root, file)
                        if self._is_video_thumbnail(file, root):
                            logger.debug(f"跳过视频封面图片: {file}")
                            continue
                            
                        file_path = os.path.join(root, file)
                        # 获取文件的修改时间作为排序依据
                        try:
                            mtime = os.path.getmtime(file_path)
                        except:
                            mtime = 0
                        
                        temp_files.append({
                            'id': hashlib.md5(file_path.encode()).hexdigest(),
                            'name': file,
                            'path': file_path,
                            'mtime': mtime
                        })
                        file_count += 1
                        if file_count % 100 == 0:
                            logger.info(f"已找到 {file_count} 个媒体文件")
            
            # 按修改时间排序（从旧到新，模拟添加到收藏的顺序）
            temp_files.sort(key=lambda x: x['mtime'])
            
            # 转换为标准格式
            for file_info in temp_files:
                media_files.append({
                    'id': file_info['id'],
                    'name': file_info['name'],
                    'path': file_info['path'],
                    'sort_key': file_info['mtime']
                })
            
            logger.info(f"文件系统方式共找到 {len(media_files)} 个媒体文件，已按修改时间排序")
        
        # 应用智能排序
        media_files = self._apply_smart_sorting(media_files)
        
        return media_files
    
    def _find_file_by_id(self, file_id):
        """根据ID查找文件路径"""
        # 常见的文件存储路径模式
        path_patterns = [
            os.path.join(self.favorites_path, str(file_id)),
            os.path.join(self.favorites_path, 'File', str(file_id)),
            os.path.join(self.favorites_path, 'Images', str(file_id)),
            os.path.join(self.favorites_path, 'Videos', str(file_id)),
            os.path.join(self.favorites_path, 'Media', str(file_id))
        ]
        
        # 检查各种可能的路径
        for pattern in path_patterns:
            if os.path.exists(pattern):
                return pattern
        
        # 如果直接路径不存在，尝试在子文件夹中查找
        for root, _, files in os.walk(self.favorites_path):
            for file in files:
                # 检查文件名是否包含ID
                if str(file_id) in file:
                    return os.path.join(root, file)
                # 检查文件名是否就是ID（无扩展名的情况）
                if os.path.splitext(file)[0] == str(file_id):
                    return os.path.join(root, file)
        
        return None
    
    def _apply_smart_sorting(self, media_files):
        """应用智能排序策略"""
        if not media_files:
            return media_files
        
        logger.info("应用智能排序策略...")
        
        # 策略1: 如果有数据库排序键，优先使用
        if media_files and 'sort_key' in media_files[0] and media_files[0]['sort_key'] is not None:
            logger.info("使用数据库排序键进行排序")
            return media_files  # 已经在数据库查询时排序了
        
        # 策略2: 按文件修改时间排序
        try:
            for file_info in media_files:
                if 'mtime' not in file_info:
                    try:
                        file_info['mtime'] = os.path.getmtime(file_info['path'])
                    except:
                        file_info['mtime'] = 0
            
            # 按修改时间排序（从旧到新）
            media_files.sort(key=lambda x: x.get('mtime', 0))
            logger.info("按文件修改时间排序完成")
            
        except Exception as e:
            logger.warning(f"按修改时间排序失败: {str(e)}")
        
        # 策略3: 如果修改时间相同或无效，尝试按文件名中的数字排序
        try:
            # 提取文件名中的数字进行排序
            import re
            
            def extract_number_from_filename(filename):
                """从文件名中提取数字"""
                numbers = re.findall(r'\d+', filename)
                if numbers:
                    return int(numbers[0])  # 使用第一个数字
                return 0
            
            # 检查是否有相同的修改时间
            mtimes = [f.get('mtime', 0) for f in media_files]
            if len(set(mtimes)) < len(mtimes) * 0.8:  # 如果80%以上的文件修改时间相同
                logger.info("检测到大量相同修改时间，尝试按文件名数字排序")
                media_files.sort(key=lambda x: (x.get('mtime', 0), extract_number_from_filename(x['name'])))
                
        except Exception as e:
            logger.warning(f"按文件名数字排序失败: {str(e)}")
        
        return media_files
    
    def parse_favorites(self):
        """解析微信收藏"""
        if not self.media_files:
            self.media_files = self._find_media_files()
        
        # 输出排序信息，帮助用户了解当前排序状态
        self._log_sorting_info()
        
        for file_info in self.media_files:
            if file_info['path'] and os.path.exists(file_info['path']):
                # 确定文件类型
                file_ext = os.path.splitext(file_info['path'])[1].lower()
                if not file_ext:
                    # 如果没有扩展名，尝试根据文件内容判断
                    file_ext = self._detect_file_type(file_info['path'])
                
                # 确保文件名有合适的扩展名
                if not file_info['name'].lower().endswith(file_ext):
                    file_info['name'] = f"{file_info['name']}{file_ext}"
                
                yield file_info
    
    def _log_sorting_info(self):
        """记录排序信息"""
        if not self.media_files:
            return
        
        logger.info("=== 文件排序信息 ===")
        logger.info(f"总文件数: {len(self.media_files)}")
        
        # 检查排序依据
        has_sort_key = any('sort_key' in f and f['sort_key'] is not None for f in self.media_files)
        has_mtime = any('mtime' in f for f in self.media_files)
        
        if has_sort_key:
            logger.info("排序依据: 数据库排序键（推荐，最接近微信收藏顺序）")
        elif has_mtime:
            logger.info("排序依据: 文件修改时间（可能反映添加到收藏的时间顺序）")
        else:
            logger.info("排序依据: 文件系统默认顺序")
        
        # 显示前几个文件的信息
        logger.info("前5个文件的排序信息:")
        for i, file_info in enumerate(self.media_files[:5]):
            sort_info = ""
            if 'sort_key' in file_info and file_info['sort_key'] is not None:
                sort_info = f"排序键: {file_info['sort_key']}"
            elif 'mtime' in file_info:
                import datetime
                mtime_str = datetime.datetime.fromtimestamp(file_info['mtime']).strftime('%Y-%m-%d %H:%M:%S')
                sort_info = f"修改时间: {mtime_str}"
            
            logger.info(f"  {i+1}. {file_info['name']} - {sort_info}")
        
        logger.info("=== 排序信息结束 ===")
    
    def get_sorting_strategy_info(self):
        """获取当前使用的排序策略信息"""
        if not self.media_files:
            self.media_files = self._find_media_files()
        
        if not self.media_files:
            return "未找到文件"
        
        has_sort_key = any('sort_key' in f and f['sort_key'] is not None for f in self.media_files)
        has_mtime = any('mtime' in f for f in self.media_files)
        
        if has_sort_key:
            return "数据库排序（最佳）- 基于微信数据库中的顺序信息"
        elif has_mtime:
            return "时间排序（良好）- 基于文件修改时间，可能反映添加顺序"
        else:
            return "默认排序（一般）- 基于文件系统顺序"
    
    def _detect_file_type(self, file_path):
        """根据文件内容检测文件类型"""
        # 文件头部特征码
        signatures = {
            b'\xff\xd8\xff': '.jpg',  # JPEG
            b'\x89PNG\r\n\x1a\n': '.png',  # PNG
            b'GIF8': '.gif',  # GIF
            b'RIFF....WEBP': '.webp',  # WEBP (.... 表示任意4个字符)
            b'\x00\x00\x00\x18ftypmp4': '.mp4',  # MP4
            b'\x00\x00\x00\x14ftypqt': '.mov',  # MOV
        }
        
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)  # 读取前16个字节
                
            for sig, ext in signatures.items():
                # 处理带有通配符的特征码
                if b'....' in sig:
                    parts = sig.split(b'....')
                    if header.startswith(parts[0]) and parts[1] in header:
                        return ext
                # 普通特征码
                elif header.startswith(sig):
                    return ext
            
            # 如果无法识别，根据文件大小猜测
            file_size = os.path.getsize(file_path)
            if file_size > 1024 * 1024:  # 大于1MB可能是视频
                return '.mp4'
            else:
                return '.jpg'  # 默认为JPEG
        except Exception:
            return '.dat'  # 无法识别时使用通用扩展名
    
    def save_file(self, file_info, save_folder):
        """保存文件到指定文件夹"""
        if not file_info['path'] or not os.path.exists(file_info['path']):
            logger.warning(f"文件不存在: {file_info['path']}")
            return False
        
        # 确保文件名合法
        safe_name = self._get_safe_filename(file_info['name'])
        
        # 如果文件名已存在，添加序号
        target_path = os.path.join(save_folder, safe_name)
        base_name, ext = os.path.splitext(safe_name)
        counter = 1
        
        while os.path.exists(target_path):
            safe_name = f"{base_name}_{counter}{ext}"
            target_path = os.path.join(save_folder, safe_name)
            counter += 1
        
        # 复制文件
        try:
            logger.info(f"保存文件: {file_info['path']} -> {target_path}")
            shutil.copy2(file_info['path'], target_path)
            return True
        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}")
            return False
    
    def save_file_with_sequence(self, file_info, save_folder):
        """保存文件到指定文件夹，带序号前缀"""
        if not file_info['path'] or not os.path.exists(file_info['path']):
            logger.warning(f"文件不存在: {file_info['path']}")
            return False
        
        # 确保文件名合法
        safe_name = self._get_safe_filename(file_info['name'])
        
        # 添加序号前缀
        sequence = file_info.get('sequence', '001')
        base_name, ext = os.path.splitext(safe_name)
        prefixed_name = f"{sequence}_{safe_name}"
        
        # 如果文件名已存在，添加额外序号
        target_path = os.path.join(save_folder, prefixed_name)
        counter = 1
        
        while os.path.exists(target_path):
            prefixed_name = f"{sequence}_{base_name}_{counter}{ext}"
            target_path = os.path.join(save_folder, prefixed_name)
            counter += 1
        
        # 复制文件
        try:
            logger.info(f"保存文件: {file_info['path']} -> {target_path}")
            shutil.copy2(file_info['path'], target_path)
            return True
        except Exception as e:
            logger.error(f"保存文件失败: {str(e)}")
            return False
    
    def _is_video_thumbnail(self, filename, file_dir):
        """判断是否为视频封面图片"""
        # 常见的视频封面图片命名模式
        thumbnail_patterns = [
            r'.*_th\.(jpg|jpeg|png)$',  # 以_th结尾的图片
            r'.*_thumb\.(jpg|jpeg|png)$',  # 以_thumb结尾的图片
            r'.*_thumbnail\.(jpg|jpeg|png)$',  # 以_thumbnail结尾的图片
            r'.*\.mp4_th\.(jpg|jpeg|png)$',  # .mp4_th格式
            r'.*\.mov_th\.(jpg|jpeg|png)$',  # .mov_th格式
        ]
        
        filename_lower = filename.lower()
        for pattern in thumbnail_patterns:
            if re.match(pattern, filename_lower):
                return True
        
        # 检查是否存在对应的视频文件
        base_name = os.path.splitext(filename)[0]
        if base_name.endswith('_th') or base_name.endswith('_thumb'):
            # 去掉后缀，检查是否有对应的视频文件
            video_base = base_name.replace('_th', '').replace('_thumb', '')
            video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv']
            
            # 在同一目录下查找对应的视频文件
            for ext in video_extensions:
                video_file = os.path.join(file_dir, f"{video_base}{ext}")
                if os.path.exists(video_file):
                    logger.debug(f"找到对应的视频文件: {video_file}，跳过封面图片: {filename}")
                    return True
        
        return False
    
    def _get_safe_filename(self, filename):
        """获取安全的文件名"""
        # 移除非法字符
        safe_name = re.sub(r'[\\/*?:"<>|]', '_', filename)
        
        # 确保文件名不为空
        if not safe_name or safe_name.startswith('.'):
            safe_name = f"file_{hashlib.md5(filename.encode()).hexdigest()[:8]}{os.path.splitext(filename)[1]}"
        
        return safe_name 