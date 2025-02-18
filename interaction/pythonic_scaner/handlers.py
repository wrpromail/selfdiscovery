import subprocess
import re
import os
import pwd
from datetime import datetime
from typing import List, Dict, Optional
import psutil
#import pynvml
import pytz


def get_disk_usage():
    """
    获取物理磁盘使用情况，排除系统相关分区和虚拟设备
    """
    try:
        df_output = subprocess.check_output(['df', '-h'], universal_newlines=True)
        disks = []
        lines = df_output.strip().split('\n')

        # 定义要排除的文件系统类型、设备或挂载点
        exclude_patterns = [
            '/dev/loop',  # snap包使用的loop设备
            'tmpfs',  # 临时文件系统
            'udev',  # 设备文件系统
            'devtmpfs',  # 设备临时文件系统
            '/snap/',  # snap相关挂载点
        ]

        # 定义要排除的挂载点
        exclude_mounts = {
            '/boot',  # 启动分区
            '/boot/efi',  # EFI系统分区
            '/efi'  # 某些系统上的EFI分区挂载点
        }

        for line in lines[1:]:
            parts = [part for part in line.split(' ') if part]

            # 检查是否应该排除这个设备
            should_exclude = any(pattern in parts[0] for pattern in exclude_patterns)
            # 检查挂载点是否应该排除
            mount_point = parts[5]
            should_exclude = should_exclude or any(mount_point.startswith(m) for m in exclude_mounts)

            if should_exclude:
                continue

            # 只处理以/dev/开头的设备
            if parts[0].startswith('/dev/'):
                # 转换容量到GB
                total = float(re.sub('[A-Za-z]', '', parts[1]))
                used = float(re.sub('[A-Za-z]', '', parts[2]))

                # 单位转换
                if 'T' in parts[1]:
                    total *= 1024  # TB to GB
                elif 'M' in parts[1]:
                    total /= 1024  # MB to GB

                if 'T' in parts[2]:
                    used *= 1024  # TB to GB
                elif 'M' in parts[2]:
                    used /= 1024  # MB to GB

                disk_info = {
                    'mount_point': mount_point,
                    'total_gb': round(total, 2),
                    'used_gb': round(used, 2),
                    'usage_percent': parts[4],
                    'filesystem': parts[0]
                }
                disks.append(disk_info)

        return disks

    except subprocess.CalledProcessError as e:
        print(f"Error executing df command: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def scan_large_files_fast(mount_point: str, total_size_gb: Optional[float] = None, max_depth: int = 3,
                          limit: int = 30) -> List[Dict]:
    """
    使用 du 命令快速扫描指定挂载点下的大文件和目录
    
    Args:
        mount_point: 挂载点路径
        total_size_gb: 磁盘总容量（GB），如果不指定则使用10GB作为基准
        max_depth: 最大递归深度，默认为3
        limit: 返回结果的最大数量，默认30
    """
    # 确保mount_point没有末尾的斜杠
    mount_point = mount_point.rstrip('/')

    # 设置大小门槛（KB）
    threshold_kb = int((total_size_gb * 0.01 if total_size_gb else 10) * 1024 * 1024)
    results = []

    def get_owner(path: str) -> str:
        """获取文件所有者"""
        try:
            stat_info = os.stat(path)
            uid = stat_info.st_uid
            try:
                return pwd.getpwuid(uid).pw_name
            except KeyError:
                return str(uid)
        except (OSError, KeyError):
            return "unknown"

    def format_size(size_kb: float) -> str:
        """将KB转换为人类可读的格式"""
        size_bytes = size_kb * 1024
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f}TB"

    def filter_nested_paths(results: List[Dict]) -> List[Dict]:
        """
        过滤掉嵌套的路径，只保留最上层的目录
        如果子目录大小与父目录相同或非常接近（差异<1%），则过滤掉子目录
        """
        filtered_results = []
        size_threshold_ratio = 0.99  # 大小相似度阈值（99%）

        # 按路径长度排序，确保先处理上层目录
        sorted_results = sorted(results, key=lambda x: len(x['path'].split('/')))

        def is_subpath_with_similar_size(path: str, size_kb: int, processed_paths: List[Dict]) -> bool:
            """检查是否是已处理路径的子路径，且大小相似"""
            for item in processed_paths:
                parent_path = item['path']
                if path.startswith(parent_path + '/'):
                    # 计算大小比例
                    size_ratio = size_kb / item['size_kb']
                    if size_ratio >= size_threshold_ratio:
                        return True
            return False

        for item in sorted_results:
            path = item['path']
            size_kb = item['size_kb']

            # 检查是否是已处理路径的子路径且大小相似
            if not is_subpath_with_similar_size(path, size_kb, filtered_results):
                filtered_results.append(item)

        return filtered_results

    try:
        cmd = [
            'du',
            '-ak',
            f'--max-depth={max_depth}',
            f'--threshold={threshold_kb}',
            mount_point
        ]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        for line in process.stdout:
            try:
                size_kb, path = line.strip().split('\t')
                size_kb = int(size_kb)

                # 跳过根目录
                if path == mount_point:
                    continue

                # 验证大小是否超过阈值
                if size_kb < threshold_kb:
                    continue

                try:
                    stat_info = os.stat(path)
                    mtime = datetime.fromtimestamp(stat_info.st_mtime)

                    # 将路径转换为相对路径
                    relative_path = path[len(mount_point):].lstrip('/')

                    results.append({
                        'path': relative_path,  # 使用相对路径
                        'size': format_size(size_kb),
                        'size_kb': size_kb,  # 用于排序
                        'owner': get_owner(path),
                        'modified_time': mtime.strftime('%Y-%m-%d %H:%M:%S')
                    })
                except (OSError, IOError) as e:
                    continue

            except ValueError:
                continue

        process.wait()

        if process.returncode != 0:
            stderr = process.stderr.read()
            print(f"Error running du command: {stderr}")

        # 按大小降序排序
        results.sort(key=lambda x: x['size_kb'], reverse=True)

        # 过滤嵌套路径
        results = filter_nested_paths(results)

        # 限制结果数量
        results = results[:limit]

        # 移除size_kb字段
        for item in results:
            del item['size_kb']

        return results

    except subprocess.CalledProcessError as e:
        print(f"Error executing du command: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []


def get_gpu_info() -> Dict:
    """
    获取GPU信息并返回结构化数据

    Returns:
        Dict: 包含所有GPU信息的字典，结构如下：
        {
            'timestamp': str,
            'gpus': [
                {
                    'id': int,
                    'name': str,
                    'temperature': int,
                    'fan_speed': int,
                    'power': {
                        'current': float,
                        'limit': float
                    },
                    'utilization': int,
                    'memory': {
                        'total': int,
                        'used': int,
                        'free': int,
                        'used_percent': float
                    },
                    'processes': [
                        {
                            'pid': int,
                            'name': str,
                            'used_memory': int,
                            'used_memory_percent': float
                        },
                        ...
                    ]
                },
                ...
            ]
        }
    """
    try:
        import pynvml
        pynvml.nvmlInit()

        result = {
            'timestamp': datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S'),
            'gpus': []
        }

        device_count = pynvml.nvmlDeviceGetCount()

        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)

            # 获取基本信息
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode('utf-8')

            # 获取使用率
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)

            # 构建GPU信息字典
            gpu_info = {
                'id': i,
                'name': name,
                'temperature': pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU),
                'fan_speed': pynvml.nvmlDeviceGetFanSpeed(handle),
                'power': {
                    'current': pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0,
                    'limit': pynvml.nvmlDeviceGetEnforcedPowerLimit(handle) / 1000.0
                },
                'utilization': utilization.gpu,
                'memory': {
                    'total': int(memory_info.total / 1024 ** 2),  # 转换为MB
                    'used': int(memory_info.used / 1024 ** 2),
                    'free': int(memory_info.free / 1024 ** 2),
                    'used_percent': round(memory_info.used / memory_info.total * 100, 2)
                },
                'processes': []
            }

            # 获取进程信息
            try:
                processes = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
                for proc in processes:
                    try:
                        process_name = pynvml.nvmlSystemGetProcessName(proc.pid)
                        if isinstance(process_name, bytes):
                            process_name = process_name.decode('utf-8')
                    except:
                        process_name = "N/A"

                    gpu_info['processes'].append({
                        'pid': proc.pid,
                        'name': process_name,
                        'used_memory': int(proc.usedGpuMemory / 1024 ** 2),  # 转换为MB
                        'used_memory_percent': round(proc.usedGpuMemory / memory_info.total * 100, 2)
                    })
            except Exception as e:
                gpu_info['processes'] = []
                gpu_info['process_error'] = str(e)

            result['gpus'].append(gpu_info)

        return result

    except Exception as e:
        return {
            'error': str(e),
            'timestamp': datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        }

    finally:
        try:
            pynvml.nvmlShutdown()
        except:
            pass


def get_process_info(pid_list: List[int]) -> List[Dict]:
    """
    获取指定PID列表的进程信息

    Args:
        pid_list (List[int]): PID列表

    Returns:
        List[Dict]: 进程信息列表，每个进程包含以下信息：
        {
            'pid': int,                # 进程ID
            'exists': bool,            # 进程是否存在
            'user': str,              # 进程所属用户
            'create_time': str,       # 创建时间
            'cmdline': str,           # 完整命令行
            'error': Optional[str]    # 错误信息（如果有）
        }
    """
    result = []

    for pid in pid_list:
        process_info = {
            'pid': pid,
            'exists': False,
            'error': None
        }

        try:
            # 检查进程是否存在
            if not psutil.pid_exists(pid):
                process_info['error'] = f"进程不存在"
                result.append(process_info)
                continue

            # 获取进程对象
            proc = psutil.Process(pid)

            # 获取基本信息
            process_info.update({
                'exists': True,
                'user': proc.username(),
                'create_time': datetime.fromtimestamp(proc.create_time()).strftime('%Y-%m-%d %H:%M:%S'),
                'cmdline': ' '.join(proc.cmdline()) if proc.cmdline() else proc.name()
            })

        except psutil.NoSuchProcess:
            process_info['error'] = "进程不存在"
        except psutil.AccessDenied:
            process_info['error'] = "访问被拒绝"
        except Exception as e:
            process_info['error'] = str(e)

        result.append(process_info)

    return result
