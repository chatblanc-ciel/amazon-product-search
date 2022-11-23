from enum import Enum, auto
from typing import Union

import ipadic
from fugashi import GenericTagger, Tagger

TAGGER = Union[Tagger, GenericTagger]


class DicType(Enum):
    UNIDIC = auto()
    IPADIC = auto()


class OutputFormat(Enum):
    WAKATI = "wakati"
    DUMP = "dump"


# https://hayashibe.jp/tr/mecab/dictionary/unidic/pos (UniDic)
# What is "形状詞" in English?
class POSTag(Enum):
    NOUN = "名詞"
    PRONOUN = "代名詞"
    ADNOMINAL = "連体詞"
    ADVERB = "副詞"
    CONJUNCTION = "接続詞"
    INTERJECTION = "感動詞"
    VERB = "動詞"
    ADJECTIVE = "形容詞"
    AUXILIARY_VERB = "助動詞"
    PARTICLE = "助詞"
    PREFIX = "接頭辞"
    SUFFIX = "接尾辞"
    SYNBOL = "記号"
    AUXILIARY_SYMBOL = "補助記号"
    WHITESPACE = "空白"


class Tokenizer:
    def __init__(self, dic_type: DicType = DicType.UNIDIC, output_format: OutputFormat = OutputFormat.WAKATI):
        self.tagger: Tagger
        if dic_type == DicType.UNIDIC:
            self.tagger = Tagger(f"-O{output_format.value}")
        elif dic_type == DicType.IPADIC:
            self.tagger = GenericTagger(f"-O{output_format.value} {ipadic.MECAB_ARGS}")
        else:
            raise ValueError(f"Unsupported dic_type was given: {dic_type}")

        self.output_format: OutputFormat = output_format

    def tokenize(self, s: str) -> list[str]:
        """Tokenize a given string into tokens.

        Args:
            s (str): A string to tokenize.

        Returns:
            List[str]: A resulting of tokens.
        """
        if self.output_format == OutputFormat.WAKATI:
            return self.tagger.parse(s).split()

        tokens = []
        pos_tags = []
        for result in self.tagger(s):
            tokens.append(str(result))
            pos_tags.append(result.pos)
        return list(zip(tokens, pos_tags))
