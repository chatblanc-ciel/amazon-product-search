from collections import defaultdict

import pandas as pd

from amazon_product_search.constants import DATA_DIR
from amazon_product_search.nlp.tokenizer import Tokenizer


class SynonymDict:
    def __init__(self, synonym_filename: str = "synonyms_jp_sbert.csv"):
        self.tokenizer = Tokenizer()
        self._entry_dict: dict[str, list[tuple[str, float]]] = self.load_synonym_dict(synonym_filename)

    @staticmethod
    def load_synonym_dict(synonym_filename: str) -> dict[str, list[tuple[str, float]]]:
        """Load the synonym file and convert it into a dict for lookup.

        Args:
        synonym_filename (str): A filename to load, which is supposed to be under `{DATA_DIR}/includes`.

        Returns:
            dict[str, list[str]]: The converted synonym dict.
        """
        df = pd.read_csv(f"{DATA_DIR}/includes/{synonym_filename}")
        entry_dict = defaultdict(list)
        for row in df.to_dict("records"):
            query = row["query"]
            title = row["title"]
            similarity = row["similarity"]
            entry_dict[query].append((title, similarity))
        # df = df[df["similarity"] >= threshold]
        # queries = df["query"].tolist()
        # synonyms = df["title"].tolist()
        # entry_dict = defaultdict(list)
        # for query, synonym in zip(queries, synonyms):
        #     entry_dict[query].append(synonym)
        return entry_dict

    def find_synonyms(self, query: str, threshold: float = 0.6) -> list[str]:
        """Return a list of synonyms for a given query.

        Args:
            query (str): A query to expand.
            threshold (float, optional): A threshold for the confidence (similarity) of synonyms. Defaults to 0.6.

        Returns:
            list[str]: A list of synonyms.
        """
        all_synonyms = []
        tokens = self.tokenizer.tokenize(query)
        for token in tokens:
            if token not in self._entry_dict:
                continue
            candidates: list[tuple[str, float]] = self._entry_dict[token]
            synonyms = [synonym for synonym, similarity in candidates if similarity >= threshold]
            if synonyms:
                all_synonyms.extend(synonyms)
        return all_synonyms