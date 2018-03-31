import gzip
import os
import traceback

from bage_utils.hangul_util import HangulUtil
from bage_utils.mongodb_util import MongodbUtil
from bage_utils.num_util import NumUtil
from nlp4kor_tensorflow.config import log, MONGO_URL, KO_WIKIPEDIA_ORG_SENTENCES_FILE, KO_WIKIPEDIA_ORG_URLS_FILE, \
    KO_WIKIPEDIA_ORG_CHARACTERS_FILE, KO_WIKIPEDIA_ORG_TRAIN_SENTENCES_FILE, KO_WIKIPEDIA_ORG_TEST_SENTENCES_FILE, \
    KO_WIKIPEDIA_ORG_INFO_FILE, KO_WIKIPEDIA_ORG_VALID_SENTENCES_FILE


class TextPreprocess(object):
    @staticmethod
    def dump_urls(mongo_url, db_name, collection_name, urls_file, mongo_query=None, limit=0):
        if mongo_query is None:
            mongo_query = {}

        corpus_mongo = MongodbUtil(mongo_url, db_name=db_name, collection_name=collection_name)
        total = corpus_mongo.count()
        log.info('%s total: %s' % (corpus_mongo, NumUtil.comma_str(total)))

        output_dir = os.path.basename(urls_file)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(urls_file, 'wt') as out_f:
            for i, row in enumerate(corpus_mongo.find(mongo_query, limit=limit)):
                if i % 1000 == 0:
                    log.info('%s %.1f%% writed.' % (os.path.basename(urls_file), i / total * 100))
                    out_f.write(row['url'])
                    out_f.write('\n')

    @staticmethod
    def dump_corpus(mongo_url, db_name, collection_name, sentences_file, characters_file, info_file, urls_file,
                    train_sentences_file, valid_sentences_file, test_sentences_file,
                    mongo_query=None, limit=None):
        """
        Mongodb에서 문서를 읽어서, 문장 단위로 저장한다. (단 문장안의 단어가 1개 이거나, 한글이 전혀 없는 문장은 추출하지 않는다.)
        :param characters_file:
        :param urls_file:
        :param info_file:
        :param mongo_url: mongodb://~~~
        :param db_name: database name of mongodb
        :param collection_name: collection name of mongodb
        :param sentences_file: *.sentence file
        :param train_sentences_file:
        :param valid_sentences_file:
        :param test_sentences_file:
        :param mongo_query: default={}
        :param limit:
        :return:
        """
        if mongo_query is None:
            mongo_query = {}

        corpus_mongo = MongodbUtil(mongo_url, db_name=db_name, collection_name=collection_name)
        total_docs = corpus_mongo.count()
        log.info('%s total: %s' % (corpus_mongo, NumUtil.comma_str(total_docs)))

        output_dir = os.path.basename(sentences_file)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with gzip.open(sentences_file, 'wt') as out_f, \
                gzip.open(train_sentences_file, 'wt') as train_f, \
                gzip.open(valid_sentences_file, 'wt') as valid_f, \
                gzip.open(test_sentences_file, 'wt') as test_f, \
                open(info_file, 'wt') as info_f, \
                open(urls_file, 'wt') as urls_f:

            char_set = set()
            n_docs = n_total = n_train = n_valid = n_test = 0
            if limit:
                cursor = corpus_mongo.find(mongo_query, limit=limit)
            else:
                cursor = corpus_mongo.find(mongo_query)

            for i, row in enumerate(cursor, 1):
                if i % 1000 == 0:
                    log.info('%s %.1f%% writed.' % (os.path.basename(sentences_file), i / total_docs * 100))

                sentences = []
                for c in row['content']:
                    sentences.extend(HangulUtil.text2sentences(c['sentences'], remove_only_one_word=True, has_hangul=True, remove_markdown=True))

                log.debug('url: %s, len: %s' % (row['url'], len(sentences)))
                if len(sentences) == 0:
                    # log.error(row['content'])
                    continue

                urls_f.write(row['url'])
                urls_f.write('\n')
                n_docs += 1

                for s in sentences:
                    _char_set = set([c for c in s])
                    char_set.update(_char_set)

                    n_total += 1
                    out_f.write(s)
                    out_f.write('\n')

                if len(sentences) >= 10:  # can split
                    test_len = valid_len = len(sentences) // 10
                    # log.info('train: %s, test: %s, valid: %s' % (len(sentences) - test_len - valid_len, test_len, valid_len))
                    for s in sentences[:test_len]:
                        n_test += 1
                        test_f.write(s)
                        test_f.write('\n')
                    for s in sentences[test_len:test_len + valid_len]:
                        n_valid += 1
                        valid_f.write(s)
                        valid_f.write('\n')
                    for s in sentences[test_len + valid_len:]:
                        n_train += 1
                        train_f.write(s)
                        train_f.write('\n')
                else:  # can't split
                    for s in sentences:
                        n_train += 1
                        train_f.write(s)
                        train_f.write('\n')

            char_list = list(char_set)
            char_list.sort()
            log.info('writed to %s...' % characters_file)
            with open(characters_file, 'w') as f:
                for c in char_list:
                    f.write(c)
                    f.write('\n')
            log.info('writed to %s OK.' % characters_file)

            log.info('total docs: %s', NumUtil.comma_str(total_docs))
            log.info('total docs: %s (has hangul sentence)', NumUtil.comma_str(n_docs))
            log.info('total sentences: %s (has hangul sentence)', NumUtil.comma_str(n_total))
            log.info('train: %s', NumUtil.comma_str(n_train))
            log.info('valid: %s', NumUtil.comma_str(n_valid))
            log.info('test: %s', NumUtil.comma_str(n_test))
            log.info('total characters: %s', NumUtil.comma_str(len(char_list)))

            info_f.write('total docs: %s\n' % NumUtil.comma_str(total_docs))
            info_f.write('total docs: %s (has hangul sentence)\n' % NumUtil.comma_str(n_docs))
            info_f.write('total sentences: %s (has hangul sentence)\n' % NumUtil.comma_str(n_total))
            info_f.write('train: %s\n' % NumUtil.comma_str(n_train))
            info_f.write('valid: %s\n' % NumUtil.comma_str(n_valid))
            info_f.write('test: %s\n' % NumUtil.comma_str(n_test))
            info_f.write('total characters: %s\n' % NumUtil.comma_str(len(char_list)))


if __name__ == '__main__':
    info_file = KO_WIKIPEDIA_ORG_INFO_FILE
    urls_file = KO_WIKIPEDIA_ORG_URLS_FILE
    sentences_file = KO_WIKIPEDIA_ORG_SENTENCES_FILE
    characters_file = KO_WIKIPEDIA_ORG_CHARACTERS_FILE
    log.info('info_file: %s' % info_file)
    log.info('urls_file: %s' % urls_file)
    log.info('sentences_file: %s' % sentences_file)
    log.info('characters_file: %s' % characters_file)

    if not os.path.exists(characters_file) or not os.path.exists(sentences_file) or not os.path.exists(info_file) or not os.path.exists(urls_file):
        try:
            log.info('create senences file...')
            TextPreprocess.dump_corpus(MONGO_URL, db_name='parsed', collection_name='ko.wikipedia.org', sentences_file=sentences_file,
                                       characters_file=characters_file,
                                       info_file=info_file, urls_file=urls_file,
                                       train_sentences_file=KO_WIKIPEDIA_ORG_TRAIN_SENTENCES_FILE,
                                       valid_sentences_file=KO_WIKIPEDIA_ORG_VALID_SENTENCES_FILE,
                                       test_sentences_file=KO_WIKIPEDIA_ORG_TEST_SENTENCES_FILE,
                                       mongo_query={})  # mongodb -> text file(corpus)
            log.info('create senences file OK')
        except:
            log.error(traceback.format_exc())
            if os.path.exists(sentences_file):
                os.remove(sentences_file)
            if os.path.exists(info_file):
                os.remove(info_file)
            if os.path.exists(urls_file):
                os.remove(urls_file)
            if os.path.exists(characters_file):
                os.remove(characters_file)
