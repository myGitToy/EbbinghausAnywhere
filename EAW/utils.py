# utils.py

import difflib
from .translate import baidu_translate

def clean_and_split_lines(content):
    """
    清理内容并按行分割，去除无关符号和空行。
    """
    if not content:
        return []
    # 去除前后空白字符，并按行分割
    cleaned_lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
    return cleaned_lines

def compare_and_merge(existing_lines, new_lines, threshold=0.8):
    """
    逐行比较新旧内容，使用 difflib 筛选出相似度低于阈值的行，并合并。
    """
    merged_lines = existing_lines.copy()  # 保留原有内容
    existing_set = set(existing_lines)  # 用集合快速去重

    for new_line in new_lines:
        is_duplicate = False
        for existing_line in existing_lines:
            # 计算相似度
            similarity = difflib.SequenceMatcher(None, existing_line, new_line).ratio()
            if similarity >= threshold:
                is_duplicate = True
                break
        # 仅在不重复的情况下添加
        if not is_duplicate and new_line not in existing_set:
            merged_lines.append(new_line)

    return merged_lines

def fetch_and_merge_translation(item_name, existing_content):
    """
    调用百度翻译 API 获取释义，并将其与现有内容进行合并。
    """
    # 调用翻译函数
    translation_result = baidu_translate(item_name)
    if not translation_result:
        return existing_content, "", "", "", ""  # 返回现有内容和空值，表示翻译失败

    # 解析翻译结果
    parts_and_means = translation_result.get('parts_and_means', [])
    simple_meaning = translation_result.get('simple_meaning', [])
    src_tts = translation_result.get('src_tts', '')
    phonetic = translation_result.get('phonetic', [])
    phonetic_am = phonetic[1] if len(phonetic) > 1 else None
    phonetic_en = phonetic[0] if len(phonetic) > 0 else None

    # 获取新旧内容
    new_content = "\n".join(parts_and_means if parts_and_means else simple_meaning)
    existing_lines = clean_and_split_lines(existing_content)
    new_lines = clean_and_split_lines(new_content)

    # 逐行比较并合并
    updated_lines = compare_and_merge(existing_lines, new_lines, threshold=0.8)

    # 合并后的内容
    updated_content = "\n".join(updated_lines)

    return updated_content, src_tts, phonetic_am, phonetic_en
