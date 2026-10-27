import json
import os
import traceback

from graph_fun_tool import requests_llm, clean_entity
from operators.common.log import logger
from prompts.entity_extraction import system_prompt, user_prompt, LOOP_PROMPT, CONTINUE_PROMPT
from prompts.query_extraction import ner_prompts


# 单轮抽取的输出预算（token）。原实现不传该参数，等于吃服务端默认值，
# 在多事实块上会中途截断；459 字块实测需要 >1200 才能把实体+关系写完。
EXTRACT_MAX_TOKENS = int(os.environ.get("GRAPH_EXTRACT_MAX_TOKENS", "2048"))


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
        # R14-P1-03：原为 `count < 2`（最多 2 轮）。实测 459 字含"产品要素 + 评级加点表"的块，
        # 两轮只能覆盖约 2/3 的事实，G1 依赖的评级映射整段缺失。
        # 轮次上限改为可配（默认 5），让"抽不完就继续"成为默认行为；
        # 真正的成本护栏是 MAX_EXTRACT_ROUNDS，而不是指望模型一次抽全。
        max_rounds = int(os.environ.get("GRAPH_EXTRACT_MAX_ROUNDS", "5"))
        while is_continue and count < max_rounds:
            if count == 0:
                extract_message = messages
            else:
                extract_message = messages + [response_message, continue_message]
            logger.info(extract_message)
            # R14-P1-03：首轮未传 max_tokens，落到 LLM 服务端默认值 —— 459 字多事实块
            # 的输出会在 ~20 行实体处被硬截断（实测：最后一行停在"十五个工作日"，
            # 尾部的评级加点表永远抽不到）。这里显式给足输出预算。
            # 温度 0 + 固定 seed：抽取是"照文抄写"的任务，不需要创造性；
            # 实测 0.1 时同一块三次跑出 17/20/27 个实体，评级档位时有时无。
            llm_response_text = requests_llm(extract_message, model_info, server_config,
                                             max_tokens=EXTRACT_MAX_TOKENS,
                                             temperature=0, seed=42)

            entity_dict, relation_dict, filtered_output = process_relation_response(llm_response_text,
                                                                                    entity_dict=entity_dict,
                                                                                    relation_dict=relation_dict,
                                                                                    debug=True)
            response_message["content"] = filtered_output
            # R14-P1-03：原为 max_tokens=1 + `== "Y"` 精确匹配。
            # max_tokens=1 时模型很可能只吐出空白或 "Y\n"，精确比较会判 False -> 永不续写。
            # 改为给 4 个 token，并把判定做归一化（去空白/大小写/取首字符）。
            continue_response = requests_llm(messages + [response_message, loop_message],
                                             model_info, server_config, max_tokens=4)
            _ans = str(continue_response or "").strip().upper()
            is_continue = _ans.startswith("Y") or _ans.startswith("是")
            count += 1
    except:
        traceback.print_exc()

    # R14-P1-03：单次调用存在**随机整段漏抽**（实测同一块 6 次里 1 次完全没有"基点"）。
    # 分块/换模型都不是必需，性价比最高的是"多采样取并集"：
    #   漏抽率 p≈0.4，3 次全漏 ≈ 6.4%
    samples = int(os.environ.get("GRAPH_EXTRACT_SAMPLES", "3"))
    for _i in range(1, samples):
        try:
            extra = requests_llm(messages, model_info, server_config,
                                 max_tokens=EXTRACT_MAX_TOKENS,
                                 temperature=0.3, seed=42 + _i)
            entity_dict, relation_dict, _ = process_relation_response(
                extra, entity_dict=entity_dict, relation_dict=relation_dict, debug=False)
        except Exception as e:
            logger.error(f"补充采样 {_i} 失败（不影响已有结果）: {str(e)[:80]}")
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
            # R14-P1-03：原为严格 5 段解包，模型只要少写一段 description
            # （或 description 里多一个 "::"）就抛 "not enough values to unpack" 并**丢整条关系**。
            # 实测同一块一轮里能丢 5~8 条，正好落在"评级加点"这类长描述上。
            _parts = line[1:-1].split("::")
            if len(_parts) < 4:
                raise ValueError(f"关系行字段不足: {line[:60]}")
            relation_name, src_ent, dest_ent = _parts[1], _parts[2], _parts[3]
            description = "::".join(_parts[4:]) if len(_parts) > 4 else ""
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
