from docx import Document
import pandas as pd
import pdfplumber
import sqlite3
import uuid
import re
import os
import sys


# =========================================================================
# 配置信息
# =========================================================================

def find_params(arg_list, target_name, target_env_name=""):
    for params in arg_list:
        if "=" in params and target_name in params:
            return params.split("=")[1].strip()
    if target_env_name != "":
        return os.environ.get(target_env_name)
    return None


def check_params(params):
    return not (params is None) and params != "" and os.path.exists(params)


# pdf_path="./document/Anti-TSHR.pdf" excel_path="./document/table.xlsx" doc_path="./document/manufacturer_num/" db_path="./meditation_db.db3"
pdf_path = find_params(sys.argv, "pdf_path")
excel_path = find_params(sys.argv, "excel_path", "MEDITATION_EXCEL_PATH")
doc_path = find_params(sys.argv, "doc_path", "MEDITATION_DOC_PATH")
dp_path = find_params(sys.argv, "db_path", "MEDITATION_DB_PATH")

print()
print("读取到参数：")
print(f"  pdf_path = {pdf_path}\n  excel_path = {excel_path}\n  doc_path = {doc_path}\n  dp_path = {dp_path}\n")

if check_params(pdf_path) and check_params(excel_path) and check_params(doc_path) and check_params(dp_path):
    print("参数可用，继续运行。")
    print()
    print()
else:
    print('请输入正确的参数，比如：pdf_path="./document/Anti-TSHR.pdf" excel_path="./document/table.xlsx" '
          'doc_path="./document/manufacturer_num/" db_path="./meditation_db.db3"')
    print()
    print()
    raise Exception("程序终止！")


# =========================================================================
# 公共方法
# =========================================================================

def print_obj_list(divider, the_list):
    print(divider)
    for item in the_list:
        print(" ", item)
    print(divider)
    print()


def extract_unit(origin_str):
    """
    2×3.5mL to 3.5
    """
    x_index = origin_str.index("×")
    m_index = origin_str.index("m")
    return origin_str[x_index + 1: m_index]


def drop_newline_character(origin_str):
    return origin_str.replace("\n", "")


def drop_ch_bracket_character(origin_str):
    return origin_str.replace("（", "").replace("）", "")


def read_pdf_to_df(path):
    pdf_doc = pdfplumber.open(path)
    if len(pdf_doc.pages) > 0:
        first_page = pdf_doc.pages[0]
        tables = first_page.extract_tables()
        if len(tables) > 0:
            df = pd.DataFrame(tables[0])
            return df


def read_pdf_to_list(path):
    pdf_doc = pdfplumber.open(path)
    pdf_content = []
    for i in range(len(pdf_doc.pages)):
        page = pdf_doc.pages[i]
        page_content = page.extract_text().split('\n')[:-1]
        pdf_content = pdf_content + page_content
    return pdf_content


def is_chinese(c):
    return 0x4E00 <= ord(c) <= 0x9FA5


def drop_duplicated_chinese(origin_str):
    if not should_drop_duplicated_chinese(origin_str):
        return origin_str
    # 定义新字符串用于存储结果
    result = ""
    last_chinese_index = -1
    # 遍历原字符串
    for i in range(0, len(origin_str), 2):
        if i == len(origin_str) - 1:
            result += origin_str[i]
            break
        if not is_chinese(origin_str[i]) and not is_chinese(origin_str[i + 1]):
            last_chinese_index = i
            break
        if origin_str[i] == origin_str[i + 1]:
            result += origin_str[i]
        else:
            result = result + origin_str[i] + origin_str[i + 1]
    if last_chinese_index == -1:
        return result
    return result + origin_str[last_chinese_index: len(origin_str)]


# “粤粤械械注注准准20232400700”这种类型的才去重。
def should_drop_duplicated_chinese(origin_str):
    # 定义新字符串用于存储结果
    all_duplicated_chinese = True
    # 遍历原字符串
    for i in range(0, len(origin_str), 2):
        if i == len(origin_str) - 1 and is_chinese(origin_str[i]):
            all_duplicated_chinese = False
            break
        if not is_chinese(origin_str[i]) and not is_chinese(origin_str[i + 1]):
            break
        if is_chinese(origin_str[i]) and not is_chinese(origin_str[i + 1]):
            all_duplicated_chinese = False
            break
        if origin_str[i] != origin_str[i + 1]:
            all_duplicated_chinese = False
            break
    return all_duplicated_chinese


# =========================================================================
# 初始化
# =========================================================================


pdf_df = read_pdf_to_df(pdf_path)
pdf_lines = read_pdf_to_list(pdf_path)


# =========================================================================
# 读取产品信息
# =========================================================================

def parse_product_name():
    full_name = drop_newline_character(pdf_df.loc[3, 1])
    # 使用正则表达式拆分字符串
    pattern = r'（.+?）'
    splits = re.split(pattern, full_name)
    splits = list(filter(lambda x: x != "", splits))

    # 将括号内的内容匹配出来
    bracket_contents = re.findall(pattern, full_name)
    bracket_contents = list(map(lambda x: drop_ch_bracket_character(x), bracket_contents))

    return splits[0], f"{splits[0]}（{bracket_contents[0]}）{splits[1]}", bracket_contents[0], bracket_contents[1]


def parse_product_registration_cer_num():
    search_str1 = "注册证编号"
    search_str2 = "注注册册证证编编号号"
    target = ""
    for line in pdf_lines:
        if search_str1 in line or search_str2 in line:
            target = line
    if target.isspace():
        return ""
    split_target = target.split("：：")
    if len(split_target) == 0:
        split_target = target.split("：")
    if len(split_target) < 1:
        return ""
    return drop_duplicated_chinese(split_target[1])


def find_product_file(product_name):
    # 遍历文件夹
    for root, dirs, files in os.walk(doc_path):
        for file in files:
            file_path = os.path.join(root, file)
            if product_name in file_path:
                return file_path
    return ""


def find_string_in_document(target_path, search_string):
    document = Document(target_path)
    for paragraph in document.paragraphs:
        if search_string in paragraph.text:
            return paragraph.text


def parse_product_manufacturing_cer_num(product_name):
    product_file_path = find_product_file(product_name)
    if product_file_path == "":
        return ""
    manufacturing_cer_num_str = find_string_in_document(product_file_path, "生产许可证编号：")
    return manufacturing_cer_num_str.split("：")[1]


def parse_product_manufacturer_name():
    manufacturer_name = drop_newline_character(pdf_df.loc[0, 1])
    return drop_duplicated_chinese(manufacturer_name)


product_guid = uuid.uuid4().__str__()
product_pure_name_zh, product_name_zh, product_name_en, product_test_method = parse_product_name()
product_registration_cer_num = parse_product_registration_cer_num()
product_manufacturing_cer_num = parse_product_manufacturing_cer_num(product_pure_name_zh)
product_manufacturer_name = parse_product_manufacturer_name()

print("读取到【产品】信息：")
print("----------------------------------")
print(
    f"  product_guid = {product_guid}\n"
    f"  product_name_zh = {product_name_zh}\n"
    f"  product_name_en = {product_name_en}\n"
    f"  product_test_method = {product_test_method}\n"
    f"  product_registration_cer_num = {product_registration_cer_num}\n"
    f"  product_manufacturing_cer_num = {product_manufacturing_cer_num}\n"
    f"  product_manufacturer_name = {product_manufacturer_name}"
)
print("----------------------------------")
print()

# =========================================================================
# 读取产品规格
# =========================================================================

spec_num_df = pd.read_excel(excel_path)
spec_num_row: pd.Series = None


def find_spec_num(targe_product_name, target_spec_name):
    find_row(targe_product_name)
    if spec_num_row is None:
        return ""
    spec_num_list = spec_num_row[2].split("\n")
    spec_name_list = spec_num_row[7].split("\n")
    if len(spec_name_list) != len(spec_num_list):
        return ""
    for index, spec_name in enumerate(spec_name_list):
        if target_spec_name == spec_name:
            return spec_num_list[index]
    return ""


def find_row(targe_product_name):
    global spec_num_row
    if spec_num_row is None:
        index = -1
        for value in spec_num_df.iloc[:, 5]:
            index = index + 1
            if targe_product_name in value:
                spec_num_row = spec_num_df.iloc[index]
                break


def parse_R(origin_str):
    r_str_list = origin_str.replace("装量：", "").split("：")
    slash_index = r_str_list[1].index("/")
    return R(r_str_list[0], r_str_list[1][:slash_index])


def parse_rspec(origin_str):
    split = re.split(r"；", origin_str)
    spec_num = find_spec_num(product_pure_name_zh, split[0])
    return RSpec(split[0], spec_num, list(map(lambda x: parse_R(x), split[1:])))


def new_rspec_with_cal(item):
    spec_name = item.spec_name + "+校准品"
    spec_num = find_spec_num(product_pure_name_zh, spec_name)
    return RSpec(spec_name, spec_num, item.r_list)


def map_rspec_to_rspec_calibrators(r_list, cal_str):
    if cal_str != "":
        return list(map(lambda item: new_rspec_with_cal(item), r_list))
    return []


def parse_calibrators_and_compound_str(origin_str):
    calibrators_part = ""
    compound_part = ""
    compound_index = 0
    if "复溶液" in origin_str:
        compound_index = origin_str.index("复溶液")
        compound_part = origin_str[compound_index:]
    if "校准品" in origin_str:
        calibrators_part = origin_str[0:compound_index]
    return calibrators_part, compound_part


def c_str_to_num(c_str):
    return int(c_str.replace("C", ""))


def parse_c_str(origin_str):
    if "-" in origin_str:
        c_num_list = list(map(lambda s: c_str_to_num(s), origin_str.split("-")))
        start = c_num_list[0]
        end = c_num_list[1]
    else:
        start = c_str_to_num(origin_str)
        end = start
    return start, end


def parse_calibrators_str(name, origin_str):
    if origin_str == "":
        return None
    pattern = r"装量：(.*?)：(.*?)\/"
    matches = re.findall(pattern, origin_str)
    c_start, c_end = parse_c_str(matches[0][0])
    volume = matches[0][1]
    vn = volume.split("×")[0]
    vi = volume.split("×")[1]
    vc = int((int(vn) / (c_end - c_start + 1)))
    return Calibrators(name, c_start, c_end, f"{vc}×{vi}")


def parse_compound_str(origin_str):
    if origin_str == "":
        return ""
    match = re.search(r'：(.*?)\/', origin_str)
    if match:
        return match.group(1)
    return ""


def contains_R_num(origin_str):
    pattern = r"\(R[0-9]+\)"
    match = re.search(pattern, origin_str)
    if match:
        return True
    else:
        return False


def drop_component_detail(origin_str):
    pattern = r"\(R[0-9]+\)"
    index = origin_str.index("(R")
    r_num = re.findall(pattern, origin_str)[0].strip("()'")
    return Component(origin_str[:index], r_num)


def parse_calibrators_name(component_list):
    component_str = ""
    for c_str in component_list:
        if "校准品C" in c_str:
            component_str = c_str
            break
    component_str_index = component_str.find("校准品")
    if component_str_index == -1:
        return "校准品"
    return component_str[0:component_str_index + 3]


class RSpec:
    def __init__(self, spec_name, num, r_list):
        self.guid = uuid.uuid4().__str__()
        self.spec_name = spec_name
        self.num = num
        self.r_list = r_list

    def __str__(self):
        r_list_str = list(map(lambda x: x.__str__(), self.r_list))
        return f"spec_name = {self.spec_name}, num = {self.num}, r_list = {r_list_str}, guid = {self.guid}"


class R:
    def __init__(self, name, volume):
        self.name = name
        self.volume = volume

    def __str__(self):
        return f"name = {self.name}, volume = {self.volume}"


class Calibrators:
    def __init__(self, name, start, end, volume):
        self.name = name
        self.start = start
        self.end = end
        self.volume = volume

    def __str__(self):
        return f"name = {self.name} ,start = {self.start}, end = {self.end}, volume = {self.volume}"


class Component:
    def __init__(self, name, r_num):
        self.name = name
        self.r_num = r_num

    def __str__(self):
        return f"name = {self.name}, r_num = {self.r_num}"


spec_str_list = list(filter(lambda x: x != "", drop_newline_character(pdf_df.loc[4, 1]).split("规格")))
spec_str_list = [s[1:] for s in spec_str_list]
r_spec_str_list = list(filter(lambda x: not is_chinese(x[0]), spec_str_list))
calibrators_str, compound_str = parse_calibrators_and_compound_str(spec_str_list[len(spec_str_list) - 1])

rspec_list = list(map(parse_rspec, r_spec_str_list))
rspec_calibrators_list = map_rspec_to_rspec_calibrators(rspec_list, calibrators_str)

all_component_str_list = drop_newline_character(pdf_df.loc[5, 1]).split("。")
r_component_str_list = list(filter(lambda x: contains_R_num(x), all_component_str_list))
r_component_list = list(map(lambda x: drop_component_detail(x), r_component_str_list))
calibrators_name = parse_calibrators_name(all_component_str_list)

calibrators = parse_calibrators_str(calibrators_name, calibrators_str)
compound_volume = parse_compound_str(compound_str)

print("读取到【规格】信息：")
print_obj_list("----------------------------------", rspec_list)

print("读取到【规格 + 校准品】信息：")
print_obj_list("----------------------------------", rspec_calibrators_list)

print("读取到【校准品】信息：")
print("----------------------------------\n  ", calibrators)
print("----------------------------------\n")

print("读取到【复溶液容量】信息：")
print("----------------------------------\n  ", compound_volume)
print("----------------------------------\n")

print("读取到【成分】信息：")
print_obj_list("----------------------------------", r_component_list)


# =========================================================================
# 存入数据库
# =========================================================================
def save_to_db():
    conn = sqlite3.connect(dp_path)
    cursor = conn.cursor()

    print()
    print()
    print("开始入库...")
    try:
        save_product_to_db(cursor)
        save_specs_to_db(cursor)
        save_components(cursor, rspec_list)
        save_components(cursor, rspec_calibrators_list)
        save_calibrators(cursor)
        save_compound(cursor)
        print()
        print()
        print("入库成功，程序结束")
    except:
        print()
        print()
        print("入库失败，程序结束")
    finally:
        conn.commit()
        conn.close()


def save_compound(cursor):
    if compound_volume == "":
        return
    compound_list_data = []
    for spec in rspec_calibrators_list:
        compound_list_data.append((
            uuid.uuid4().__str__(),
            spec.guid,
            "复溶液",
            "复溶液",
            compound_volume,
            extract_unit(compound_volume)
        ))

    cursor.executemany(
        'INSERT INTO ProductSizeComponents '
        '(Id, ProductSizeId, ComponentName, Code, SizeName, Qty) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        compound_list_data
    )


def save_calibrators(cursor):
    if calibrators is None:
        return
    calibrators_list_data = []
    for spec in rspec_calibrators_list:
        index = calibrators.start
        while index <= calibrators.end:
            calibrators_list_data.append((
                uuid.uuid4().__str__(),
                spec.guid,
                calibrators.name + "C" + str(index),
                "C" + str(index),
                calibrators.volume,
                extract_unit(calibrators.volume)
            ))
            index = index + 1

    cursor.executemany(
        'INSERT INTO ProductSizeComponents '
        '(Id, ProductSizeId, ComponentName, Code, SizeName, Qty) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        calibrators_list_data
    )


def save_components(cursor, the_rspec_list):
    if len(the_rspec_list) == 0:
        return
    # ProductSizeComponents
    component_list_data = []
    for component in r_component_list:
        for spec in the_rspec_list:
            target_r = find_target_R(component, spec)
            component_list_data.append((
                uuid.uuid4().__str__(),
                spec.guid,
                component.name,
                target_r.name,
                target_r.volume,
                extract_unit(target_r.volume)
            ))
    cursor.executemany(
        'INSERT INTO ProductSizeComponents '
        '(Id, ProductSizeId, ComponentName, Code, SizeName, Qty) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        component_list_data
    )


def find_target_R(component, spec):
    for r in spec.r_list:
        if r.name == component.r_num:
            return r
    return None


def save_specs_to_db(cursor):
    size_data_list = list(map(lambda rspec: (
        rspec.guid, product_guid, rspec.num, rspec.spec_name
    ), rspec_list))

    size_calibrators_data_list = list(map(lambda rspec: (
        rspec.guid, product_guid, rspec.num, rspec.spec_name
    ), rspec_calibrators_list))

    cursor.executemany(
        'INSERT INTO ProductSizes (Id, ProductId, Code, Name) VALUES (?, ?, ?, ?)',
        size_data_list
    )
    cursor.executemany(
        'INSERT INTO ProductSizes (Id, ProductId, Code, Name) VALUES (?, ?, ?, ?)',
        size_calibrators_data_list
    )


def save_product_to_db(cursor):
    # Products
    product_data = (
        product_guid,
        product_name_zh,
        product_name_en,
        product_test_method,
        product_registration_cer_num,
        product_manufacturing_cer_num,
        product_manufacturer_name
    )
    cursor.execute(
        'INSERT INTO Products (Id, CnName, EnName,MethodName,CorCode,QsCode,CoName) VALUES (?, ?, ?, ?, ?, ?, ?)',
        product_data
    )


save_to_db()
