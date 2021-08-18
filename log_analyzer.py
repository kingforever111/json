import re
import json
import pandas as pd
import seaborn as sns
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from NovishLogger import logger

FLAG_SAVE = True
OUTPUT = 'result.log'
t0, u0 = 0, 0
JSON_ANALYSIS_DICT = {'ok': [], 'ng': []}
""" THRES """
THRES_JSON_DATE = ('2021-08-10 00:00:00', '3000-01-01 00:00:00')
THRES_JSON_INTERVAL = (3, 1e+8)  # second
THRES_OS_DATE = ('2000-01-01 00:00:00', '3000-01-01 00:00:00')
THRES_OS_SYNC_CHECK = '2021-01-01 00:00:00'
THRES_OS_RAM = (0, 10000)  # mb
THRES_OS_CPU = (0, 1000)  # %
THRES_OS_GPU_T = (0, 1000)  # C
THRES_OS_CPU_T = (0, 1000)  # C
THRES_DEBUG_DATE = ('2000-01-01 00:00:00', '3000-01-01 00:00:00')
THRES_DEBUG_MODEL = 0.24  # s


def set_axis_locator(ax, flag='DH'):
    if flag == 'HM':
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y%m%d-%H'))
        ax.xaxis.set_minor_locator(mdates.MinuteLocator(interval=15))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter('%M'))
    elif flag == 'DH':
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y%m%d'))
        ax.xaxis.set_minor_locator(mdates.HourLocator(interval=2))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter('%H'))


def get_timestamp(date):
    try:
        t = datetime.strptime(date, '%Y-%m-%d %H:%M:%S').timestamp()
    except:
        t = datetime.strptime(date, '%Y-%m-%d %H:%M:%S %f').timestamp()
    return t


def get_timestamp_format(date, d_format):
    try:
        t = datetime.strptime(date, d_format).timestamp()
    except:
        t = datetime.strptime(date, '%Y-%m-%d %H:%M:%S %f').timestamp()
    return t


def get_datetime(t):
    return datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S.%f')


def get_datetime_obj(date):
    return datetime.strptime(date, '%Y-%m-%d %H:%M:%S')


def mean(obj):
    return sum(obj) // len(obj)


def visualized(items):
    for k in items:
        if not items[k]['count']: return
    f, axs = plt.subplots(nrows=2, ncols=2, figsize=(50, 50))
    # plt.gcf().autofmt_xdate()
    ax_list = [axs[m, n] for m in range(2) for n in range(2)]
    sns.set_theme()

    for k, ax in zip(items, ax_list):
        ax.tick_params(pad=10)
        ax.set_title(items[k]['label'])
        set_axis_locator(ax)
        data = items[k]['data']
        for item in data:
            item['date'] = get_datetime_obj(item['date'])
        data = pd.DataFrame(data)
        sns.lineplot(x='date', y='value', data=data, ax=ax)
    plt.show()


logger.info(f'开始检查{THRES_JSON_DATE[0]}到{THRES_JSON_DATE[1]}的json包信息')
THRES_JSON_DATE = [get_timestamp(date) for date in THRES_JSON_DATE]
THRES_OS_DATE = [get_timestamp(date) for date in THRES_OS_DATE]
THRES_DEBUG_DATE = [get_timestamp(date) for date in THRES_DEBUG_DATE]
THRES_OS_SYNC_CHECK = get_timestamp(THRES_OS_SYNC_CHECK)
PATTERN_JSON = re.compile(r'^(.{10}) at (.{8}).?(\d{1,3})? INFO.*Intersection')
PATTERN_JSON_U = re.compile(r'\'U\': \'(.{10})\'')
PATTERN_OS = re.compile(r'^(.{10}) (.{8}),')
PATTERN_OS_RAM = re.compile(r'RAM (\d{1,4})')
PATTERN_OS_CPU = re.compile(r'(\d+)%@\d+')
PATTERN_OS_GPU_T = re.compile(r'GPU@([\d\.]+)C')
PATTERN_OS_CPU_T = re.compile(r'CPU@([\d\.]+)C')
""" DEBUG """
PATTERN_DEBUG = re.compile(r'^(.{10}) at (.{8}).?(\d{1,3})? DEBUG')
PATTERN_DEBUG_MODEL = re.compile(r'模型\d检测\d耗费([\d\.e-]*)')
PATTERN_DEBUG_STARTUP = re.compile(r'现在1个子进程ready')


class LogAnalyzer:
    def __init__(self, road_id, json_result_path):
        self.json_result_path = json_result_path
        self.road_id = road_id
        self.F = Path(OUTPUT).open('a') if FLAG_SAVE else None
        """ JSON PACKETS """
        self.RESULTS_JSON = {'data': [], 'count': 0}
        """ OS STATUS """
        self.RESULTS_OS = {
            'ram': {'label': 'Memory', 'data': [], 'count': 0},
            'cpu': {'label': 'CPU', 'data': [], 'count': 0},
            'gpu_t': {'label': 'GPU Temperature', 'data': [], 'count': 0},
            'cpu_t': {'label': 'CPU Temperature', 'data': [], 'count': 0}
        }
        self.RESULTS_DEBUG = {
            'model': {'data': [], 'count': 0},
            'startup': {'data': [], 'count': 0}
        }
        self.flag_time_sync_checked = False

    def unit_json(self, line):
        global t0, u0
        date = ' '.join(PATTERN_JSON.findall(line)[0]).strip()
        t = get_timestamp(date)
        if THRES_JSON_DATE[0] < t < THRES_JSON_DATE[1]:
            if FLAG_SAVE: self.F.write(line)
            client_json_time = [int(t) for t in PATTERN_JSON_U.findall(line)]
            u = [get_datetime(t) for t in client_json_time]
            # print(THRES_OS_SYNC_CHECK)
            # print(client_json_time[0])
            if client_json_time[0] < THRES_OS_SYNC_CHECK and not self.flag_time_sync_checked:
                logger.warning(f'{self.road_id}路口时间不同步: {t}')
                self.flag_time_sync_checked = True
            interval = t - t0
            if t0 != 0 and THRES_JSON_INTERVAL[0] < interval < THRES_JSON_INTERVAL[1]:
                self.RESULTS_JSON['data'].append({
                    'interval': round(interval, 2),
                    'server': (get_datetime(t0), get_datetime(t)),
                    'client': (u0, u),
                })
            t0 = t
            u0 = u

    def unit_os(self, line):
        date = ' '.join(PATTERN_OS.findall(line)[0]).strip()
        t = get_timestamp(date)
        if THRES_OS_DATE[0] < t < THRES_OS_DATE[1]:
            if FLAG_SAVE: self.F.write(line)
            date_obj = date
            ram = int(PATTERN_OS_RAM.findall(line)[0])
            if THRES_OS_RAM[0] < ram < THRES_OS_RAM[1]:
                self.RESULTS_OS['ram']['data'].append({'date': date_obj, 'value': ram})
            cpu = mean(list(map(int, PATTERN_OS_CPU.findall(line))))
            if THRES_OS_CPU[0] < cpu < THRES_OS_CPU[1]:
                self.RESULTS_OS['cpu']['data'].append({'date': date_obj, 'value': cpu})
            gpu_t = float(PATTERN_OS_GPU_T.findall(line)[0])
            if THRES_OS_GPU_T[0] < gpu_t < THRES_OS_GPU_T[1]:
                self.RESULTS_OS['gpu_t']['data'].append({'date': date_obj, 'value': gpu_t})
            cpu_t = float(PATTERN_OS_CPU_T.findall(line)[0])
            if THRES_OS_CPU_T[0] < cpu_t < THRES_OS_CPU_T[1]:
                self.RESULTS_OS['cpu_t']['data'].append({'date': date_obj, 'value': cpu_t})

    def unit_debug(self, line):
        date = ' '.join(PATTERN_DEBUG.findall(line)[0]).strip()
        t = get_timestamp(date)
        if THRES_DEBUG_DATE[0] < t < THRES_DEBUG_DATE[1]:
            if FLAG_SAVE: self.F.write(line)
            result = PATTERN_DEBUG_MODEL.findall(line)
            if result:
                duration = eval(result[0])
                if duration > THRES_DEBUG_MODEL:
                    self.RESULTS_DEBUG['model']['data'].append(line)
            result = PATTERN_DEBUG_STARTUP.findall(line)
            if result:
                self.RESULTS_DEBUG['startup']['data'].append(line)

    def handler(self):
        if self.F:
            self.F.close()
            p = OUTPUT.split('.')
            Path(OUTPUT).rename('%s_%s.%s' % (p[0], datetime.now().strftime('%Y-%m-%d_%H-%M-%S'), p[1]))

    def counter(self):
        """
        Count the number of
        :return:
        """
        self.RESULTS_JSON['count'] = len(self.RESULTS_JSON['data'])
        interval_less_5_count = 0
        interval_large_5_count = 0
        for d in self.RESULTS_JSON['data']:
            if d['interval'] <= 5:
                interval_less_5_count += 1
            else:
                interval_large_5_count += 1
        self.RESULTS_JSON['interval_less_5_count'] = interval_less_5_count
        self.RESULTS_JSON['interval_large_5_count'] = interval_large_5_count

        for obj in [self.RESULTS_OS, self.RESULTS_DEBUG]:
            for k in obj:
                obj[k]['count'] = len(obj[k]['data'])

    def printer(self):
        if self.RESULTS_JSON['count']:
            print('* JSON PACKETS')
            print(json.dumps(self.RESULTS_JSON, indent=4, ensure_ascii=False), '\n\n')
            ng_count = self.RESULTS_JSON['count']
            # interval_less_5_count = self.RESULTS_JSON['interval_less_5_count']
            interval_large_5_count = self.RESULTS_JSON['interval_large_5_count']
            logger.warning(f'{self.road_id}路口接收json包异常，异常{ng_count}次，大于5秒: {interval_large_5_count}次')
            JSON_ANALYSIS_DICT['ng'].append(self.road_id)
            data = json.dumps(self.RESULTS_JSON, indent=4, ensure_ascii=False)
            with open(self.json_result_path, 'a', encoding='utf-8') as f:
                f.write(data)
                f.close()
        else:
            logger.info(f'{self.road_id}路口接收json包正常')
            JSON_ANALYSIS_DICT['ok'].append(self.road_id)
        if 0 < self.RESULTS_OS['ram']['count'] < 100:
            print('* OS STATUS')
            print(json.dumps(self.RESULTS_OS, indent=4, ensure_ascii=False))
        if any([self.RESULTS_DEBUG[k]['count'] for k in self.RESULTS_DEBUG]):
            print('* DEBUG')
            print(json.dumps(self.RESULTS_DEBUG, indent=4, ensure_ascii=False), '\n\n')

    def analyze(self, file):
        print(f'分析{file}')
        with open(file, encoding='utf-8') as f:
            for line in f:
                if PATTERN_JSON.match(line):
                    # print('分析Json')
                    self.unit_json(line)
                elif PATTERN_OS.match(line):
                    # print('分析OS')
                    self.unit_os(line)
                elif PATTERN_DEBUG.match(line):
                    # print('分析debug')
                    self.unit_debug(line)
        # handler()

    def display(self):
        self.counter()
        self.printer()
        visualized(self.RESULTS_OS)


if __name__ == '__main__':
    # import sys
    #
    # if len(sys.argv) == 2:
    #     file = sys.argv[1]
    # else:
    #     file = '0\INFO.2021-08-04_15-25-46_799323.log'
    # main(file)
    #
    # 分析结果存储位置
    json_result_path = 'json_results/0810/'
    import os

    # json包所在位置
    dir_path = 'json_received/20210812/'
    if os.path.isdir(dir_path):
        for i in range(0, 31):
            dir_path_numbered = f'{dir_path}/{i}/'
            if os.path.isdir(dir_path_numbered):
                json_result_filepath = f'{json_result_path}/{i}.txt'
                if not os.path.exists(json_result_path):
                    os.makedirs(json_result_path)
                logger.info(f'分析{i}路口日志: {dir_path_numbered}')
                analyzer = LogAnalyzer(i, json_result_filepath)
                filelist = os.listdir(dir_path_numbered)
                for file_name in filelist:
                    subfile_path = f'{dir_path_numbered}/{file_name}'
                    logger.info(f'查看{i}路口日志文件名是否在区间范围: {subfile_path}')
                    log_filename_list = file_name.split('.')
                    if len(log_filename_list) > 2:
                        log_time = log_filename_list[1]
                        time_str_list = log_time.split('_')
                        date_str = time_str_list[0]
                        time_str = time_str_list[1]
                        timestamp = get_timestamp_format(f'{date_str}-{time_str}', '%Y-%m-%d-%H-%M-%S')
                        if THRES_JSON_DATE[0] - 48 * 3600 < timestamp < THRES_JSON_DATE[1]:
                            logger.info(f'分析{i}路口日志: {subfile_path}')
                            analyzer.analyze(subfile_path)
                        else:
                            logger.debug(f'不分析{i}路口日志: {subfile_path}')
                    else:
                        logger.info(f'分析{i}路口日志: {subfile_path}')
                        analyzer.analyze(subfile_path)
                analyzer.display()
            else:
                print(f'{i}路口日志不存在:{dir_path_numbered}')

    logger.info(f'json包信息检查完毕,更多详情请看{json_result_path}里的信息')
    logger.info(f'检查结果为{JSON_ANALYSIS_DICT}')
