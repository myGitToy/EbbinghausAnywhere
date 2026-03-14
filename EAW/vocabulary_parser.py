"""
词汇表PDF解析器

支持不同格式的词汇表PDF文件解析
"""
import re
from typing import List, Dict


class ShanghaiZhongkaoParser:
    """上海中考词汇解析器"""

    def parse(self, pdf_path: str) -> List[Dict]:
        """
        解析上海中考词汇PDF
        格式: "序号. [*]单词 音标/" (如 "7. *absent /ˈæbsənt/")
        """
        import pdfplumber

        entries = []

        with pdfplumber.open(pdf_path) as pdf:
            # 第一部分：第1-51页（中文→英文）
            part1_pages = pdf.pages[:51]
            part1_data = self._parse_chinese_part(part1_pages)

            # 第二部分：第52页及以后（英文→中文）
            part2_pages = pdf.pages[51:]
            part2_data = self._parse_english_part(part2_pages)

            # 按序号合并
            entries = self._merge_parts(part1_data, part2_data)

        return entries

    def _parse_chinese_part(self, pages) -> Dict[int, str]:
        """
        解析中文部分
        支持两种格式:
        1. "序号. /音标/ 词性.中文释义" (如 "7. /ˈæbsənt/ adj.缺席的;缺乏的")
        2. "序号. 词性.中文释义" (如 "648. n. 获得")
        注意：音标可能包含多个部分，如 "/eɪ/,/ən/"
        """
        data = {}

        for page in pages:
            text = page.extract_text()
            if not text:
                continue

            for line in text.split('\n'):
                line = line.strip()
                if not line or len(line) < 3:
                    continue

                # 先尝试匹配带音标的格式: "序号. /音标/ 词性.中文释义"
                match = re.match(r'^(\d+)\.\s*/.*/\s*(.+)$', line)
                if match:
                    seq_num = int(match.group(1))
                    meaning = match.group(2).strip()
                    if meaning:
                        data[seq_num] = meaning
                    continue

                # 再尝试匹配不带音标的格式: "序号. 词性.中文释义"
                match = re.match(r'^(\d+)\.\s*(.+)$', line)
                if match:
                    seq_num = int(match.group(1))
                    meaning = match.group(2).strip()
                    # 过滤掉只有单个字母或特殊符号的行
                    if meaning and len(meaning) > 2:
                        data[seq_num] = meaning

        return data

    def _parse_english_part(self, pages) -> Dict[int, Dict]:
        """
        解析英文部分
        格式: "序号. [*]单词 /音标/"
        示例: "1. *a, an /eɪ/,/ən/" 或 "7. *absent /ˈæbsənt/"
        返回: {序号: {'word': '单词', 'uk_phonetic': '英式音标', 'is_marked': 是否带星号}}
        """
        data = {}

        for page in pages:
            text = page.extract_text()
            if not text:
                continue

            for line in text.split('\n'):
                line = line.strip()
                if not line or len(line) < 3:
                    continue

                # 跳过标题或特殊行
                match = re.match(r'^(\d+)\.', line)
                if not match:
                    continue

                # 提取序号
                seq_num = int(match.group(1))

                # 检查是否带星号
                is_marked = '*' in line

                # 提取序号后的内容
                # 格式: "序号. [*]单词 /音标/"
                # 先移除序号
                content = re.sub(r'^\d+\.\s*', '', line)

                # 移除开头的星号（如果有）
                is_marked = '*' in content  # 再次检查，因为序号后才有星号
                content = content.lstrip('*').strip()

                # 提取音标（格式：/.../）
                phonetic = ''
                phonetic_match = re.search(r'/([^/]*(?:/[^/]*)*)/', content)
                if phonetic_match:
                    phonetic = phonetic_match.group(0)  # 保留完整的 /.../ 格式

                # 查找第一个以字母开头的单词（到音标斜杠为止）
                # 单词可能包含逗号、空格、括号、点号
                word_match = re.match(r'^([a-zA-Z\u0080-\uffff][a-zA-Z\u0080-\uffff\-, ().]*?)(?:\s*/|$)', content)
                if word_match:
                    word = word_match.group(1).strip()
                    # 只清理多余的空格（保留单词间的单个空格）
                    word = re.sub(r'\s+', ' ', word)

                    if word and len(word) >= 2:  # 至少2个字母的单词
                        data[seq_num] = {
                            'word': word,
                            'uk_phonetic': phonetic,  # 英式音标
                            'is_marked': is_marked
                        }

        return data

    def _merge_parts(self, part1: Dict[int, str], part2: Dict[int, Dict]) -> List[Dict]:
        """
        合并两部分数据
        part1: {序号: '词性.中文释义'}
        part2: {序号: {'word': '单词', 'uk_phonetic': '/音标/', 'is_marked': 是否带星号}}
        """
        merged = []

        # 获取所有序号
        all_seq_nums = set(part1.keys()) | set(part2.keys())

        for seq_num in sorted(all_seq_nums):
            # 从part2获取单词信息
            if seq_num in part2:
                word_info = part2[seq_num]
                word = word_info['word']
                uk_phonetic = word_info.get('uk_phonetic', '')
                is_marked = word_info.get('is_marked', False)
            else:
                word = ''
                uk_phonetic = ''
                is_marked = False

            # 从part1获取中文释义
            chinese_meaning = part1.get(seq_num, '')

            # 合并音标和中文释义到meaning字段
            # 格式: "/音标/ 词性.中文释义" 或 "词性.中文释义"（无音标时）
            if uk_phonetic:
                meaning = f"{uk_phonetic} {chinese_meaning}" if chinese_meaning else uk_phonetic
            else:
                meaning = chinese_meaning if chinese_meaning else word

            # 至少需要有英文单词
            if word:
                merged.append({
                    'sequence_number': seq_num,
                    'word': word,
                    'meaning': meaning,  # 格式: "/音标/ 词性.中文释义"
                    'uk_phonetic': uk_phonetic,  # 英式音标（用于导入到Item.uk_phonetic）
                    'us_phonetic': '',  # 美式音标（PDF不提供）
                    'is_marked': is_marked
                })

        return merged
