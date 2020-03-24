from memory_profiler import profile

@profile
def foo():
    sum = 0
    for i in range(10000):
        sum += i
    return sum

if __name__ == "__main__" :
    # for i in range(10000):
    foo()

"""
python -m cProfile -o test1.out cProfileTest1.py

查看运行结果：

python -c "import pstats; p=pstats.Stats('test1.out'); p.print_stats()" >out1.log

查看排序后的运行结果：

python -c "import pstats; p=pstats.Stats('test1.out'); p.sort_stats('time').print_stats()" >out1.log

ncalls ： 函数的被调用次数
tottime ：函数总计运行时间，除去函数中调用的函数运行时间
percall ：函数运行一次的平均时间，等于tottime/ncalls
cumtime ：函数总计运行时间，含调用的函数运行时间
percall ：函数运行一次的平均时间，等于cumtime/ncalls
filename:lineno(function) 函数所在的文件名，函数的行号，函数名
"""

"""
使用memory_profiler分析内存使用情况
需要安装memory_profiler ：

pip install psutil
pip install memory_profiler

from memory_profiler import profile

@profile
def my_func():
    a = [1] * (10*6)
    b = [2] * (10*7)
    del b
    return a


"""