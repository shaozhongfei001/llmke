import json
import os
import time
import traceback

from graph_fun_tool import requests_llm, clean_entity
from operators.common.log import logger
from prompts.entity_extraction import system_prompt, user_prompt, LOOP_PROMPT, CONTINUE_PROMPT
from prompts.query_extraction import ner_prompts
# R15-W02/A02：反向重复判定（同一事实正反两种写法）与 pair 索引构建。
# 判定函数放在 graph_types（纯函数、不依赖存储），这里只负责"标记 + 不交付给写入侧"。
from graph_types import as_pair_index, pair_key


# 单轮抽取的输出预算（token）。原实现不传该参数，等于吃服务端默认值，
# 在多事实块上会中途截断；459 字块实测需要 >1200 才能把实体+关系写完。
EXTRACT_MAX_TOKENS = int(os.environ.get("GRAPH_EXTRACT_MAX_TOKENS", "2048"))

# R15-W01：单块重试配置。
# 实测同一文件连续解析四次得到 155 条 / 0 边 / 59 条 / 200s+ 未结束，日志反复出现
# `关系行字段不足: ("relationship"::评级授信`——模型有时把输出截断在半行上（只吐出
# tag + 关系名，没有源/目标实体）。原实现在这种行解析失败时直接跳过、不重试、不计数，
# 一个 passage 的整批关系就这么静默丢了。
# 这里只对"拿不到可用结果"的那一次请求重发**完全相同的 messages**（prompt 语义不变）。
EXTRACT_MAX_RETRIES = int(os.environ.get("GRAPH_EXTRACT_RETRY_TIMES", "2"))
EXTRACT_RETRY_BACKOFF = tuple(
    float(_x) for _x in os.environ.get("GRAPH_EXTRACT_RETRY_BACKOFF", "1,3").split(",") if _x.strip()
)
# temperature=0 + 固定 seed 实测会稳定复现同一处截断，原样重发等于空转，
# 所以第 2 次起只递增 seed（不改 prompt / max_tokens / temperature）。
# 需要"严格同参重试"时置 GRAPH_EXTRACT_RETRY_VARY_SEED=0。
EXTRACT_RETRY_VARY_SEED = os.environ.get("GRAPH_EXTRACT_RETRY_VARY_SEED", "1") not in ("0", "false", "False", "")

# R15-W02/A02：反向重复去重开关（默认开）。
# 关掉只用于对照实验（证明"旧行为会产出双向边"），生产不应关闭。
EXTRACT_REVERSE_DEDUP = os.environ.get("GRAPH_EXTRACT_REVERSE_DEDUP", "1") not in ("0", "false", "False", "")

# R15-W01：输出结构约束（去掉首尾括号后按 "::" 切分）。
# 实体行必须**恰好 3 段**：tag + 名称 + 类型（原实现靠解包异常兜底，报错信息里看不出是几段）。
ENTITY_FIELDS = 3
# 关系行：tag + 三元组核心 3 段（关系名 / 源实体 / 目标实体），描述段可选。
RELATION_CORE_FIELDS = 3
RELATION_MIN_FIELDS = 1 + RELATION_CORE_FIELDS
RELATION_MAX_FIELDS = RELATION_MIN_FIELDS + 1


def _bump(stats, key, n=1):
    """统计计数（stats 为 None 时静默跳过，便于单独调用解析函数）。"""
    if stats is not None:
        stats[key] = stats.get(key, 0) + n


def _accumulate_stats(total, part):
    """把一个 passage 内多次解析（多轮 / 重试 / 补充采样）的计数合并进总账。"""
    for _k, _v in (part or {}).items():
        if isinstance(_v, int):
            total[_k] = total.get(_k, 0) + _v
    return total


def _retry_delay(attempt):
    """第 attempt 次重试前的等待秒数（默认 1s、3s）。"""
    if not EXTRACT_RETRY_BACKOFF:
        return 1.0
    return EXTRACT_RETRY_BACKOFF[min(attempt - 1, len(EXTRACT_RETRY_BACKOFF) - 1)]


def _last_output_line(response_text):
    """返回输出里最后一个非空行（去掉行首尾空白）。"""
    lines = [ln.strip() for ln in str(response_text or "").split("\n") if ln.strip()]
    return lines[-1] if lines else ""


def _looks_truncated(response_text):
    """末行未闭合 -> 疑似被 max_tokens / 服务端截断（修法 1，TL 2026-10-29 裁决）。

    依据（实测）：三档人为压低 max_tokens 的输出，`finish_reason` 全是 `length`，
    且末行分别止于 `贷` / `最` / `高` 这类非 `)` 字符；而完整输出的每一行（实体行、
    关系行）都以 `)` 收尾，提示词要求的 `########` 终止符模型经常不写，不能用它判定。

    刻意保守，只在"末行确实是候选行但没闭合"时判截断：
    - 末行空                       -> 不判截断
    - 末行以 `########` 开头        -> 不判截断（模型给了结束标记）
    - 末行不是以 `("` 开头的候选行   -> 不判截断（可能是说明性文字，不能被误判成截断）
    - 末行以 `)` 结尾              -> 不判截断（闭合）
    其余（以 `("` 开头且不以 `)` 结尾）-> 判截断。
    """
    last = _last_output_line(response_text)
    if not last:
        return False
    if last.startswith("#"):
        return False
    if not last.startswith('("'):
        return False
    return not last.endswith(")")


def _classify_attempt(response_text, attempt_stats, truncated=None):
    """判断本次 LLM 输出是否"拿不到可用结果"，返回原因串；可用时返回 None。

    R15-W01：这里刻意区分"合法空"与"解析失败"，只对后者重试——
    - 文本为空/全空白：请求失败或模型没有输出，值得重发；
    - 完全没有 entity/relationship 候选行：模型跑题（只输出说明文字或"无"），值得重发；
    - 有候选关系行但一条都没落地：整批丢弃，是"边为 0"的直接原因，值得重发；
    - **关系块整段缺失且末行未闭合**（修法 1）：模型被截断在写关系之前，此时输出里
      一条关系行都没有，与"合法无关系资料"形状相同，原实现判可用 -> 盲区，现在判截断重试。
    只要有实体、或至少一条关系落地，且末行闭合，就算可用，不重试。
    """
    if not str(response_text or "").strip():
        return "空响应"
    if truncated is None:
        truncated = _looks_truncated(response_text)
    if attempt_stats.get("candidate_lines", 0) == 0:
        return "无可解析行(末行未闭合,疑似截断)" if truncated else "无可解析行"
    if attempt_stats.get("relation_lines", 0) > 0 and attempt_stats.get("relations_parsed", 0) == 0:
        return "关系行全部丢弃"
    if truncated:
        return "关系块缺失且末行未闭合(疑似截断)"
    return None


def generate_graph_relations(passage, model_info, server_config, entity_types=None, exclude_pairs=None):
    """
    生成图谱三元组
    Args:
        entity_types:
        passage:
        model_info:
        server_config:
        exclude_pairs: R15-W02/A02（可选）存储里**已存在**的三元组/pair 索引。
            传入后，与已有事实"同关系名 + 同无序端点对"的关系会被标记
            `reverse_duplicate=True, skip_write=True` 且**不出现在返回值里**，
            调用方无需改动写入循环即可不写反向边。形态见 graph_types.as_pair_index()。

    Returns:
        (relations, entity_dict)；relations 已剔除 skip_write 的条目（形状与旧版一致）。

    """
    if entity_types is None:
        entity_types = []

    # R15-W01：一次调用的可诊断统计。原实现解析失败只打单条 error 日志、没有汇总，
    # "同一块四次 155/0/59 条"这种抖动无法从日志复算。这里在调用内累计，
    # 返回前输出一行固定格式 EXTRACT_STATS（k=v，便于 grep 与后续做分布监控）。
    _t_start = time.time()
    _stats = {
        "passage": 1,
        "passage_chars": len(passage or ""),
        "llm_calls": 0,
        "rounds": 0,
        "retries_used": 0,
        "candidate_lines": 0,
        "entity_lines": 0,
        "entities_parsed": 0,
        "relation_lines": 0,
        "relations_parsed": 0,
        "field_anomalies": 0,
        "parse_failed_lines": 0,
        "description_overflow": 0,
        "truncation_suspected": 0,
        # R15-W02/A02：被判定为反向重复（同 rel + 同无序端点对）而未交付写入的条数
        "reverse_dup_skipped": 0,
    }

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
            # R15-W01：单块重试。重试仍发送同一条 extract_message（prompt 语义不变），
            # 最多 EXTRACT_MAX_RETRIES 次、退避 1s/3s，且重试预算按 **passage** 记
            # （不是按轮次），所以最坏情况只多 2 次调用，不会把 200s+ 的耗时再放大。
            attempt = 0
            _last_reason = ""
            _final_failed = False
            filtered_output = ""
            while True:
                _att = {}
                _seed = 42 + attempt if (attempt and EXTRACT_RETRY_VARY_SEED) else 42
                _stats["llm_calls"] += 1
                # R14-P1-03：首轮未传 max_tokens，落到 LLM 服务端默认值 —— 459 字多事实块
                # 的输出会在 ~20 行实体处被硬截断（实测：最后一行停在"十五个工作日"，
                # 尾部的评级加点表永远抽不到）。这里显式给足输出预算。
                # 温度 0 + 固定 seed：抽取是"照文抄写"的任务，不需要创造性；
                # 实测 0.1 时同一块三次跑出 17/20/27 个实体，评级档位时有时无。
                llm_response_text = requests_llm(extract_message, model_info, server_config,
                                                 max_tokens=EXTRACT_MAX_TOKENS,
                                                 temperature=0, seed=_seed)

                entity_dict, relation_dict, filtered_output = process_relation_response(
                    llm_response_text,
                    entity_dict=entity_dict,
                    relation_dict=relation_dict,
                    debug=True,
                    stats=_att,
                    # R15-W02/A02：把"存储里已存在的事实"透传到解析层，
                    # 反向重复在这里就被标记，不必等 normalize 之后（那是另一个批次）。
                    existing_pairs=exclude_pairs)
                # R15-W01 修法 1：每次尝试单独判一次"末行是否闭合"，既用于分类也计入总账，
                # 这样 STATS 能回答"这次 0 边到底是模型没写关系，还是被截断在写关系之前"。
                _truncated = _looks_truncated(llm_response_text)
                if _truncated:
                    _bump(_att, "truncation_suspected")
                _accumulate_stats(_stats, _att)
                _reason = _classify_attempt(llm_response_text, _att, truncated=_truncated)
                if _reason is None:
                    if attempt:
                        # "第几次成功"——重试生效时必须在日志里留痕，否则下次仍要靠复放判断。
                        logger.warning(f"单块重试：第{attempt + 1}次尝试成功"
                                       f"（passage_chars={_stats['passage_chars']}, "
                                       f"首次失败原因={_last_reason}, seed={_seed}, "
                                       f"本轮落库三元组={_att.get('relations_parsed', 0)}）")
                    elif _att.get("relation_lines", 0) == 0:
                        # TL 要求：两种"无关系行"必须在日志里可区分，不能都静默放过。
                        logger.info(f"无关系行且输出完整（末行以)结尾）→ 判可用（合法空, 不重试）: "
                                    f"passage_chars={_stats['passage_chars']}, "
                                    f"candidate_lines={_att.get('candidate_lines', 0)}, "
                                    f"entities={_att.get('entities_parsed', 0)}")
                    break
                _last_reason = _reason
                if _truncated and _att.get("relation_lines", 0) == 0:
                    # TL 要求的明确日志：这一种"无关系行"是截断，不是合法空。
                    logger.warning(f"无关系行且疑似截断（末行不以)结尾）→ 重试: "
                                   f"passage_chars={_stats['passage_chars']}, "
                                   f"candidate_lines={_att.get('candidate_lines', 0)}, "
                                   f"末行={_last_output_line(llm_response_text)[:40]!r}")
                if attempt >= EXTRACT_MAX_RETRIES or _stats["retries_used"] >= EXTRACT_MAX_RETRIES:
                    _final_failed = True
                    logger.error(f"单块重试：最终失败（共尝试{attempt + 1}次, 原因={_reason}, "
                                 f"passage_chars={_stats['passage_chars']}, "
                                 f"已重试{_stats['retries_used']}次）")
                    break
                _delay = _retry_delay(attempt + 1)
                _stats["retries_used"] += 1
                attempt += 1
                logger.warning(f"单块重试：第{attempt}次尝试不可用（{_reason}），"
                               f"{_delay}s 后重发同一请求（prompt 不变, 已重试"
                               f"{_stats['retries_used']}/{EXTRACT_MAX_RETRIES}）")
                time.sleep(_delay)

            response_message["content"] = filtered_output
            _stats["rounds"] += 1
            if _final_failed:
                # 这一轮重试预算已用尽仍无可用结果：继续用"还有遗漏吗"追问只会放大耗时，
                # 直接结束本 passage 的多轮循环，交给后面的补充采样兜底。
                break
            # R14-P1-03：原为 max_tokens=1 + `== "Y"` 精确匹配。
            # max_tokens=1 时模型很可能只吐出空白或 "Y\n"，精确比较会判 False -> 永不续写。
            # 改为给 4 个 token，并把判定做归一化（去空白/大小写/取首字符）。
            _stats["llm_calls"] += 1
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
            _stats["llm_calls"] += 1
            extra = requests_llm(messages, model_info, server_config,
                                 max_tokens=EXTRACT_MAX_TOKENS,
                                 temperature=0.3, seed=42 + _i)
            if _looks_truncated(extra):
                _bump(_stats, "truncation_suspected")
            entity_dict, relation_dict, _ = process_relation_response(
                extra, entity_dict=entity_dict, relation_dict=relation_dict, debug=False, stats=_stats,
                existing_pairs=exclude_pairs)
        except Exception as e:
            logger.error(f"补充采样 {_i} 失败（不影响已有结果）: {str(e)[:80]}")

    # R15-W01：一次调用一次的汇总行（固定格式、单行、k=v），用于 grep 与做分布监控。
    # passage 数固定为 1（本函数按 passage 调用），保留字段是为了和批量侧口径一致。
    # 字段契约（R15-W01，对 W03 的 graph-rebuild.sh 生效）：前缀 `R15-W01 EXTRACT_STATS` 不改名，
    # 已有 k=v 的位置不变，新字段**只在行尾追加**（description_overflow / truncation_suspected
    # 均按此规则追加，W03 的解析器无需改动）。
    logger.info(
        "R15-W01 EXTRACT_STATS passage={} passage_chars={} llm_calls={} rounds={} retries={} "
        "candidate_lines={} parse_failed_lines={} field_anomalies={} "
        "valid_entities={} valid_triples={} elapsed_ms={} description_overflow={} "
        "truncation_suspected={} reverse_dup_skipped={}".format(
            _stats["passage"], _stats["passage_chars"], _stats["llm_calls"], _stats["rounds"],
            _stats["retries_used"], _stats["candidate_lines"], _stats["parse_failed_lines"],
            _stats["field_anomalies"], len(entity_dict), len(relation_dict),
            int((time.time() - _t_start) * 1000), _stats["description_overflow"],
            _stats["truncation_suspected"], _stats["reverse_dup_skipped"]))
    # R15-W02/A02：带 skip_write 标记的关系**不交付**给写入侧。
    # 保留在 relation_dict 里是为了可审计（谁、以哪个方向被判定为反向重复），
    # 返回值的形状仍是 list[relation]，调用方循环无需改动。
    return [r for r in relation_dict.values() if not r.get("skip_write")], entity_dict


def _strip_wrapper(line):
    """去掉模型输出行首的 "(" 与行尾的 ")"。

    R15-W01：原实现固定用 line[1:-1]，遇到被截断的行（缺尾部 ")"，例如
    `("relationship"::评级授信`）会把最后一个真实字符也切掉，字段值莫名少一位。
    这里只在确实以 ")" 结尾时才去掉尾部字符。
    """
    body = line[1:] if line.startswith("(") else line
    if body.endswith(")"):
        body = body[:-1]
    return body


def process_relation_response(response_text, entity_dict=None, relation_dict=None, debug=False,
                              stats=None, existing_pairs=None):
    entity_dict = entity_dict or {}
    relation_dict = relation_dict or {}
    visited_entity = set()
    response_strings = []
    verified_strings = []
    relation_lines = []
    # R15-W01：stats 为可选出参（默认 None 保持原调用方式不变）。传入 dict 时累计
    # 候选行/实体行/关系行/解析失败/字段数异常/有效三元组计数，供上层汇总。
    #
    # R15-W02/A02：反向重复判定的"已见集合"。
    # 组成 = 存储里已存在的事实（existing_pairs，跨批次）∪ 本次调用已被接受的键
    # （跨轮次/跨补充采样，因为 relation_dict 在多轮之间是复用的）。
    _existing_index = as_pair_index(existing_pairs)
    _seen_pairs = set(_existing_index)
    for _k in relation_dict:
        try:
            _seen_pairs.add(pair_key(_k[1], _k[0], _k[2]))
        except Exception:
            continue

    def _generate_filtered_response():
        """将抽取出有效的关系、实体，生成符合prompt 要求的格式，后面再输给大模型判断抽取是否完整"""
        filtered_response = []
        for entity in entity_dict.values():
            filtered_response.append(f'("entity"::{entity["name"]}::{entity["type"]})')

        for relation in relation_dict.values():
            # R15-W02/A02：被判定为反向重复的关系不反馈给模型当作"已抽取"，
            # 否则下一轮"还有遗漏吗"会把它当成既成事实继续强化。
            if relation.get("skip_write"):
                continue
            filtered_response.append(
                f'("relationship"::{relation["name"]}::{relation["src_entity"]["name"]}::{relation["dest_entity"]["name"]}::{relation["description"]})')
        return "\n".join(filtered_response)

    for line in response_text.split("\n"):
        line = line.strip()
        if len(line) == 0:
            continue
        if line.startswith('("entity"::') or line.startswith('("relationship"::'):
            _bump(stats, "candidate_lines")
        try:
            if line.startswith('("entity"::'):
                _bump(stats, "entity_lines")
                # R15-W01：实体行必须**恰好 3 段**（tag + 名称 + 类型）。
                # 原实现靠解包异常兜底，报错里只有原文、看不出是几段/缺哪段。
                _entity_parts = _strip_wrapper(line).split("::")
                if len(_entity_parts) != ENTITY_FIELDS:
                    _bump(stats, "field_anomalies")
                    _bump(stats, "parse_failed_lines")
                    logger.error(f"数据处理失败,字段数异常(实体行期望{ENTITY_FIELDS}段,"
                                 f"实际{len(_entity_parts)}段),{line[:80]}")
                    continue
                _, name, ent_type = _entity_parts
                name = clean_entity(name)
                ent_type = clean_entity(ent_type)
                if not ent_type:
                    ent_type = '其他'
                entity_dict[name] = {"name": name, "type": ent_type}
                _bump(stats, "entities_parsed")
                verified_strings.append("+ " + line)
            elif line.startswith('("relationship"::'):
                _bump(stats, "relation_lines")
                relation_lines.append(line)
        except Exception as e:
            _bump(stats, "parse_failed_lines")
            logger.error(f"数据处理失败,{line}，{e}")
            pass  # 抽取不符合要求
    for line in relation_lines:
        flag = False
        try:
            # R14-P1-03：原为严格 5 段解包，模型只要少写一段 description
            # （或 description 里多一个 "::"）就抛 "not enough values to unpack" 并**丢整条关系**。
            # 实测同一块一轮里能丢 5~8 条，正好落在"评级加点"这类长描述上。
            _parts = _strip_wrapper(line).split("::")
            _n_fields = len(_parts)
            _description_overflow = False
            if _n_fields < RELATION_MIN_FIELDS:
                # R15-W01：不足 -> 记 字段数异常 并计数（原来只有一条 error 日志、没有汇总）。
                # 实测来源就是模型把输出截断在半行上：("relationship"::评级授信
                _bump(stats, "field_anomalies")
                raise ValueError(f"字段数异常(关系行字段不足: 期望>={RELATION_MIN_FIELDS}段"
                                 f"[tag+{RELATION_CORE_FIELDS}段三元组],实际{_n_fields}段): {line[:60]}")
            if _n_fields > RELATION_MAX_FIELDS:
                # R15-W01：超出通常是描述里自带 "::"（如"口径::按日"），不是脏数据，
                # 所以只计数 + 告警，仍按"描述=剩余段拼接"落地，不把有效关系一起丢掉。
                # R15-W01 / TL 裁决 b（2026-10-29）：真实的"超出"多是模型把多实体串成一行
                # （如 9 段：办理流程-> / 受理 / 资料审核 / 评级授信 / …），救回后 description
                # 会混入本应是端点的名词。保留关系但**必须可追溯**：打 description_overflow=true，
                # 并在关系字典上带同名标记，供社区摘要/引用侧识别"这条描述不可靠"。
                # 不改三元组本身的 name/src/dest/description，也不改成"丢弃+要求重写"（语义变更，超出本轮）。
                _description_overflow = True
                _bump(stats, "field_anomalies")
                _bump(stats, "description_overflow")
                logger.warning(f"字段数异常(关系行超出: 期望<={RELATION_MAX_FIELDS}段,"
                               f"实际{_n_fields}段,描述含'::'),已按描述拼接,"
                               f"description_overflow=true: {line[:80]}")
            relation_name, src_ent, dest_ent = _parts[1], _parts[2], _parts[3]
            description = "::".join(_parts[4:]) if _n_fields > 4 else ""
            src_ent = clean_entity(src_ent)
            dest_ent = clean_entity(dest_ent)
            if not src_ent or not dest_ent:
                # R15-W01：三元组核心 3 段有空值 -> 端点不确定，原实现静默 continue，
                # 这里补计数与日志，否则"少了很多边"在日志里看不到原因。
                _bump(stats, "field_anomalies")
                _bump(stats, "parse_failed_lines")
                logger.error(f"字段数异常(关系行核心字段为空: 关系名={relation_name[:20]},"
                             f"源实体={src_ent[:20]},目标实体={dest_ent[:20]}): {line[:80]}")
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

            # R15-W02/A02：反向重复判定。
            # 同一 (关系名, 无序端点对) 一旦已有事实存在（存储里的 existing_pairs，
            # 或本次调用前几轮已接受的关系），这条就不再作为新事实交付写入。
            # 方向是否正确不由本函数裁决：先写的方向即被认定为该事实的自然方向，
            # 后来者一律视为重复 —— 存储因此不会同时出现 A->B 与 B->A 两个 show_flag=1。
            _rel_name = clean_entity(relation_name)
            _rel_key = pair_key(_rel_name, src_ent, dest_ent)
            if EXTRACT_REVERSE_DEDUP and _rel_key in _seen_pairs:
                _scope = "existing" if _rel_key in _existing_index else "batch"
                relation_dict[(src_ent, relation_name, dest_ent)] = {
                    "name": _rel_name,
                    "src_entity": src_entity,
                    "dest_entity": dest_entity,
                    "description": description,
                    "reverse_duplicate": True,
                    "reverse_duplicate_scope": _scope,
                    "skip_write": True,
                }
                _bump(stats, "reverse_dup_skipped")
                logger.info(f"反向重复已跳过(scope={_scope}): {src_ent} -{_rel_name}-> {dest_ent}")
                visited_entity.add(src_entity["name"])
                visited_entity.add(dest_entity["name"])
                # 记为"-"（未落地），让 debug 快照与落库结果一致
                verified_strings.append("- " + line + f"  # 反向重复({_scope})")
                continue

            relation_dict[(src_ent, relation_name, dest_ent)] = {
                "name": clean_entity(relation_name),
                "src_entity": src_entity,
                "dest_entity": dest_entity,
                "description": description
            }
            # 接受即入"已见集合"：同一 passage 后续再出现反方向也会被判定为重复
            _seen_pairs.add(_rel_key)
            if _description_overflow:
                # TL 裁决 b：只加侧车标记，不改 name/src_entity/dest_entity/description。
                # 现有消费者（graph_service.llm_generate_triple、_generate_filtered_response）
                # 都按字段名取值，多一个键不影响；要落库需 graph_service 侧消费该键（他人文件，本包不越界）。
                relation_dict[(src_ent, relation_name, dest_ent)]["description_overflow"] = True
            visited_entity.add(src_entity["name"])
            visited_entity.add(dest_entity["name"])
            response_strings.append(f'("relationship"::{relation_name}::{src_entity["name"]}::{dest_entity["name"]}::{description})')
            _bump(stats, "relations_parsed")
            flag = True
        except Exception as e:
            _bump(stats, "parse_failed_lines")
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
