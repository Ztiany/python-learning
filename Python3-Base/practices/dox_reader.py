import docx


##################################################
# 用 python 把读取 world 文档，然后把 world 文档里面的所有标题都升一级，比如四级标题升级为三级标题，二级标题升级为一级标题，一级标题则保持不变。
# 然后把四级及以上标题改为正文加粗。【For Notion】
##################################################


def upgrade_headings(doc):
    for paragraph in doc.paragraphs:
        if paragraph.style.name is not None:
            if paragraph.style.name.startswith('Heading'):
                level = int(paragraph.style.name[-1])
                if level > 1:
                    new_level = level - 1
                    if new_level >= 4:
                        paragraph.style = doc.styles['Normal']
                        paragraph.runs[0].bold = True
                    else:
                        paragraph.style = doc.styles['Heading %d' % new_level]


def main():
    input_file = 'test.practices'
    output_file = 'output2.practices'

    doc = docx.Document(input_file)
    upgrade_headings(doc)
    doc.save(output_file)


if __name__ == '__main__':
    main()
