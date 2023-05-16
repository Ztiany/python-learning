import pandas as pd
import pdfplumber
import sqlite3
import uuid
import re


# =========================================================================
# 公共方法
# =========================================================================

def print_obj_list(divider, the_list):
    print(divider)
    for item in the_list:
        print(item)
    print()


#
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

pdf_path = "./document/Anti-TSHR.pdf"
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

    return f"{splits[0]}({bracket_contents[0]}){splits[1]}", bracket_contents[0], bracket_contents[1]


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


def parse_product_manufacturing_cer_num():
    return ""


def parse_product_manufacturer_name():
    manufacturer_name = drop_newline_character(pdf_df.loc[0, 1])
    return drop_duplicated_chinese(manufacturer_name)


product_guid = uuid.uuid4().__str__()
product_name_zh, product_name_en, product_test_method = parse_product_name()
product_registration_cer_num = parse_product_registration_cer_num()
product_manufacturing_cer_num = parse_product_manufacturing_cer_num()
product_manufacturer_name = parse_product_manufacturer_name()

print(
    f"product_guid = {product_guid}\n"
    f"product_name_zh = {product_name_zh}\n"
    f"product_name_en = {product_name_en}\n"
    f"product_test_method = {product_test_method}\n"
    f"product_registration_cer_num = {product_registration_cer_num}\n"
    f"product_manufacturing_cer_num = {product_manufacturing_cer_num}\n"
    f"product_manufacturer_name = {product_manufacturer_name}\n"
)


# =========================================================================
# 读取产品规格
# =========================================================================

def parse_R(origin_str):
    r_str_list = origin_str.replace("装量：", "").split("：")
    slash_index = r_str_list[1].index("/")
    return R(r_str_list[0], r_str_list[1][:slash_index])


def parse_rspec(origin_str):
    split = re.split(r"；", origin_str)
    return RSpec(split[0], list(map(lambda x: parse_R(x), split[1:])))


def map_rspec_to_rspec_calibrators(r_list, cal_str):
    if cal_str != "":
        return list(map(lambda item: RSpec(item.spec_name + "+校准品", item.r_list), r_list))
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


def parse_calibrators_str(origin_str):
    pattern = r"装量：(.*?)：(.*?)\/"
    matches = re.findall(pattern, origin_str)
    c_start, c_end = parse_c_str(matches[0][0])
    return Calibrators(c_start, c_end, matches[0][1])


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


class RSpec:
    def __init__(self, spec_name, r_list):
        self.guid = uuid.uuid4().__str__()
        self.spec_name = spec_name
        self.r_list = r_list

    def __str__(self):
        r_list_str = list(map(lambda x: x.__str__(), self.r_list))
        return f"spec_name = {self.spec_name}, r_list = {r_list_str}, guid = {self.guid}"


class R:
    def __init__(self, name, volume):
        self.name = name
        self.volume = volume

    def __str__(self):
        return f"name = {self.name}, volume = {self.volume}"


class Calibrators:
    def __init__(self, start, end, volume):
        self.start = start
        self.end = end
        self.volume = volume

    def __str__(self):
        return f"start = {self.start}, end = {self.end}, volume = {self.volume}"


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
calibrators = parse_calibrators_str(calibrators_str)
compound_volume = parse_compound_str(compound_str)
component_str_list = list(filter(lambda x: contains_R_num(x), drop_newline_character(pdf_df.loc[5, 1]).split("。")))
component_list = list(map(lambda x: drop_component_detail(x), component_str_list))

print_obj_list("规格----------------------------------", rspec_list)
print_obj_list("规格+----------------------------------", rspec_calibrators_list)
print("校准品----------------------------------\n", calibrators)
print("复溶液----------------------------------\n", compound_volume)
print_obj_list("成分----------------------------------", component_list)


# =========================================================================
# 存入数据库
# =========================================================================
def save_to_db():
    conn = sqlite3.connect('meditation_db.db3')
    cursor = conn.cursor()

    save_product_to_db(cursor)
    save_specs_to_db(cursor)
    save_components(cursor, rspec_list)
    save_components(cursor, rspec_calibrators_list)

    conn.commit()
    conn.close()


def save_components(cursor, the_rspec_list):
    # ProductSizeComponents
    component_list_data = []
    for component in component_list:
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
        rspec.guid, product_guid, "Fake", rspec.spec_name
    ), rspec_list))

    size_calibrators_data_list = list(map(lambda rspec: (
        rspec.guid, product_guid, "Fake", rspec.spec_name
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
