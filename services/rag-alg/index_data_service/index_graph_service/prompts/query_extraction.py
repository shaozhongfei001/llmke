from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.prompts import HumanMessagePromptTemplate, ChatPromptTemplate

ner_instruction = (
""" 你是一个实体提取助手，负责从用户输入的查询语句中提取关键实体。
请根据以下步骤处理查询语句：
1. 识别实体类型：从查询语句中识别出人名、地点、时间、事件、角色等关键实体。
2. "提取关系：根据查询的意图，提取出与实体相关的关系或属性。
<注意> 保证实体名词的正确性,不要因为数量而抽取不正确的实体，实体语意明确
<注意> 注意识别动词、名词和形容词的区分，你可以根据语意形成新的实体，但是结果输出一定要保留原语句中的实体。
<注意> 返回的实体名称，尽量简短、精炼，字数不要太多，返回的实体请不要超过20个字符，返回的实体也不要单独一个汉字或者字符.
<注意> 抽取的实体中如果有 '逗号(,)'，'顿号(、)'，需要拆分成多个实体，保证每个返回的实体都是独立的，不要多个实体名词在一个里面
<注意> 只返回要求正确的实体名称，不要一些不明确的，错误的，有歧义的.
###################################
示例 1:
查询语句: 李白在哪个朝代出生
提取结果:
<keyword> ["李白", "朝代", "出生"]
###################################
示例 2: 
查询语句: 《红楼梦》是谁写的？
提取结果:
<keyword> ["红楼梦", "作者"]
###################################
"""
)

ner_user_input = """查询语句:{user_input}\n 提取结果："""
ner_prompts = ChatPromptTemplate.from_messages([SystemMessage(ner_instruction),
                                                HumanMessagePromptTemplate.from_template(ner_user_input)])