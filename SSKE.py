# coding: utf-8

import os
import sys
import string
import itertools
import nltk
import re
import networkx as nx
import numpy as np
import math
import matplotlib.pyplot as plt
from nltk.stem import SnowballStemmer
from sklearn import feature_extraction
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import CountVectorizer
    
def get_filelist(file_path):
    file_list = []
    files = os.listdir(file_path)
    for f in files:
        file_list.append(f)
    return file_list

def readfile(file_path, file_name):
    with open(file_path+'/'+file_name, 'r') as f:
        file_text = f.read()
    return file_text

def write_file(text, file_path, file_name):
    if not os.path.exists(file_path) : 
        os.mkdir(file_path)
    with open(file_path+'/'+file_name, 'w') as f:
        f.write(text)

def rm_tags(file_text):
    """处理输入文本，将已经标注好的POS tag去掉，以便使用nltk包处理。"""
    file_splited = file_text.split()
    text_notag = ''
    for t in file_splited:
        text_notag = text_notag + ' ' + t[:t.find('_')]
    return text_notag

def get_tagged_tokens(file_text):
    file_splited = file_text.split()
    tagged_tokens = []
    for token in file_splited:
        tagged_tokens.append(tuple(token.split('_')))
    return tagged_tokens

###################################################################
def is_word(token):
    """
    A token is a "word" if it begins with a letter.
    
    This is for filtering out punctuations and numbers.
    """
    return re.match(r'^[A-Za-z].+', token)

def is_good_token(tagged_token):
    """
    A tagged token is good if it starts with a letter and the POS tag is
    one of ACCEPTED_TAGS.
    """
    return is_word(tagged_token[0]) and tagged_token[1] in ACCEPTED_TAGS
    
def normalized_token(token):
    """
    Use stemmer to normalize the token.
    建图时调用该函数，而不是在file_text改变词形的存储
    """
    stemmer = SnowballStemmer("english") 
    return stemmer.stem(token.lower())
###################################################################
    
def get_filtered_text(tagged_tokens, ACCEPTED_TAGS):
    """过滤掉无用词汇，留下候选关键词，选择保留名词和形容词，并且恢复词形stem
       使用filtered_text的时候要注意：filtered_text是一串文本，其中的单词是可能会重复出现的。
    """
    filtered_text = ''
    for tagged_token in tagged_tokens:
        if is_good_token(tagged_token):
            filtered_text = filtered_text + ' '+ normalized_token(tagged_token[0])
    return filtered_text
    
# def get_corpus(corpus, filtered_text):
#     """返回一个list，每项为每个文本的内容，排列顺序按照file_list
#        第一次调用之前，要先初始化corpus = []"""
#     return corpus

def read_node_features(node_list, raw_node_features, file_name):
    file = re.findall(file_name+'.*', raw_node_features)
    tmp1 = []
    for t in file:
        tmp1.append(t.split(':'))
    tmp2 = {}
    for t in tmp1:
        features_t = re.search('\d.*', t[1]).group().split(',')
        feature_num = len(features_t)
        for i in range(feature_num):
            features_t[i] = float(features_t[i])
        tmp2[re.search('[a-zA-Z].*' ,t[0]).group()] = features_t
    zero_feature = []
    for i in range(feature_num):
        zero_feature.append(0)
    node_features = {}
    for node in node_list:
        node_features[node] = tmp2.get(node, zero_feature)
    return node_features

def calc_node_weight(node_features, phi):
    """字典，{node: weight, node2: weight2}
    """
    node_weight = {}
    for node in node_features:
        node_weight[node] = float(node_features[node] * phi)
    return node_weight
    
def get_edge_freq(filtered_text, window=2):
    """
    输出边
    顺便统计边的共现次数
    输出格式：{('a', 'b'):[2], ('b', 'c'):[3]}
    """
    edges = []
    edge_and_freq = {}
    tokens = filtered_text.split()
    for i in range(0, len(tokens) - window + 1):
        edges += list(itertools.combinations(tokens[i:i+window],2))
    for i in range(len(edges)):
        for edge in edges:
            if edges[i][0] == edge[1] and edges[i][1] == edge[0]:
                edges[i] = edge
                # 此处处理之后，在继续输入其他特征时，需要先判断下边的表示顺序是否一致
    for edge in edges:
        edge_and_freq[edge] = [2 * edges.count(edge) / (tokens.count(edge[0]) + tokens.count(edge[1]))]
    return edge_and_freq

def lDistance(firstString, secondString):
    "Function to find the Levenshtein distance between two words/sentences - gotten from http://rosettacode.org/wiki/Levenshtein_distance#Python"
    if len(firstString) > len(secondString):
        firstString, secondString = secondString, firstString
    distances = range(len(firstString) + 1)
    for index2, char2 in enumerate(secondString):
        newDistances = [index2 + 1]
        for index1, char1 in enumerate(firstString):
            if char1 == char2:
                newDistances.append(distances[index1])
            else:
                newDistances.append(1 + min((distances[index1], distances[index1+1], newDistances[-1])))
        distances = newDistances
    return distances[-1]

def add_lev_distance(edge_and_freq):
    for edge in edge_and_freq:
        # print(edge_and_freq[edge])
        edge_and_freq[edge].append(lDistance(edge[0], edge[1]))
    edge_freq_lev = edge_and_freq
    return edge_freq_lev

def add_word_distance(parameter_list):
    """
    候选关键词之间词的个数，待思量，
    """
    pass

def calc_edge_weight(edge_features, omega):
    """
    注意edge_features的格式，字典，如'a'到'b'的一条边，特征为[1,2,3]，{('a','b'):[1,2,3], ('a','c'):[2,3,4]}
    ('analysi', 'lsa'): [0.2857142857142857, 5], ('languag', 'such'): [0.16666666666666666, 6]
    返回[['a','b',weight], ['a','c',weight]]
    """
    edge_weight = []
    for edge in edge_features:
        edge_weight_tmp = list(edge)
        edge_weight_tmp.append(float(edge_features[edge] * omega))
        edge_weight.append(tuple(edge_weight_tmp))
    return edge_weight
    
def build_graph(edge_weight):
    """
    建图，无向
    返回一个list，list中每个元素为一个图
    """
    graph = nx.Graph()
    graph.add_weighted_edges_from(edge_weight)
    return graph
    
def getTransMatrix(graph):
    P = nx.google_matrix(graph, alpha=1)
    # P /= P.sum(axis=1)
    P = P.T
    return P

def calcPi3(node_weight, node_list, pi, P, d):
    """
    r is the reset probability vector, pi3 is an important vertor for later use
    node_list = list(graph.node)
    """
    r = []
    for node in node_list:
        r.append(node_weight[node])
    r = np.matrix(r)
    r = r.T
    r = r / r.sum()
    pi3 = d * P.T * pi - pi + (1 - d) * r
    return pi3

def calcGradientPi(pi3, P, B, mu, alpha, d):
    P1 = d * P - np.identity(len(P))
    g_pi = (1 - alpha) * P1 * pi3 - alpha/2 * B.T * mu
    return g_pi

def get_xijk(i, j, k, edge_features, node_list):
    x = edge_features.get((node_list[i], node_list[j]), 0)
    if x == 0:
        return 0
    else:
        return x[k]
    # return edge_features[(node_list[i], node_list[j])][k]

def get_omegak(k, omega):
    return float(omega[k])

def calc_pij_omegak(i, j, k, edge_features, node_list, omega):
    n = len(node_list)
    l = len(omega)
    s1 = 0
    for j2 in range(n):
        for k2 in range(l):
            s1 += get_omegak(k2, omega) * get_xijk(i,j2,k2,edge_features,node_list)
    s2 = 0
    for k2 in range(l):
        s2 += get_omegak(k2, omega) * get_xijk(i,j,k2,edge_features,node_list)
    s3 = 0
    for j2 in range(n):
        s3 += get_xijk(i,j2,k,edge_features,node_list)
    result = (get_xijk(i,j,k,edge_features,node_list) * s1 - s2 * s3)/(s1 * s1)
    return float(result)

def calc_deriv_vP_omega(edge_features, node_list, omega):
    n = len(node_list)
    l = len(omega)
    #p_ij的顺序？
    m = []
    for i in range(n):
        for j in range(n):
            rowij = []
            for k in range(l):
                rowij.append(calc_pij_omegak(i, j, k, edge_features, node_list, omega))
            m.append(rowij)
    return np.matrix(m)

def calcGradientOmega(edge_features, node_list, omega, pi3, pi, alpha, d):
    g_omega = (1 - alpha) * d * np.kron(pi3, pi).T * calc_deriv_vP_omega(edge_features, node_list, omega)
    # g_omega算出来是行向量？
    return g_omega.T

def calcGradientPhi(pi3, node_features, node_list, alpha, d):
    #此处R有疑问, g_phi值有问题
    R_temp = []
    for key in node_list:
        R_temp.append(node_features[key])
    R = np.matrix(R_temp)
    g_phi = (1 - alpha) * (1 - d) * pi3.T * R
    return g_phi.T

def calcG(pi, pi3, B, mu, alpha, d):
    one = np.matrix(np.ones(B.shape[0])).T
    G = alpha * pi3.T * pi3 + (1 - alpha) * mu.T * (one - B * pi)
    return G

def updateVar(var, g_var, step_size):
    var = var - step_size * g_var
    var /= var.sum()
    return var

def init_value(n):
    value = np.ones(n)
    value /= value.sum()
    return np.asmatrix(value).T

def create_B(node_list, gold):
    keyphrases = gold.split()
    for i in range(len(keyphrases)):
        keyphrases[i] = normalized_token(keyphrases[i])
    n = len(node_list)

    for g in keyphrases:
        if g not in node_list:
            keyphrases.pop(keyphrases.index(g))

    for keyphrase in keyphrases:
        prefer = node_list.index(keyphrase)
        b = [0] * n
        b[prefer] = 1
        B = []
        for node in node_list:
            if node not in keyphrases:
                neg = node_list.index(node)
                b[neg] = -1
                c = b[:]
                B.append(c)
                b[neg] = 0
    return np.matrix(B)

def rank_doc(file_path, file_name, alpha=0.5, d=0.85, step_size=0.1, epsilon=0.00001, max_iter=2):
    file_text = readfile(file_path, file_name)
    tagged_tokens = get_tagged_tokens(file_text)
    filtered_text = get_filtered_text(tagged_tokens, ACCEPTED_TAGS)
    edge_and_freq = get_edge_freq(filtered_text)
    edge_features = add_lev_distance(edge_and_freq)#edge_freq_lev
    len_omega = len(list(edge_features.values())[0])
    omega = init_value(len_omega)
    edge_weight = calc_edge_weight(edge_features, omega)
    # print(edge_features)
    graph = build_graph(edge_weight)

    node_list = list(graph.node)
    if 'KDD' in file_path:
        raw_node_features = readfile('./data', 'KDD_node_features')
    else:
        raw_node_features = readfile('./data', 'WWW_node_features')
    node_features = read_node_features(node_list, raw_node_features, file_name)
    len_phi = len(list(node_features.values())[0])
    phi = init_value(len_phi)
    node_weight = calc_node_weight(node_features, phi)

    gold = readfile(file_path+'/../gold', file_name)
    B = create_B(node_list, gold)
    mu = init_value(len(B))

    pi = init_value(len(node_list))
    P = getTransMatrix(graph)
    pi3 = calcPi3(node_weight, node_list, pi, P, d)
    G0 = calcG(pi, pi3, B, mu, alpha, d)
    # print(pi3)
    g_pi = calcGradientPi(pi3, P, B, mu, alpha, d)
    g_omega = calcGradientOmega(edge_features, node_list, omega, pi3, pi, alpha, d)
    g_phi = calcGradientPhi(pi3, node_features, node_list, alpha, d)
    
    # print(g_pi)
    # print(g_omega)
    # print(g_phi)

    e = 1
    iteration = 0
    while  e > epsilon and iteration < max_iter:
        pi = updateVar(pi, g_pi, step_size)
        omega = updateVar(omega, g_omega, step_size)
        phi = updateVar(phi, g_phi, step_size)

        g_pi = calcGradientPi(pi3, P, B, mu, alpha, d)
        g_omega = calcGradientOmega(edge_features, node_list, omega, pi3, pi, alpha, d)
        g_phi = calcGradientPhi(pi3, node_features, node_list, alpha, d)

        edge_weight = calc_edge_weight(edge_features, omega)
        graph = build_graph(edge_weight)
        P = getTransMatrix(graph)
        pi3 = calcPi3(node_weight, node_list, pi, P, d)
        G1 = calcG(pi, pi3, B, mu, alpha, d)
        e = abs(G1 - G0)
        # print(e)
        G0 = G1
        iteration += 1
        print(iteration)
    if iteration > max_iter:
        print("Over Max Iteration, iteration =", iteration)
    return pi, omega, phi, node_list



ACCEPTED_TAGS = ['NN', 'NNS', 'NNP', 'NNPS', 'JJ']
pi, omega, phi, node_list = rank_doc('./data/KDD/abstracts','679710')
print("pi:", pi.T)
print("omega:", omega.T)
print("phi:", phi.T)

print(node_list)


# tokens = nltk.word_tokenize(text)
# tagged_tokens = nltk.pos_tag(tokens)
# tagged_tokens = get_tagged_tokens(file_text)
# edge_features这个量最重要, 向量存储成列matrix