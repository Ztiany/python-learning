##################################################
# 装饰器：装饰器的玩法【极客时间《左耳听风》编程范式-5】
##################################################

def make_html_tag(tag, *args, **kwds):
    print(tag)
    print(args)
    print(kwds)

    def real_decorator(fn):
        css_class = " class='{0}'".format(kwds["css_class"]) if "css_class" in kwds else ""
        print("css_class =", css_class)

        def wrapped(*args, **kwds):
            return "<" + tag + css_class + ">" + fn(*args, **kwds) + "</" + tag + ">"

        return wrapped

    return real_decorator


# 相当于：real_decorator("b","bold_css") (real_decorator("i","italic_css")(hello))
@make_html_tag(tag="b", css_class="bold_css")
@make_html_tag(tag="i", css_class="italic_css")
def hello():
    return "hello world"


print(hello())
print(hello.__name__)

# 输出：
# <b class='bold_css'><i class='italic_css'>hello world</i></b>
