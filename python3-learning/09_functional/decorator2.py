##################################################
# 装饰器：带参数的装饰器
##################################################

# 如果 decorator 本身需要传入参数，那就需要编写一个返回 decorator 的高阶函数
def log(text):
    def decorator(func):
        def wrapper(*args, **kw):
            print('%s %s():' % (text, func.__name__))
            return func(*args, **kw)

        return wrapper

    return decorator


@log('execute')
def now():
    print('2015-3-25')


# 相当于 log('execute')(now)
now()

# 首先执行 log('execute')，返回的是 decorator 函数，再调用返回的函数，参数是 now 函数，返回值最终是 wrapper 函数，所以下面 now.__name__ 结果是 wrapper
print(now.__name__)
