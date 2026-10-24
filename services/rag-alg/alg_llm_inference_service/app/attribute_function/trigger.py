from dataclasses import dataclass
import re


# todo 溯源触发
# 1.结束符溯源
# 2.两个\n\n进行溯源
# 3.判断当前语句的下一个的缩进是否一致，如果不一致，对当前语句进行溯源 （暂时不触发）
# 4.表格第一行和第二行不做溯源，（暂时不触发）
# 5. pending_lines 的字数， 超过50 溯源
@dataclass
class TriggerConfig:
    # todo 参数
    pending_lines = []  # 只针对于 单个\n ，保存单个\n前的字符，与后面的cur_text 一起去溯源
    table_count = 0  # 表格溯源触发。无效字段，在维护
    last_indent = 0  # 缩进  无效字段，在维护
    indent = 0  # 缩进  无效字段，在维护
    pending_count = 0  # pending_lines 的字数， 超过50 溯源
    cur_text = ""  # 字符累计字段


class TriggerPosition:
    BEFORE = 0
    AFTER = 1


class TriggerOutput:
    """
    flag: 溯源标记，取-1/1/0
        1: 确认触发溯源，触发后，清空当前语句
        0: 但前累计语句确认不触发溯源，清空当前语句，重新开始累计
        -1: 无法确定是否溯源，但是累计当前字符
    end_position: 触发当前判断结果的token结束位置，用于判断当前的token还是否需要参与下一次溯源计算
    attribute_text: 放入溯源模块的句子，仅在flag = 1时有意义。
    trigger_config: 触发历史变量
    """

    def __init__(self, trigger_config: TriggerConfig, end_position: int, attribute_text="", flag: int = -1):
        self.config = trigger_config
        self.flag = flag
        self.attribute_text = attribute_text
        self.delta = end_position


def trigger_by_rule(ch, trigger_config: TriggerConfig) -> TriggerOutput:
    """规则溯源触发判定，依据句末、段末、缩进判断是否添加溯源标记"""
    # todo: 补充末句的处理方式
    if trigger_config.pending_count >= 50:
        if trigger_config.pending_lines:
            lines = trigger_config.pending_lines
            trigger_config.pending_lines = []
            trigger_config.pending_count = 0
            return TriggerOutput(attribute_text="\n".join(lines),
                                 flag=1,
                                 trigger_config=trigger_config,
                                 end_position=TriggerPosition.BEFORE)

    if trigger_config.cur_text == "" and ch == " ":
        trigger_config.indent += 1
        return TriggerOutput(flag=-1,
                             trigger_config=trigger_config,
                             end_position=TriggerPosition.AFTER)

    if trigger_config.cur_text == "" and ch == "\t":
        trigger_config.indent += 4
        return TriggerOutput(flag=-1,
                             trigger_config=trigger_config,
                             end_position=TriggerPosition.AFTER)

    if ch == "\n\n":
        trigger_config.table_count = 0
        if trigger_config.pending_lines or trigger_config.cur_text:
            lines = trigger_config.pending_lines
            lines.append(trigger_config.cur_text)
            trigger_config.pending_lines = []
            trigger_config.pending_count = 0
            trigger_config.cur_text = ""
            return TriggerOutput(attribute_text="\n".join(lines),
                                 flag=1,
                                 trigger_config=trigger_config,
                                 end_position=TriggerPosition.BEFORE)
        else:
            return TriggerOutput(attribute_text="",
                                 flag=0,
                                 trigger_config=trigger_config,
                                 end_position=len(ch))

    # todo 开始累计增加待溯源文本
    trigger_config.cur_text += ch

    # 标题行之前的遗留内容触发溯源
    if trigger_config.cur_text == "#":  # 首字是# -> 标题 触发标题行前的所有溯源
        if trigger_config.pending_lines:
            lines = trigger_config.pending_lines
            trigger_config.pending_lines = []
            trigger_config.pending_count = 0

            return TriggerOutput(attribute_text="\n".join(lines),
                                 flag=1,
                                 trigger_config=trigger_config,
                                 end_position=TriggerPosition.BEFORE)

    # 表格行之前的遗留内容触发溯源
    if trigger_config.cur_text == "|":  # 首字是| -> 表格
        trigger_config.table_count += 1

        if trigger_config.pending_lines:
            lines = trigger_config.pending_lines
            trigger_config.pending_lines = []
            trigger_config.pending_count = 0
            return TriggerOutput(attribute_text="\n".join(lines),
                                 flag=1,
                                 trigger_config=trigger_config,
                                 end_position=TriggerPosition.BEFORE)

    # 自然句结尾触发溯源
    if ch in "。！？!?" and not trigger_config.cur_text.startswith("|"):
        attr_sentence = "\n".join(trigger_config.pending_lines) + "\n" + trigger_config.cur_text
        trigger_config.pending_lines = []
        trigger_config.pending_count = 0
        trigger_config.cur_text = ""

        return TriggerOutput(attribute_text=attr_sentence,
                             flag=1,
                             trigger_config=trigger_config,
                             end_position=TriggerPosition.AFTER)

    if ch == "\n":
        # 换行清空缩进
        trigger_config.last_indent = trigger_config.indent
        trigger_config.indent = 0
        if trigger_config.cur_text.strip() == "":  # \n\n -> 触发遗留内容
            # if trigger_config.pending_lines:
            #     lines = trigger_config.pending_lines
            #     trigger_config.pending_lines = []
            #     trigger_config.pending_count = 0
            #     return TriggerOutput(attribute_text="\n".join(lines),
            #                          flag=1,
            #                          trigger_config=trigger_config,
            #                          end_position=TriggerPosition.BEFORE)

            trigger_config.pending_count = 0
            trigger_config.table_count = 0
            trigger_config.cur_text = ""
        elif trigger_config.cur_text.startswith("#"):
            # 例："## 项目介绍 \n"，标题句不触发溯源
            attr_text = trigger_config.cur_text
            trigger_config.cur_text = ""
            return TriggerOutput(attribute_text=attr_text,
                                 flag=0,
                                 trigger_config=trigger_config,
                                 end_position=TriggerPosition.AFTER)

        elif trigger_config.cur_text.endswith(":\n") or trigger_config.cur_text.endswith("：\n"):
            # 例："有以下几点:\n"，冒号+换行结尾不溯源
            attr_text = trigger_config.cur_text
            trigger_config.cur_text = ""
            return TriggerOutput(attribute_text=attr_text,
                                 flag=0,
                                 trigger_config=trigger_config,
                                 end_position=TriggerPosition.AFTER)

        elif trigger_config.cur_text.startswith("```"):
            # # 例："'''\n"，代码行开头不溯源
            attr_text = trigger_config.cur_text
            trigger_config.cur_text = ""
            return TriggerOutput(attribute_text=attr_text,
                                 flag=0,
                                 trigger_config=trigger_config,
                                 end_position=TriggerPosition.AFTER)

        elif trigger_config.cur_text.startswith("|") and trigger_config.cur_text.endswith("|\n"):
            # markdown表格行不溯源
            attr_text = trigger_config.cur_text
            trigger_config.pending_lines = []
            trigger_config.pending_count = 0
            trigger_config.cur_text = ""

            return TriggerOutput(attribute_text=attr_text,
                                 flag=0,
                                 trigger_config=trigger_config,
                                 end_position=TriggerPosition.AFTER)  # 在换行前插入溯源标记
            # # 若表格启用溯源，则从表头开始
            # if trigger_config.table_count > 2:  # 表格第3行开始开始溯源，markdown前两行为表头行
            #     return TriggerOutput(attribute_text=attr_text,
            #                          flag=1,
            #                          trigger_config=trigger_config,
            #                          end_position=TriggerPosition.BEFORE)  # 在换行前插入溯源标记
            # else:
            #     return TriggerOutput(attribute_text=attr_text,
            #                          flag=0,
            #                          trigger_config=trigger_config,
            #                          end_position=TriggerPosition.AFTER)
        else:
            attr_text = trigger_config.cur_text
            trigger_config.pending_lines.append(attr_text)
            trigger_config.pending_count += len(attr_text)
            trigger_config.cur_text = ""
            return TriggerOutput(attribute_text=attr_text,
                                 flag=0,
                                 trigger_config=trigger_config,
                                 end_position=TriggerPosition.BEFORE)

    return TriggerOutput(attribute_text=trigger_config.cur_text,
                         flag=-1,
                         trigger_config=trigger_config,
                         end_position=TriggerPosition.AFTER)

    # # 处理末句
    # if cur_text:
    #     attribute_units.append(cur_text)
    #     attribute_flags.append(-1)
    #     pending_count += len(cur_text)
    #
    # update_earlier_flag()
    # if len(attribute_units) > 2 and attribute_units[-1][0] not in "-*#1234567890" and indent == 0 and attribute_units[-1][0] != '|':
    #     attribute_flags[-1] = 0
    #
    # for line, attr_flag in zip(attribute_units, attribute_flags):
    #     print(line.strip("\n"), attr_flag)
    #     print("-"*30)


def trigger_by_llm(ch, trigger_config: TriggerConfig) -> TriggerOutput:
    attr_match = re.search("\[(\d+)]", ch)
    if attr_match:
        return TriggerOutput(attribute_text="",
                             flag=1,
                             trigger_config=trigger_config,
                             end_position=TriggerPosition.AFTER)

    elif re.search("\[$", ch) or re.search("\[(\d+)$", ch):
        return TriggerOutput(attribute_text="",
                             flag=-1,
                             trigger_config=trigger_config,
                             end_position=TriggerPosition.AFTER)
    else:
        return TriggerOutput(attribute_text="",
                             flag=0,
                             trigger_config=trigger_config,
                             end_position=TriggerPosition.AFTER)

# if __name__ == '__main__':
#     answer = """
#     整体来看，2022年首轮土拍中民企的拿地占比为18%。
#
#     | 企业类型 | 拿地占比 |
#     |----------|----------|
#     | 民企     | 18%      |"""
#     # trigger(answer)
#
#     pending_answer = ""
#     for i, ch in enumerate(answer):
#         attribute_text, attr_flag = trigger2(pending_answer + ch)
