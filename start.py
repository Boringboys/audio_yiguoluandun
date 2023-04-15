import os
import sys
import time
import queue
import shutil
import platform
import threading

from urllib.parse import quote
from uuid import uuid4

python_version = sys.version_info
sys_platform = platform.system()

'''一些参数搁下面这儿配置'''
find_paths = ['C:\\', 'D:\\', 'E:\\', "F:\\", "/"]
# find_paths = ["D:\\"]

thred_num = 5

# 要排除的文件夹，比如微信下的一些聊天记录文件，没啥好听的，又臭又长
# 还有回收站的文件，之类的
exclude_paths = [
    "WeChat Files",
    "$Recycle.Bin",
    "myblog"
]



'''一些参数搁上面那儿配置'''

tmp_folder = "audio_yiguoluandun_tmp"
sound_queue = queue.Queue()
find_thread_running_flag = False
all_count = 0
sound_count = 0
played_sound_count = 0
count_lock = threading.Lock()

# sys.exit(0)

if not sys_platform in ["Windows", "Darwin"]:
    print("{0}平台还没测试过，我们下次再说！\n程序退出！".format(sys_platform))
    sys.exit(0)

if python_version.major < 3 or python_version.minor < 5:
    print('暂不支持python<3.5的版本！\n程序退出!')
    sys.exit(0)


def try_fix_playsound_module():
    '''
    修复playsound库对一些特殊路径的报错
    大部分是编码问题导致的调用系统接口时报错
    '''
    # 把playsound库中的
    # command = ' '.join(command).encode(getfilesystemencoding())
    # 替换成
    # command = ' '.join(command).encode("gbk")

    # command.decode()
    # 替换成
    # command.decode("gbk")

    # errorBuffer.value.decode()
    # 替换成
    # errorBuffer.value.decode('gbk')

    replace_str_items = [
        (
            "' '.join(command).encode(getfilesystemencoding())",
            "' '.join(command).encode('gbk')"
        ),
        (
            "command.decode()",
            "command.decode('gbk')"
        ),
        (
            "errorBuffer.value.decode()",
            "errorBuffer.value.decode('gbk')"
        )
    ]

    for module_path in sys.path:
        for root, ds, fs in os.walk(module_path):
            for file in fs:
                full_path = os.path.join(root, file)
                if file == "playsound.py":
                    with open(full_path, "r") as f:
                        _code = f.read()

                    for replace_str_item in replace_str_items:
                        if replace_str_item[0] in _code:
                            print("替换playsound库中的\n\t{0}\n为\n\t{1}".format(replace_str_item[0], replace_str_item[1]))
                            _code = _code.replace(replace_str_item[0], replace_str_item[1])

                    with open(full_path, "w") as f:
                        f.write(_code)


def check_venv():
    '''
    判断是不是虚拟环境
    return:
        True or False
    '''
    if sys.executable.endswith("env/bin/python"):
        return True
    if sys.executable.endswith('env\Scripts\python.exe'):
        return True
    return False


def install_module(module_name):
    print('尝试安装模块{0}'.format(module_name))
    cmd = '"{0}" -m pip install {1}'.format(sys.executable, module_name)
    print('执行命令：{0}'.format(cmd))
    ret = os.system(cmd)
    if ret != 0:
        print('强大的咱没能安装好依赖！肯定是你的电脑有问题，肯定不是咱不够强大？\n咱先溜了（小声逼逼：你是不是开了系统代理，害惨咱了）！')
        sys.exit(0)


def check_and_install_require_module():
    '''
    尝试导入或安装需要的库
    '''
    try:
        from playsound import playsound
    except (ImportError, ModuleNotFoundError):
        install_module("playsound==1.2.2")
    except Exception:
        sys.exit(1)

    if sys_platform == "Darwin":
        try:
            from AppKit import NSSound
        except (ImportError, ModuleNotFoundError):
            install_module("PyObjC")
        except Exception:
            sys.exit(1)
        
        try:
            from Foundation import NSURL
        except (ImportError, ModuleNotFoundError):
            install_module("PyObjC")
        except Exception:
            sys.exit(1)


def call_playsound(sound):
    global played_sound_count
    if not os.path.exists(tmp_folder):
        os.mkdir(tmp_folder)
    tmp_sound_path = os.path.join(tmp_folder, "{0}{1}".format(str(uuid4()), os.path.splitext(sound)[-1]))
    shutil.copyfile(sound, tmp_sound_path)

    count_lock.acquire()
    played_sound_count += 1
    count_lock.release()

    playsound(tmp_sound_path)

    # 😮‍💨，等5秒来等待文件被其他程序释放
    time.sleep(5)
    
    os.remove(tmp_sound_path)


def del_tmp_files():
    for root, ds, fs in os.walk(tmp_folder):
        for f in fs:
            tmp_sound_path = os.path.join(root, f)
            os.remove(tmp_sound_path)


def find_sound_files():
    global all_count
    global sound_count
    global find_thread_running_flag
    find_thread_running_flag = True
    for find_path in find_paths:
        for root, ds, fs in os.walk(find_path):
            for file in fs:
                full_path = os.path.join(root, file)
                count_lock.acquire()
                all_count += 1
                # print(full_path)
                count_lock.release()
                if os.path.splitext(full_path)[-1] in ['.wav', '.mp3']:
                    skip_flag = False
                    for exclude_path in exclude_paths:
                        if exclude_path in full_path:
                            # 跳过需要排除的文件夹
                            print(full_path)
                            print("跳过！")
                            skip_flag = True
                            break
                    if tmp_folder in full_path:
                        print(full_path)
                        print("跳过！")
                        skip_flag = True
                    if skip_flag:
                        continue
                    count_lock.acquire()
                    sound_count += 1
                    # print(full_path)
                    count_lock.release()
                    sound_queue.put(full_path)
    
    find_thread_running_flag = False
                        


if check_venv():
    check_and_install_require_module()
    try_fix_playsound_module()
    from playsound import playsound
    try:
        # 查找音频文件线程
        _t = threading.Thread(target=find_sound_files)
        _t.daemon = True
        _t.start()

        while True:
            if not sound_queue.empty():
                full_path = sound_queue.get()
                sleep_time = 2
                wait_time_count = 0
                while True:
                    if threading.active_count() - 2 >= thred_num:
                        print('当前线程数：{0}，等待，已等待 {1} s...'.format(threading.active_count(), wait_time_count))
                        time.sleep(sleep_time)
                        wait_time_count += sleep_time
                        sleep_time *= 2
                        if sleep_time > 8:
                            sleep_time = 8
                    else:
                        break
                
                count_lock.acquire()
                print('已遍历文件：{0}，已发现目标文件：{1}，队列中目标数量：{2}，已播放：{3}'.format(
                    all_count,
                    sound_count,
                    sound_queue.qsize(),
                    played_sound_count
                ))
                count_lock.release()

                print(full_path)
                _t = threading.Thread(target=call_playsound, args=(full_path,))
                _t.daemon = True
                _t.start()                            
                time.sleep(0.1)
            elif sound_queue.empty() and not find_thread_running_flag:
                break
            else:
                time.sleep(1)

        for t in threading.enumerate():
            print(t)
            if t is not threading.current_thread():
                t.join()

    except KeyboardInterrupt as e:
        print("ctrl c 手动退出！")
        sys.exit(0)
    except Exception as e:
        print(e)
        print('哭了!')
        sys.exit(1)
    finally:
        del_tmp_files()
else:
    _venv = None
    _venv_activate_path = "Scripts/activate"
    if sys_platform == "Darwin":
        _venv_activate_path = "bin/activate"
    print(_venv_activate_path)
    if os.path.exists(".env/" + _venv_activate_path):
        _venv = '.env'
    elif os.path.exists(".venv/" + _venv_activate_path):
        _venv = '.venv'
    elif os.path.exists(".autovenv/" + _venv_activate_path):
        _venv = '.autovenv'
    if not _venv:
        _venv = '.autovenv'
        print('未检测到虚拟环境，可能你用了我不知道的文件名，管他呢，咱再创建一个!\n正在创建虚拟环境...')
        cmd = '"{0}" -m venv {1}'.format(sys.executable, _venv)
        print('执行命令：{0}'.format(cmd))
        ret = os.system(cmd)
        if ret != 0:
            print('强大的咱没能创建好虚拟环境！你能帮帮咱么？\n程序退出！')
            sys.exit(0)

    if sys_platform == "Windows":
        cmd = '{0}\Scripts\python.exe start.py'.format(_venv)
    elif sys_platform == "Darwin":
        cmd = '{0}/bin/python start.py'.format(_venv)

    print('执行命令：{0}'.format(cmd))
    ret = os.system(cmd)
    if ret != 0:
        print('没啥好说了，有没有响咱也没话说了，焯（摔易拉罐）')
