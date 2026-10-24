import json
import traceback

from graph_fun_tool import requests_llm, clean_entity
from operators.common.log import logger
from prompts.entity_extraction import system_prompt, user_prompt, LOOP_PROMPT, CONTINUE_PROMPT
from prompts.query_extraction import ner_prompts


def generate_graph_relations(passage, model_info, server_config, entity_types=None):
    """
    生成图谱三元组
    Args:
        entity_types:
        passage:
        model_info:
        server_config:

    Returns:

    """
    if entity_types is None:
        entity_types = []

    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt.format(passage=passage, entity_types=",".join(entity_types))}]

    response_message = {"role": "assistant", "content": ""}
    continue_message = {'role': "user", "content": CONTINUE_PROMPT}
    loop_message = {'role': "user", "content": LOOP_PROMPT}
    entity_dict = {}
    relation_dict = {}
    is_continue = True
    count = 0
    try:
        while is_continue and count < 2:
            if count == 0:
                extract_message = messages
            else:
                extract_message = messages + [response_message, continue_message]
            logger.info(extract_message)
            llm_response_text = requests_llm(extract_message, model_info, server_config)

            entity_dict, relation_dict, filtered_output = process_relation_response(llm_response_text,
                                                                                    entity_dict=entity_dict,
                                                                                    relation_dict=relation_dict,
                                                                                    debug=True)
            response_message["content"] = filtered_output
            continue_response = requests_llm(messages + [response_message, loop_message], model_info, server_config, max_tokens=1)
            is_continue = continue_response == "Y"
            count += 1
    except:
        traceback.print_exc()
    return list(relation_dict.values()), entity_dict


def process_relation_response(response_text, entity_dict=None, relation_dict=None, debug=False):
    entity_dict = entity_dict or {}
    relation_dict = relation_dict or {}
    visited_entity = set()
    response_strings = []
    verified_strings = []
    relation_lines = []

    def _generate_filtered_response():
        """将抽取出有效的关系、实体，生成符合prompt 要求的格式，后面再输给大模型判断抽取是否完整"""
        filtered_response = []
        for entity in entity_dict.values():
            filtered_response.append(f'("entity"::{entity["name"]}::{entity["type"]})')

        for relation in relation_dict.values():
            filtered_response.append(
                f'("relationship"::{relation["name"]}::{relation["src_entity"]["name"]}::{relation["dest_entity"]["name"]}::{relation["description"]})')
        return "\n".join(filtered_response)

    for line in response_text.split("\n"):
        line = line.strip()
        if len(line) == 0:
            continue
        try:
            if line.startswith('("entity"::'):
                _, name, ent_type = line[1:-1].split("::")
                name = clean_entity(name)
                ent_type = clean_entity(ent_type)
                if not ent_type:
                    ent_type = '其他'
                entity_dict[name] = {"name": name, "type": ent_type}
                verified_strings.append("+ " + line)
            elif line.startswith('("relationship"::'):
                relation_lines.append(line)
        except Exception as e:
            logger.error(f"数据处理失败,{line}，{e}")
            pass  # 抽取不符合要求
    for line in relation_lines:
        flag = False
        try:
            _, relation_name, src_ent, dest_ent, description = line[1:-1].split("::")
            src_ent = clean_entity(src_ent)
            dest_ent = clean_entity(dest_ent)
            if not src_ent or not dest_ent:
                continue
            if src_ent in entity_dict:
                src_entity = entity_dict[src_ent]
            else:
                src_entity = {"name": src_ent, "type": "其他"}
                entity_dict[src_ent] = src_entity
            if dest_ent in entity_dict:
                dest_entity = entity_dict[dest_ent]
            else:
                dest_entity = {"name": dest_ent, "type": "其他"}
                entity_dict[dest_ent] = dest_entity

            relation_dict[(src_ent, relation_name, dest_ent)] = {
                "name": clean_entity(relation_name),
                "src_entity": src_entity,
                "dest_entity": dest_entity,
                "description": description
            }
            visited_entity.add(src_entity["name"])
            visited_entity.add(dest_entity["name"])
            response_strings.append(f'("relationship"::{relation_name}::{src_entity["name"]}::{dest_entity["name"]}::{description})')
            flag = True
        except Exception as e:
            logger.error(e)
            pass

        if flag:
            verified_strings.append("+ " + line)
        else:
            verified_strings.append("- " + line)

    if debug:
        logger.info("模型输出&审核结果：")
        logger.info("\n".join(verified_strings))
        logger.info(f"没有用到的实体:{set(entity_dict.keys()).difference(visited_entity)}", )
        logger.info("=" * 30)
    return entity_dict, relation_dict, _generate_filtered_response()


def generate_query_entities(passage, model_info, server_config):
    """
    生成实体
    Args:
        passage:
        model_config:
        server_config:

    Returns:

    """
    ner_messages = ner_prompts.format_prompt(user_input=passage)
    prompt_dict_list = ner_messages.dict()["messages"]
    messages = [{"role": "system", "content": prompt_dict_list[0]["content"]},
                {"role": "user", "content": prompt_dict_list[1]["content"]}]
    res_result = requests_llm(messages, model_info, server_config)
    return process_query_response(res_result)


def process_query_response(llm_response_text):
    for line in llm_response_text.split("\n"):
        try:
            line = line.strip()
            if line.startswith("<keyword>"):
                return json.loads(line[len("<keyword>"):])
        except:
            traceback.print_exc()
    return []
