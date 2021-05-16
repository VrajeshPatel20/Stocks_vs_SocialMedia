# -*- coding: utf-8 -*-
"""Untitled1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1JPQh9d5gDOyRS8NE_xXZQ480iy88947v
"""

"""AnalyzePosts.ipynb
Automatically generated by Colaboratory.
Original file is located at
    https://colab.research.google.com/drive/1e1Ci0rOAjXsTmf-ntw91k7iGR_j-3B_4
"""

# Commented out IPython magic to ensure Python compatibility.
#########################################  DATA REQUESTS #############################################


##########################################  DATA MINING ##############################################

import smtplib

#######################################  DATA MANIPULATION ###########################################

import numpy as np
import pandas as pd
import csv
import re
import string
import os
import time

#######################################  DATA VISUALIZATION ###########################################

import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pylab as plt
# %matplotlib inline
import seaborn as sns
import plotly.figure_factory as ff
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot
import plotly

####################################### Sentiment Analysis #########################################

import torch
import torchvision
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import torch.nn as nn
import torch.nn.functional as F
from torchvision.datasets import MNIST
from torchvision.transforms import ToTensor
from torchvision.utils import make_grid
from torch.utils.data.dataloader import DataLoader
from torch.utils.data import random_split
from torchtext.legacy import data
from torchtext.legacy import datasets
import random
from torch.utils.data import DataLoader, TensorDataset, random_split
import spacy


#######################################################################################################

# NOTE: Sentiment Analysis Model is referenced from another source. Link below
# URL: https://github.com/bentrevett/pytorch-sentiment-analysis/blob/master/3%20-%20Faster%20Sentiment%20Analysis.ipynb

def generate_bigrams(x):
    n_grams = set(zip(*[x[i:] for i in range(2)]))
    for n_gram in n_grams:
        x.append(' '.join(n_gram))
    return x


################################ LOAD TRAINING DATA ###################################

SEED = 1234

torch.manual_seed(SEED)
torch.backends.cudnn.deterministic = True

TEXT = data.Field(tokenize='spacy',
                  tokenizer_language='en_core_web_sm',
                  preprocessing=generate_bigrams)

LABEL = data.LabelField(dtype=torch.float)

train_data, test_data = datasets.IMDB.splits(TEXT, LABEL)

train_data, valid_data = train_data.split(random_state=random.seed(SEED))

print("train_data: ", len(train_data), " test_data: ", len(test_data))

MAX_VOCAB_SIZE = 25_000

TEXT.build_vocab(train_data,
                 max_size=MAX_VOCAB_SIZE,
                 vectors="glove.6B.100d",
                 unk_init=torch.Tensor.normal_)

LABEL.build_vocab(train_data, )

BATCH_SIZE = 64

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

train_iterator, valid_iterator, test_iterator = data.BucketIterator.splits(
    (train_data, valid_data, test_data),
    batch_size=BATCH_SIZE,
    device=device)


################################################################################

class Sentiment(nn.Module):
    def __init__(self, in_size, out_size, vocab_size, pad_idx):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, in_size, padding_idx=pad_idx)
        self.linear = nn.Linear(in_size, out_size)

    def forward(self, xb):
        emd = self.embedding(xb)
        emd = emd.permute(1, 0, 2)
        out = F.avg_pool2d(emd, (emd.shape[1], 1)).squeeze(1)
        return self.linear(out)


################################################################################

def evaluate(model, iterator, criterion):
    epoch_loss = 0
    epoch_acc = 0

    model.eval()

    with torch.no_grad():
        for batch in iterator:
            predictions = model(batch.text).squeeze(1)

            loss = criterion(predictions, batch.label)

            acc = accuracy(predictions, batch.label)

            epoch_loss += loss.item()
            epoch_acc += acc.item()

    return epoch_loss / len(iterator), epoch_acc / len(iterator)


################################################################################

def train(model, iterator, optimizer, criterion):
    epoch_loss = 0
    epoch_acc = 0

    model.train()

    for batch in iterator:
        optimizer.zero_grad()

        predictions = model(batch.text).squeeze(1)

        loss = criterion(predictions, batch.label)

        acc = accuracy(predictions, batch.label)

        loss.backward()

        optimizer.step()

        epoch_loss += loss.item()
        epoch_acc += acc.item()

    return epoch_loss / len(iterator), epoch_acc / len(iterator)


################################################################################

def accuracy(preds, y):
    """
    Returns accuracy per batch, i.e. if you get 8/10 right, this returns 0.8, NOT 8
    """

    # round predictions to the closest integer
    rounded_preds = torch.round(torch.sigmoid(preds))
    correct = (rounded_preds == y).float()
    acc = correct.sum() / len(correct)
    return acc


################################ Load Model #####################################

criterion = nn.BCEWithLogitsLoss()

model = Sentiment(64, 1, len(TEXT.vocab), TEXT.vocab.stoi[TEXT.pad_token])

model = model.to(device)
criterion = criterion.to(device)
import torch.optim as optim 
optimizer = optim.Adam(model.parameters())

##################################### TRAIN ######################################

N_EPOCHS = 10
min_loss = float('inf')
for epoch in range(N_EPOCHS):
    train_loss, train_acc = train(model, train_iterator, optimizer, criterion)
    valid_loss, valid_acc = evaluate(model, valid_iterator,criterion)

    if valid_loss < min_loss:
        min_loss = valid_loss
        torch.save(model.state_dict(), 'tut3-model.pt')
    print(f'\tTrain Loss: {train_loss:.3f} | Train Acc: {train_acc * 100:.2f}%')
    print(f'\t Val. Loss: {valid_loss:.3f} |  Val. Acc: {valid_acc * 100:.2f}%')

################################################################################

nlp = spacy.load('en_core_web_sm')


def predict_sentiment(model, sentence):
    model.eval()
    tokenized = generate_bigrams([tok.text for tok in nlp.tokenizer(sentence)])
    indexed = [TEXT.vocab.stoi[t] for t in tokenized]
    tensor = torch.LongTensor(indexed).to(device)
    tensor = tensor.unsqueeze(1)
    prediction = torch.sigmoid(model(tensor))
    return prediction.item()

    
################################################################################

# To get the number of posts of a stock subreddit we choose
def Analyze_Reddit_Posts(stocks, df, common_words):
    """
    Count the total occurences and upvotes of every stock on reddit by
    crossreferencing it with the DataFrame of reddit post we retreived earlier.
    Parameters
    ----------
    stocks       : pd.DataFrame
    df           : pd.DataFrame
    common_words : list
    Returns
    -------
    pd.DataFrame
    """
    ############################ Analyze Reddit Posts ##########################

    result = []

    for stock in stocks.itertuples():
        sum, count, positive, negative, neutral = 0, 0, 0, 0, 0
        stock_ = stock.Stock_Name
        for item in df.itertuples():

            # If the stock name occurred in either Title or Content of the post
            if stock_ in item.Title or stock_ in item.Content:
                sum = sum + item.Upvotes
                count = count + 1
                if predict_sentiment(model, item.Content) >= 0.5:
                  positive += 1
                elif predict_sentiment(model, item.Content) <= 0.2:
                    negative += 1
                else:
                    neutral += 1

        # Append data if the stock:
        #                           Occurred More than once
        #                           Not a common word
        #                           The name is of len > 4

        if count > 0 and len(stock.Stock_Name) > 4 and stock_ not in common_words:
            result.append({'Stock_Name': stock.Stock_Name,
                           'Ticker': stock.Ticker,
                           'Number_Of_Occurences': count,
                           'Total_Upvotes': sum,
                           'Positive' : positive,
                           'Negative' : negative,
                           'Neutral' : neutral})

    ############################################################################

    return pd.DataFrame(result)


# To get the number of posts of a stock subreddit we choose
def Analyze_Reddit_Crypto(cryptos, df, common_words):
    """
    Count the total occurences and upvotes of every crypto on reddit by
    crossreferencing it with the DataFrame of reddit post we retreived earlier.
    Parameters
    ----------
    cryptos      : pd.DataFrame
    df           : pd.DataFrame
    common_words : list
    Returns
    -------
    pd.DataFrame
    """
    ############################ Analyze Reddit Posts ##########################

    result = []

    for crypto in cryptos.itertuples():
        sum, count, positive, negative, neutral = 0, 0, 0, 0, 0
        crypto_ = crypto.Name
        for item in df.itertuples():

            # If the stock name occurred in either Title or Content of the post
            if crypto_ in item.Title or crypto_ in item.Content:
                sum = sum + item.Upvotes
                count = count + 1
                semt = predict_sentiment(model, item.Content)
                if semt >= 0.5:
                    positive += 1
                elif semt <= 0.2 :
                    negative += 1
                else:
                    neutral += 1

        # Append data if the stock:
        #                           Occurred More than once
        #                           Not a common word
        #                           The name is of len > 4

        if count > 0 and len(crypto_) > 4 and crypto_ not in common_words:
            result.append({'Name': crypto_,
                           'Symbol': crypto.Symbol,
                           'Number_Of_Occurences': count,
                           'Total_Upvotes': sum,
                           'Positive' : positive,
                           'Negative' : negative,
                           'Neutral' : neutral})

    ############################################################################

    return pd.DataFrame(result)


def Analyze_tweets(stocks, df, common_words):
    """
    Count the total occurences and retweets of every stock on twitter by
    crossreferencing it with the DataFrame of tweets we retreived earlier.
    Parameters
    ----------
    stocks       : pd.DataFrame
    df           : pd.DataFrame
    common_words : list
    Returns
    -------
    pd.DataFrame
    """
    ############################### Analyze Tweets #############################

    result = []
    for stock in stocks.iterrows():
        sum, count, positive, negative, neutral = 0, 0, 0, 0, 0
        stock_ = stock[1]['Stock_Name']
        for item in df.itertuples():
            if stock_ in item.text:
                sum = sum + item.retweet_count
                count = count + 1
                semt = predict_sentiment(model, item.text)
                if semt >= 0.5:
                    positive += 1
                elif semt <= 0.2 :
                    negative += 1
                else:
                    neutral += 1

        # Append data if the stock:
        #                           Occurred More than once
        #                           Not a common word
        #                           The name is of len > 4

        if count > 0 and len(stock_) > 4 and stock_ not in common_words:
            result.append({'Stock_Name': stock_,
                           'Ticker': stock[1]['Ticker'],
                           'Number_Of_Occurences': count,
                           'Total_retweets': sum,
                           'Positive' : positive,
                           'Negative' : negative,
                           'Neutral' : neutral})

    ############################################################################
    return pd.DataFrame(result)


# To get the number of posts of a stock subreddit we choose
def Analyze_Tweets_Crypto(cryptos, df, common_words):
    """
    Count the total occurences and upvotes of every crypto on reddit by
    crossreferencing it with the DataFrame of reddit post we retreived earlier.
    Parameters
    ----------
    cryptos      : pd.DataFrame
    df           : pd.DataFrame
    common_words : list
    Returns
    -------
    pd.DataFrame
    """
    ############################ Analyze Reddit Posts ##########################

    result = []

    for crypto in cryptos.itertuples():
        sum, count, positive, negative, neutral = 0, 0, 0, 0, 0
        crypto_ = crypto.Name
        for item in df.itertuples():

            # If the stock name occurred in either Title or Content of the post
            if crypto_ in item.text:
                sum = sum + item.retweet_count
                count = count + 1
                semt = predict_sentiment(model, item.text)
                if semt >= 0.5:
                    positive += 1
                elif semt <= 0.2 :
                    negative += 1
                else:
                    neutral += 1

        # Append data if the stock:
        #                           Occurred More than once
        #                           Not a common word
        #                           The name is of len > 4

        if count > 0 and len(crypto_) > 4 and crypto_ not in common_words:
            result.append({'Name': crypto_,
                           'Symbol': crypto.Symbol,
                           'Number_Of_Occurences': count,
                           'Total_Retweets': sum,
                           'Positive' : positive,
                           'Negative' : negative,
                           'Neutral' : neutral})

    ############################################################################

    return pd.DataFrame(result)

