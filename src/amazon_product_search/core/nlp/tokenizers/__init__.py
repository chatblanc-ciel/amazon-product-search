from amazon_product_search.core.nlp.tokenizers.english_tokenizer import EnglishTokenizer
from amazon_product_search.core.nlp.tokenizers.japanese_tokenizer import JapaneseTokenizer
from amazon_product_search.core.nlp.tokenizers.tokenizer import Tokenizer
from amazon_product_search.core.source import Locale


def locale_to_tokenizer(locale: Locale) -> Tokenizer:
    return {
        "us": EnglishTokenizer,
        "jp": JapaneseTokenizer,
    }[locale]()


__all__ = [
    "EnglishTokenizer",
    "JapaneseTokenizer",
    "Tokenizer",
]
