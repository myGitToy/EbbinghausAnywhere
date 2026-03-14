"""
从PDF导入词汇表到临时数据库

使用方法:
    python manage.py vocabulary_import_pdf "path/to/vocabulary.pdf" --name "词汇表名称" --level "中考"
"""
from django.core.management.base import BaseCommand
from EAW.vocabulary_parser import ShanghaiZhongkaoParser
from EAW.models import VocabularyBook, VocabularyEntry


class Command(BaseCommand):
    help = '从PDF导入词汇表到临时数据库'

    def add_arguments(self, parser):
        parser.add_argument('pdf_path', type=str, help='PDF文件路径')
        parser.add_argument('--name', type=str, help='词汇表名称')
        parser.add_argument('--level', type=str, help='词汇等级')
        parser.add_argument('--description', type=str, help='词汇表描述')

    def handle(self, *args, **options):
        pdf_path = options['pdf_path']
        parser = ShanghaiZhongkaoParser()

        self.stdout.write(f'正在解析PDF: {pdf_path}')
        try:
            entries_data = parser.parse(pdf_path)
            self.stdout.write(self.style.SUCCESS(f'成功解析 {len(entries_data)} 个单词'))

            # 创建词汇表
            book = VocabularyBook.objects.create(
                name=options.get('name', '导入词汇表'),
                description=options.get('description', ''),
                level=options.get('level', ''),
                source_file=pdf_path,
                word_count=len(entries_data)
            )

            # 创建条目
            for data in entries_data:
                VocabularyEntry.objects.create(
                    vocabulary_book=book,
                    sequence_number=data['sequence_number'],
                    word=data['word'],
                    meaning=data['meaning'],  # 词性+中文释义（不含音标）
                    uk_phonetic=data.get('uk_phonetic', ''),  # 英式音标
                    us_phonetic=data.get('us_phonetic', ''),  # 美式音标（通常为空）
                    is_marked=data.get('is_marked', False)  # 是否带星号
                )

            self.stdout.write(
                self.style.SUCCESS(f'✓ 成功导入 {len(entries_data)} 个单词到词汇表 "{book.name}" (ID: {book.id})')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ 导入失败: {str(e)}')
            )
