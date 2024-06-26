import numpy as np
import argparse
import pickle
import os
import torch
import random
from tqdm import tqdm
from nltk.tokenize import word_tokenize, sent_tokenize


hf_token = "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"

parser = argparse.ArgumentParser()

parser.add_argument('--seed', type=int, default=42)
parser.add_argument('--root', type=str, default="/data/mathieu")
parser.add_argument('--dataset_names', type=list, default=["Arxiv", "PubMed", "GovReport", "SummScreen", "MultiNews"])
parser.add_argument('--subsets', type=list, default=["test", "test", "test", "test", "test"])
parser.add_argument('--subset_sizes', type=list, default=[6440, 6658, 973, 337, 5622])
parser.add_argument('--alignment_metric', type=str, default="rouge-1", choices=["rouge-1", "rouge-2", "rouge-l"])
parser.add_argument('--absolute_bin_size', type=int, default=400)  # 100 or 400
parser.add_argument('--min_bin', type=int, default=3)
parser.add_argument('--sample_sizes', type=list, default=[50, 50, 50, 25, 50])

args = parser.parse_args()


def main(args):
    print(args)

    seed_everything(args)

    test_queries, test_texts, test_labels = [], [], []
    for i in range(len(args.dataset_names)):
        # load the data
        dataset_name = args.dataset_names[i]
        subset = args.subsets[i]
        subset_size = args.subset_sizes[i]
        texts_path = f"summaries/{dataset_name}/{subset}/{subset}_texts_{subset_size}.pkl"
        texts = pickle.load(open(texts_path, "rb"))
        labels_path = f"summaries/{dataset_name}/{subset}/{subset}_labels_{subset_size}.pkl"
        labels = pickle.load(open(labels_path, "rb"))
        print(f"\nLoading labels from {labels_path}")
        print(len(texts), len(labels))

        # load the labels alignment
        folder = f"alignments/{dataset_name}/{subset}"
        alignment_path = f"{folder}/{subset}_labels_relative_alignment_{len(texts)}.pkl"
        if args.alignment_metric == "rouge-2":
            alignment_path = f"{folder}/{subset}_labels_relative_alignment_r2_{len(texts)}.pkl"
        elif args.alignment_metric == "rouge-l":
            alignment_path = f"{folder}/{subset}_labels_relative_alignment_rl_{len(texts)}.pkl"
        aligned_labels = pickle.load(open(alignment_path, "rb"))
        print(f"\nLoaded labels alignments from: {alignment_path}")
        print(len(aligned_labels))

        # stats on alignment
        sents_bins = absolute_stats(texts, aligned_labels, args)

        idx = [k for k in range(len(sents_bins)) if np.min(sents_bins[k]) >= args.min_bin]
        idx = np.array(idx)
        print(f"There are {len(idx)} potential data points")
        p = np.random.permutation(len(idx))
        sample_size = args.sample_sizes[i]
        p = p[:sample_size]
        sampled_idx = idx[p]
        test_queries += [dataset_name] * len(sampled_idx)
        test_texts += [texts[x] for x in sampled_idx]
        test_labels += [labels[x] for x in sampled_idx]
    print(len(test_queries), len(test_texts), len(test_labels))

    print(test_texts[0][:100])

    size = len(test_texts)
    folder = f"raw_summaries/MiddleSum/test"
    os.makedirs(folder, exist_ok=True)
    queries_path = f"{folder}/test_queries_{size}.pkl"
    texts_path = f"{folder}/test_texts_{size}.pkl"
    labels_path = f"{folder}/test_labels_{size}.pkl"
    pickle.dump(test_queries, open(queries_path, "wb"))
    pickle.dump(test_texts, open(texts_path, "wb"))
    pickle.dump(test_labels, open(labels_path, "wb"))
    print(f"Saved test texts to: {texts_path}")

def seed_everything(args):
    seed = int(args.seed)
    random.seed(seed)
    os.environ['PYTHONASSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = True

def absolute_stats(texts, aligned_summaries, args):
    n_bins = 20
    all_sents_bins = []
    total_bin_fracs = np.zeros(n_bins)
    for i in tqdm(range(len(texts))):
        text = texts[i]
        sents = sent_tokenize(text)
        if len(sents) == 0:
            continue
        sent_idx_to_tokens = {}
        words_count = 0
        for j in range(len(sents)):
            words = word_tokenize(sents[j])
            words_count += len(words)
            sent_idx_to_tokens[j] = words_count
        sent_bins = [int(sent_idx_to_tokens[x] / args.absolute_bin_size) for x in aligned_summaries[i][0]]
        sent_bins = np.array(sent_bins)
        all_sents_bins.append(sent_bins)
        bin_fracs = np.zeros(n_bins)
        for j in range(len(bin_fracs)):
            bin_fracs[j] = 100 * np.sum(sent_bins == j) / len(sent_bins)
        total_bin_fracs += bin_fracs
    total_bin_fracs /= len(texts)
    values = [np.round(x, 2) for x in total_bin_fracs]
    print(f"Histogram with {n_bins}:")
    print(values)

    return all_sents_bins


if __name__ == '__main__':
    main(args)
