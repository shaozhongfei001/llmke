from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.prompts import HumanMessagePromptTemplate, ChatPromptTemplate


system_prompt = """
-目标-
给定一个可能与此活动相关的文本文档和一个实体类型列表，从文本中识别出所有属于这些类型的实体，并识别出这些实体之间的关系。

-步骤-
1. 识别所有实体。对于每个识别的实体，提取以下信息：
- entity_name: 实体的名称，若为英文则首字母大写，不要出现代词。请使用完整名字来代替
- entity_type: 实体类型中的一个
将每个实体格式化为 ("entity"::<entity_name>::<entity_type>)

2. 从步骤1中识别的实体中，识别出所有*明显相关*的（source_entity, target_entity）对。
对于每对相关实体，提取以下信息：
- relation_name: 关系名称
- source_entity: 源实体的名称，如步骤1中所识别
- target_entity: 目标实体的名称，如步骤1中所识别
- relationship_description: 解释为什么你认为源实体和目标实体是相关的
将每个关系格式化为 ("relationship"::<relation_name>::<source_entity>::<target_entity>::<relationship_description>)

3.用中文返回输出，作为步骤1和2中识别的所有实体和关系的单一列表。使用****作为列表分隔符。
4. 完成后，输出########

######################
-示例-
######################
示例1:
Entity_types: 组织, 人
Text:
Verdantis的中央机构定于周一和周四举行会议，该机构计划于周四下午1:30 PDT发布其最新政策决定，随后将举行新闻发布会，中央机构主席Martin Smith将回答提问。投资者预计市场战略委员会将保持基准利率在3.5%-3.75%的范围内不变。
######################
Output:
("entity"::中央机构::组织)

("entity"::MARTIN SMITH::人)

("entity"::市场战略委员会::组织)

("relationship"::担任主席::MARTIN SMITH::中央机构::Martin Smith是中央机构的主席，并将在新闻发布会上回答问题)
########

######################
示例2:
Entity_types: 组织
Text:
TechGlobal（TG）的股票在周四全球交易所的首日交易中飙升。但IPO专家警告称，这家半导体公司在公开市场的首次亮相并不能预示其他新上市公司的表现。
TechGlobal曾是一家上市公司，2014年被Vision Holdings私有化。这家老牌芯片设计公司表示，其产品为85%的高端智能手机提供动力。
######################
Output:
("entity"::TECHGLOBAL::组织)

("entity"::VISION HOLDINGS::组织)

("relationship"::收购::VISION HOLDINGS::TECHGLOBAL::TechGlobal2014年被Vision Holdings私有化)
########
"""

user_prompt = """
######################
-真实数据-
######################
Entity_types: {entity_types}
Text: {passage}
######################
Output:"""

CONTINUE_PROMPT = "在上一次提取中，许多实体和关系被遗漏了。请记住，只输出与之前提取的类型匹配的实体。使用相同的格式将它们添加在下面："
LOOP_PROMPT = "似乎仍有实体或关系被遗漏。如果还有需要补充的实体或关系，请回答“Y”；否则回答“N”。"



