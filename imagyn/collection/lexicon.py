"""
MIT License

Copyright (c) 2017 Zev Isert; Jose Gordillo; Matt Hodgson; Graeme Turney; Maxwell Borden

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""
Contains classes and functions regarding wordnet and imagenet synsets.
"""

import requests
import random
import os

from nltk import download, data
from nltk.corpus import wordnet as wn
from nltk.corpus.reader.wordnet import Synset, WordNetError
from functools import namedtuple


class InvalidKeywordException(Exception):
    """
    Exception for a keyword that is not in WordNet.
    """
    def __init__(self, msg):
        self.msg = msg

# Cache class declared outside ImageNetAPI to allow pickling for multidownloader

Cache = namedtuple('Cache', ['synsets', 'words', 'urls', 'hyponyms'])


class ImageNetAPI:
    def __init__(self):
        self.__cache = Cache(synsets=list(), words=dict(), urls=dict(), hyponyms=dict())

    @property
    def all_synsets(self) -> list:
        """
        Get and cache the list of word net identifiers indexed by imagenet
        :return: List of strings, WordNet ID's (wnid)
        """
        if len(self.__cache.synsets) == 0:
            allsynsetsurl = "http://image-net.org/api/text/imagenet.synset.obtain_synset_list"

            allsynsetsreq = requests.get(allsynsetsurl)
            if allsynsetsreq.status_code == 200:
                self.__cache.synsets.clear()
                self.__cache.synsets.extend(allsynsetsreq.content.decode().splitlines())

        return self.__cache.synsets

    def words_for(self, wnid: str) -> list:
        """
        Get ImageNet's description of a synset, and cache the result
        :param wnid: synset offset, also called wordnet id
        :return: List of strings, words
        """

        if wnid not in self.__cache.words:
            if wnid in self.all_synsets:
                wordurl = "http://image-net.org/api/text/wordnet.synset.getwords?wnid={}".format(wnid)
                wordreq = requests.get(wordurl)

                if wordreq.status_code == 200:
                    self.__cache.words[wnid] = wordreq.content.decode().splitlines()

        return self.__cache.words.get(wnid, [])

    def urls_for(self, wnid: str) -> list:
        """
        Get image urls for a synset from ImageNet, cache the result
        :param wnid: synset offset, also called wordnet id
        :return: List of urls as strings
        """

        if wnid not in self.__cache.urls:
            if wnid in self.all_synsets:
                urlsurl = "http://image-net.org/api/text/imagenet.synset.geturls?wnid={}".format(wnid)
                urlsreq = requests.get(urlsurl)

                if urlsreq.status_code == 200:
                    self.__cache.urls[wnid] = urlsreq.content.decode().splitlines()

        return self.__cache.urls.get(wnid, [])

    def hyponym_for(self, wnid: str) -> list:
        """
        Get hyponyms for a word as interpreted by ImageNet, cache the result
        :param wnid: synset offset, also called wordnet id
        :return: List of strings, hyponyms
        """

        if wnid not in self.__cache.hyponyms:
            if wnid in self.all_synsets:
                hyposurl = "http://image-net.org/api/text/wordnet.structure.hyponym?wnid={}".format(wnid)
                hyposreq = requests.get(hyposurl)

                if hyposreq.status_code == 200:
                    self.__cache.hyponyms[wnid] = hyposreq.content.decode().splitlines()

        return self.__cache.hyponyms.get(wnid, [])


class SynsetLexicon:
    def __init__(self):
        """
        Contains various synset related functions.
        """
        try:
            data.find(os.path.join("corpora", "wordnet"))
        except LookupError:
            download("wordnet")

        self.API = ImageNetAPI()

    def get_synset(self, keyword: str):
        """
        Get the synset that matches the given keyword.
        :param keyword: The user provided string to obtain the synset from
        :raises: InvalidKeywordException
        :return: The synset obtained from WordNet
        """

        synset = wn.synset("{}.n.01".format(keyword)) 
        if self.valid_synset(synset):
            return synset
        else:
            # Invalid synset, it is not in WordNet.
            raise InvalidKeywordException("{} is not a viable keyword in ImageNet.".format(keyword))

    @staticmethod
    def get_synset_id(synset: Synset):
        """
        Get the corresponding synset id of the synset.
        :param synset: The synset to extract the id from
        :return: The corresponding synset id
        """

        sid = "n{}".format(str(synset.offset()).zfill(8))
        return sid

    def valid_synset(self, synset: Synset):
        """
        Determines if the synset is valid by checking to see that it is in ImageNet.
        :param synset: The synset to check for validity
        :return: A boolean determining whether or not the synset is in ImageNet
        """

        sid = self.get_synset_id(synset)
        return sid in self.API.all_synsets

    def get_siblings(self, synset: Synset, limit=None):
        """
        Returns siblings of the synset (hyponyms of the hypernym of this synset).
        :param synset: The synset to obtain the siblings from
        :return: The siblings obtained from the synset
        """

        siblings = []
        sibling_count = 0
        parent = self.get_parent(synset)

        for sibling in parent.hyponyms():
            if sibling_count == limit:
                break
            if sibling != synset and self.valid_synset(sibling):
                siblings.insert(sibling_count, sibling)
                sibling_count += 1
        
        return siblings

    @staticmethod
    def get_parent(synset: Synset):
        """
        Returns one random parent of the synset (hypernym).
        :param synset: The synset to obtain the parent from
        :return: One of the parents of the synset
        """

        return random.choice(synset.hypernyms())

    @staticmethod
    def get_parents(synset: Synset):
        """
        Returns all parents of the synset (hypernyms).
        :param synset: The synset to obtain the parent from
        :return: List of the parents of the synset
        """

        return synset.hypernyms()

    @staticmethod
    def get_grandparents(synset: Synset):
        """
        Returns all grandparents of the synset (hypernyms of hypernyms).
        :param synset: The synset to obtain the grandparents from
        :return: The grandparents of the synset
        """

        grandparents = []

        for parent in synset.hypernyms():
            grandparents.extend(parent.hypernyms())
        
        return grandparents

    def get_unrelated_synsets(self, synset: Synset, limit=5):
        """
        Gets unrelated synsets.
        :param synset: The synset to compare with
        :return: Five synsets that are unrelated to the synset passed
        """

        # Get the matching grandparents in order to ensure unrelated synsets
        match_grandparents = self.get_grandparents(synset)

        unrelated_synsets = []
        unrelated_count = 0
        while unrelated_count < limit:
            # Obtain an unrelated synset
            unrelated_synset_id = random.choice(self.API.all_synsets)
            unrelated_synset_name = random.choice(self.API.words_for(unrelated_synset_id))

            # Keeps attempting to obtain an actual noun      
            try:
                unrelated_synset = wn.synset("{}.n.01".format(unrelated_synset_name))
            except WordNetError:
                # Skip to the next loop iteration to retrieve a noun
                continue
            
            # Get grandparents of unrelated synset
            unrelated_grandparents = self.get_grandparents(unrelated_synset)
            
            # Ensure valid synset and that it is truely unrelated
            # This is done by ensuring the set intersection of the grandparent synsets is empty
            intersection = set(match_grandparents) & set(unrelated_grandparents)
            if self.valid_synset(unrelated_synset) and not bool(intersection):
                unrelated_synsets.insert(unrelated_count, unrelated_synset)
                unrelated_count += 1

        return unrelated_synsets

    def main(self):
        parser = argparse.ArgumentParser(description="Imagyn Lexicon")
        group = parser.add_mutually_exclusive_group(required=True)

        group.add_argument(
            "--id",
            type=str,
            help="Return the id of a keyword"
        )

        group.add_argument(
            "--siblings",
            type=str,
            help="Return a list of siblings of a synset id"
        )

        group.add_argument(
            "--parent",
            type=str,
            help="Return a list of parents of a synset id"
        )

        group.add_argument(
            "--grandparents",
            type=str,
            help="Return a list of grandparents of a synset id"
        )

        args = parser.parse_args()

        if args.id:
            synset = self.get_synset(args.id)
            print(self.get_synset_id(synset))

        elif args.siblings:
            synset = wn.synset_from_pos_and_offset(args.siblings[0], int(args.siblings[1:]))
            print("\n".join([word.name().split(".")[0] for word in self.get_siblings(synset)]))

        elif args.parent:
            synset = wn.synset_from_pos_and_offset(args.parent[0], int(args.parent[1:]))
            print(self.get_parent(synset).name().split(".")[0])

        elif args.grandparents:
            synset = wn.synset_from_pos_and_offset(args.grandparents[0], int(args.grandparents[1:]))
            print("\n".join([word.name().split(".")[0] for word in self.get_grandparents(synset)]))

if __name__ == '__main__':
    import argparse
    SynsetLexicon().main()
