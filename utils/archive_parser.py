#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import shutil
import zipfile
import tempfile
import hashlib
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ArchiveParser:
    """压缩包解析工具类"""
    
    # 类变量，用于跟踪所有创建的临时目录
    temp_directories = []
    
    def __init__(self, archive_path):
        """
        初始化解析器
        
        Args:
            archive_path: 压缩包文件路径
        """
        self.archive_path = archive_path
        logger.info(f"初始化压缩包解析器，压缩包路径: {self.archive_path}")
        
        # 检查文件是否存在
        if not os.path.exists(self.archive_path):
            logger.error(f"压缩包文件不存在: {self.archive_path}")
            raise FileNotFoundError(f"压缩包文件不存在: {self.archive_path}")
            
        # 检查文件是否为压缩包
        self.archive_type = self._detect_archive_type()
        if not self.archive_type:
            logger.error(f"不支持的压缩包格式: {self.archive_path}")
            raise ValueError(f"不支持的压缩包格式: {self.archive_path}")
        
        # 获取系统临时目录
        system_temp = tempfile.gettempdir()
        logger.info(f"系统临时目录: {system_temp}")
        
        # 创建临时目录用于解压文件
        try:
            # 尝试在系统临时目录下创建文件夹
            self.temp_dir = tempfile.mkdtemp(prefix="archive_extract_", dir=system_temp)
            logger.info(f"创建临时目录: {self.temp_dir}")
            
            # 将临时目录添加到类变量中
            ArchiveParser.temp_directories.append(self.temp_dir)
            logger.info(f"当前活跃的临时目录数量: {len(ArchiveParser.temp_directories)}")
            
            # 测试临时目录是否可写
            test_file = os.path.join(self.temp_dir, "test_write.txt")
            with open(test_file, 'w') as f:
                f.write("Test write permission")
            if os.path.exists(test_file):
                os.remove(test_file)
                logger.info("临时目录写入测试成功")
            else:
                logger.error("临时目录写入测试失败")
                raise IOError("无法在临时目录创建文件")
                
        except Exception as e:
            logger.error(f"创建临时目录失败: {str(e)}")
            # 如果在系统临时目录创建失败，尝试在当前目录创建
            try:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                self.temp_dir = tempfile.mkdtemp(prefix="archive_extract_", dir=current_dir)
                logger.info(f"在当前目录创建临时目录: {self.temp_dir}")
                
                # 将临时目录添加到类变量中
                ArchiveParser.temp_directories.append(self.temp_dir)
                logger.info(f"当前活跃的临时目录数量: {len(ArchiveParser.temp_directories)}")
            except Exception as e2:
                logger.error(f"在当前目录创建临时目录也失败: {str(e2)}")
                raise IOError(f"无法创建临时目录: {str(e2)}")
            
        # 媒体文件列表
        self.media_files = []
        
        # 标记是否已解压
        self.is_extracted = False
        
        # 文件句柄列表，用于保持文件打开状态
        self.file_handles = []
        
    def __del__(self):
        """析构函数，清理临时文件"""
        # 关闭所有打开的文件句柄
        self.close_file_handles()
        
        # 只有在对象被销毁时才清理临时文件
        try:
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                logger.info(f"清理临时目录: {self.temp_dir}")
                
                # 从类变量中移除
                if self.temp_dir in ArchiveParser.temp_directories:
                    ArchiveParser.temp_directories.remove(self.temp_dir)
                    logger.info(f"从活跃临时目录列表中移除，剩余: {len(ArchiveParser.temp_directories)}")
                
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            logger.error(f"清理临时目录失败: {str(e)}")
    
    def close_file_handles(self):
        """关闭所有打开的文件句柄"""
        for handle in self.file_handles:
            try:
                handle.close()
                logger.debug("关闭文件句柄")
            except Exception as e:
                logger.error(f"关闭文件句柄失败: {str(e)}")
        
        self.file_handles = []
    
    @classmethod
    def cleanup_all_temp_dirs(cls):
        """清理所有临时目录"""
        logger.info(f"开始清理所有临时目录，数量: {len(cls.temp_directories)}")
        
        for temp_dir in cls.temp_directories[:]:
            try:
                if os.path.exists(temp_dir):
                    logger.info(f"清理临时目录: {temp_dir}")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                
                cls.temp_directories.remove(temp_dir)
            except Exception as e:
                logger.error(f"清理临时目录失败: {temp_dir}, 错误: {str(e)}")
        
        logger.info(f"临时目录清理完成，剩余: {len(cls.temp_directories)}")
    
    def _detect_archive_type(self):
        """检测压缩包类型"""
        file_ext = os.path.splitext(self.archive_path)[1].lower()
        
        if file_ext in ['.zip']:
            return 'zip'
        else:
            # 尝试根据文件头识别
            try:
                with open(self.archive_path, 'rb') as f:
                    header = f.read(10)
                    
                if header.startswith(b'PK\x03\x04'):
                    return 'zip'
            except Exception as e:
                logger.error(f"检测压缩包类型失败: {str(e)}")
                
        return None
    
    def extract_archive(self):
        """解压压缩包到临时目录"""
        try:
            logger.info(f"开始解压压缩包: {self.archive_path}")
            
            if self.archive_type == 'zip':
                with zipfile.ZipFile(self.archive_path, 'r') as zip_ref:
                    # 获取压缩包中的文件列表
                    file_list = zip_ref.namelist()
                    logger.info(f"压缩包中包含 {len(file_list)} 个文件")
                    
                    # 解压所有文件
                    zip_ref.extractall(self.temp_dir)
                    
                    # 验证解压结果
                    extracted_files = []
                    for root, _, files in os.walk(self.temp_dir):
                        for file in files:
                            if file != "test_write.txt":  # 排除测试文件
                                file_path = os.path.join(root, file)
                                extracted_files.append(file_path)
                    
                    logger.info(f"成功解压 {len(extracted_files)} 个文件")
                    if len(extracted_files) == 0:
                        logger.error("解压后没有找到任何文件")
                        return False
                    
                    # 检查几个文件是否存在
                    for i, file_path in enumerate(extracted_files[:5]):
                        if os.path.exists(file_path):
                            logger.info(f"文件{i+1}存在: {file_path}")
                        else:
                            logger.error(f"文件{i+1}不存在: {file_path}")
            
            logger.info(f"解压完成，临时目录: {self.temp_dir}")
            self.is_extracted = True
            return True
            
        except Exception as e:
            logger.error(f"解压压缩包失败: {str(e)}")
            return False
    
    def get_total_files(self):
        """获取可解析的文件总数"""
        if self.media_files:
            return len(self.media_files)
            
        self.media_files = self._find_media_files()
        return len(self.media_files)
    
    def _find_media_files(self):
        """查找媒体文件"""
        # 先解压压缩包
        if not self.is_extracted and not self.extract_archive():
            return []
            
        media_files = []
        
        # 图片和视频文件扩展名
        media_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', 
                           '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv']
        
        file_count = 0
        temp_files = []
        
        # 遍历临时目录查找媒体文件
        for root, _, files in os.walk(self.temp_dir):
            for file in files:
                if file == "test_write.txt":  # 排除测试文件
                    continue
                    
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in media_extensions:
                    file_path = os.path.join(root, file)
                    
                    # 确认文件存在并可访问
                    if not os.path.exists(file_path):
                        logger.error(f"文件不存在: {file_path}")
                        continue
                    
                    try:
                        # 尝试打开文件并保持文件句柄打开，防止文件被删除
                        file_handle = open(file_path, 'rb')
                        self.file_handles.append(file_handle)
                        
                        # 读取文件的前几个字节，确保文件可访问
                        file_handle.seek(0)
                        file_handle.read(10)
                        file_handle.seek(0)  # 重置文件指针
                    except Exception as e:
                        logger.error(f"文件无法访问: {file_path}, 错误: {str(e)}")
                        continue
                    
                    # 获取文件的修改时间作为备用排序依据
                    try:
                        mtime = os.path.getmtime(file_path)
                    except:
                        mtime = 0
                    
                    # 提取文件名中的数字作为排序键
                    file_name = file
                    number_match = re.search(r'_(\d+)', file_name)
                    sort_number = 999999  # 默认大数字，让没有数字的排在后面
                    
                    if number_match:
                        try:
                            sort_number = int(number_match.group(1))
                        except:
                            pass
                    
                    temp_files.append({
                        'id': hashlib.md5(file_path.encode()).hexdigest(),
                        'name': file_name,
                        'path': file_path,
                        'mtime': mtime,
                        'sort_number': sort_number,
                        'handle_index': len(self.file_handles) - 1  # 记录文件句柄索引
                    })
                    file_count += 1
                    if file_count % 100 == 0:
                        logger.info(f"已找到 {file_count} 个媒体文件")
        
        # 按文件名中的数字排序
        temp_files.sort(key=lambda x: (x['sort_number'], x['name']))
        logger.info("按资源名称数字顺序排序完成")
        
        # 转换为标准格式
        for file_info in temp_files:
            # 再次验证文件存在
            if os.path.exists(file_info['path']):
                # 创建一个副本，不包含handle_index
                media_file = {
                    'id': file_info['id'],
                    'name': file_info['name'],
                    'path': file_info['path'],
                    'sort_key': file_info['sort_number']
                }
                media_files.append(media_file)
            else:
                logger.error(f"添加到媒体列表前发现文件不存在: {file_info['path']}")
                # 尝试重新打开文件
                try:
                    handle_index = file_info.get('handle_index', -1)
                    if handle_index >= 0 and handle_index < len(self.file_handles):
                        # 关闭旧句柄
                        self.file_handles[handle_index].close()
                        # 重新打开文件
                        file_handle = open(file_info['path'], 'rb')
                        self.file_handles[handle_index] = file_handle
                        
                        # 添加到媒体文件列表
                        media_file = {
                            'id': file_info['id'],
                            'name': file_info['name'],
                            'path': file_info['path'],
                            'sort_key': file_info['sort_number']
                        }
                        media_files.append(media_file)
                        logger.info(f"成功重新打开文件: {file_info['path']}")
                except Exception as e:
                    logger.error(f"重新打开文件失败: {file_info['path']}, 错误: {str(e)}")
        
        logger.info(f"共找到 {len(media_files)} 个有效媒体文件，已按资源名称数字顺序排序")
        logger.info(f"保持打开的文件句柄数量: {len(self.file_handles)}")
        
        # 检查几个文件是否存在
        for i, file_info in enumerate(media_files[:5]):
            if os.path.exists(file_info['path']):
                logger.info(f"媒体文件{i+1}存在: {file_info['path']}")
            else:
                logger.error(f"媒体文件{i+1}不存在: {file_info['path']}")
                
        return media_files
    
    def parse_archive(self):
        """解析压缩包"""
        if not self.media_files:
            self.media_files = self._find_media_files()
        
        # 确保所有文件路径都存在
        valid_files = []
        for file_info in self.media_files:
            if os.path.exists(file_info['path']):
                valid_files.append(file_info)
            else:
                logger.error(f"文件不存在，跳过: {file_info['path']}")
        
        logger.info(f"有效文件数量: {len(valid_files)}/{len(self.media_files)}")
        
        for file_info in valid_files:
            yield file_info
    
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
    
    def _get_safe_filename(self, filename):
        """获取安全的文件名"""
        # 移除非法字符
        safe_name = re.sub(r'[\\/*?:"<>|]', '_', filename)
        
        # 确保文件名不为空
        if not safe_name or safe_name.startswith('.'):
            safe_name = f"file_{hashlib.md5(filename.encode()).hexdigest()[:8]}{os.path.splitext(filename)[1]}"
        
        return safe_name 