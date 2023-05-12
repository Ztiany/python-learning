import pdfplumber
import pandas as pd


def read_pdf(path):
    pdf = pdfplumber.open(path)
    if len(pdf.pages) > 0:
        first_page = pdf.pages[0]
        tables = first_page.extract_tables()
        if len(tables) > 0:
            df = pd.DataFrame(tables[0])
            return df


pdf_path = "./pdf/Anti-TSHR.pdf"
# pdf_path = "./pdf/BAP.pdf"

pdf_df = read_pdf(pdf_path)
print(pdf_df)
print(pdf_df.loc[4, 1].replace("\n", ""))

with pdfplumber.open(pdf_path) as pdf:
    content = ''
    for i in range(len(pdf.pages)):
        # 读取PDF文档第i+1页
        page = pdf.pages[i]

        # page.extract_text()函数即读取文本内容，下面这步是去掉文档最下面的页码
        page_content = '\n'.join(page.extract_text().split('\n')[:-1])
        print(page_content)
