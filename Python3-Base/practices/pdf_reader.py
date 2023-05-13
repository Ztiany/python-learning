import pandas as pd
import pdfplumber
import uuid
import re


# =========================================================================
# 公共方法
# =========================================================================

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
    # 定义新字符串用于存储结果
    result = ""
    last_chinese_index = -1
    # 遍历原字符串
    for i in range(0, len(origin_str), 2):
        if i >= len(origin_str) - 1:
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


# =========================================================================
# 初始化
# =========================================================================

pdf_path = "./document/Anti-TSHR.pdf"
pdf_df = read_pdf_to_df(pdf_path)
pdf_lines = read_pdf_to_list(pdf_path)


# print(pdf_lines)
# print(pdf_df)


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
    company_name = drop_newline_character(pdf_df.loc[0, 1])
    return drop_duplicated_chinese(company_name)


product_guid = uuid.uuid4()
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
print("规格----------------------------------\n", drop_newline_character(pdf_df.loc[4, 1]).split("规格"))

print("成分----------------------------------\n", drop_newline_character(pdf_df.loc[5, 1]))
