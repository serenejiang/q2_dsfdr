import numpy as np
import pandas as pd
import scipy as sp
import scipy.stats

import matplotlib as mpl
import matplotlib.pyplot as plt


# data transformation
def rankdata(data):
        rdata=np.zeros(np.shape(data))
        for crow in range(np.shape(data)[0]):
                rdata[crow,:]=sp.stats.rankdata(data[crow,:])
        return rdata

def logdata(data):
        data[data < 2] = 2
        data = np.log2(data)
        return data

def apdata(data):
        data[data != 0] = 1
        return data

def normdata(data):
        data = data / np.sum(data, axis = 0)
        return data


# different methods to calculate test statistic
def meandiff(data, labels):
        mean0 = np.mean(data[:, labels==0], axis = 1)
        mean1 = np.mean(data[:, labels==1], axis = 1)
        tstat = abs(mean1 - mean0)
        return tstat


def mannwhitney(data, labels):
        group0 = data[:, labels == 0]
        group1 = data[:, labels == 1]
        tstat = np.array([scipy.stats.mannwhitneyu(group0[i, :],
                group1[i, :]).statistic for i in range(np.shape(data)[0])])
        return tstat


# kruwallis give a column vector while others give row vector
def kruwallis(data, labels):
        n = len(np.unique(labels))
        allt=[]
        for cbact in range(np.shape(data)[0]):
                group = []
                for j in range(n):
                        group.append(data[cbact, labels == j])
                tstat = scipy.stats.kruskal(*group).statistic
                allt.append(tstat)
        return allt

def stdmeandiff(data, labels):
        mean0 = np.mean(data[:, labels==0], axis = 1)
        mean1 = np.mean(data[:, labels==1], axis = 1)
        sd0 = np.std(data[:, labels==0], axis = 1, ddof = 1)
        sd1 = np.std(data[:, labels==1], axis = 1, ddof = 1)
        tstat = abs(mean1 - mean0)/(sd1 + sd0)
        return tstat






# new fdr method
def _pfdr(data, labels, method, transform=None,
         alpha=0.1,numperm=1000, fdrbefast=False):

        if transform == 'rankdata':
                data = rankdata(data)
        elif transform == 'logdata':
                data = logdata(data)
        elif transform == 'apdata':
                data = apdata(data)
        elif transform == 'normdata':
                data = normdata(data)

        #print('permuting')
        numbact=np.shape(data)[0]

        if method == "meandiff":
                method = meandiff
                t=method(data,labels)
                numsamples=np.shape(data)[1]
                p=np.zeros([numsamples,numperm])
                k1=1/np.sum(labels == 0)
                k2=1/np.sum(labels == 1)
                for cperm in range(numperm):
                        np.random.shuffle(labels)
                        p[labels==0, cperm] = k1
                p2 = np.ones(p.shape)*k2
                p2[p>0] = 0
                mean1 = np.dot(data, p)
                mean2 = np.dot(data, p2)
                u = np.abs(mean1 - mean2)

        elif method == 'mannwhitney':
                method = mannwhitney
                t=method(data,labels)
                u=np.zeros([numbact,numperm])
                for cperm in range(numperm):
                        rlabels=np.random.permutation(labels)
                        rt=method(data,rlabels)
                        u[:,cperm]=rt

        elif method == 'kruwallis':
                method = kruwallis
                t=method(data,labels)
                u=np.zeros([numbact,numperm])
                for cperm in range(numperm):
                        rlabels=np.random.permutation(labels)
                        rt=method(data,rlabels)
                        u[:,cperm]=rt

        elif method == 'stdmeandiff':
                method = stdmeandiff
                t=method(data,labels)
                u=np.zeros([numbact,numperm])
                for cperm in range(numperm):
                        rlabels=np.random.permutation(labels)
                        rt=method(data,rlabels)
                        u[:,cperm]=rt


        elif method == 'spearman' or method == 'pearson':
                if method == 'spearman':
                        data = rankdata(data)
                        labels = sp.stats.rankdata(labels)
                meanval=np.mean(data,axis=1).reshape([data.shape[0],1])
                data=data-np.repeat(meanval,data.shape[1],axis=1)
                labels=labels-np.mean(labels)
                t=np.abs(np.dot(data, labels))
                permlabels = np.zeros([len(labels), numperm])
                for cperm in range(numperm):
                        rlabels=np.random.permutation(labels)
                        permlabels[:,cperm] = rlabels
                u=np.abs(np.dot(data,permlabels))

        elif method == 'nonzerospearman' or method == 'nonzeropearson':
                t = np.zeros([numbact])
                u = np.zeros([numbact, numperm])
                for i in range(numbact):
                        index = np.nonzero(data[i, :])
                        label_nonzero = labels[index]
                        sample_nonzero = data[i, :][index]
                        if method == 'nonzerospearman':
                                sample_nonzero = sp.stats.rankdata(sample_nonzero)
                                label_nonzero = sp.stats.rankdata(label_nonzero)
                        sample_nonzero = sample_nonzero - np.mean(sample_nonzero)
                        label_nonzero = label_nonzero - np.mean(label_nonzero)
                        t[i] = np.abs(np.dot(sample_nonzero, label_nonzero))

                        permlabels = np.zeros([len(label_nonzero), numperm])
                        for cperm in range(numperm):
                                rlabels=np.random.permutation(label_nonzero)
                                permlabels[:,cperm] = rlabels
                        u[i, :] = np.abs(np.dot(sample_nonzero, permlabels))

        else:
                # method = userfunction
                #t=method(data,labels)
                u=np.zeros([numbact,numperm])
                for cperm in range(numperm):
                        rlabels=np.random.permutation(labels)
                        rt=method(data,rlabels)
                        u[:,cperm]=rt

        #print('calculating fdr')
        #print(np.shape(u))

        #print('fixing floating point errors')
        for crow in range(numbact):
                closepos=np.isclose(t[crow],u[crow,:])
                u[crow,closepos]=t[crow]

        #print('rank transforming')
        # rank transfrom the results
        for crow in range(numbact):
                cvec=np.hstack([t[crow],u[crow,:]])
                cvec=sp.stats.rankdata(cvec,method='min')
                t[crow]=cvec[0]
                u[crow,:]=cvec[1:]

        # now calculate the fdr for each t value
        #print('fdring')
        sortt=list(set(t))
        sortt=np.sort(sortt)
        if fdrbefast:
                sortt=sortt[::-1]
        #print('ok')
        foundit=False
        allfdr=[]
        allt=[]
        for ct in sortt:
                realnum=np.sum(t>=ct)
                if realnum == 0:
                        fdr = (1+np.count_nonzero(u>=ct))/(numperm+1)
                else:
                        fdr=(realnum+np.count_nonzero(u>=ct)) / (realnum*(numperm+1))
                allfdr.append(fdr)
                allt.append(ct)
                # print(fdr)

                if fdrbefast:
                        if fdr>alpha:
                                break
                        realct=ct

                if fdr<=alpha:
                        if not foundit:
                                realct=ct
                        foundit=True

        if not foundit:
                #print('not low enough. number of rejects : 0')
                reject=np.zeros(numbact,dtype=int)
                reject= (reject>10)
                return reject

        # and fill the reject null hypothesis
        reject=np.zeros(numbact,dtype=int)
        reject= (t>=realct)
        maxrej=np.max(np.where(reject)[0])
        #print('number of rejects : %d' % np.sum(reject))
        return reject


## qiime 2 layout goes below
from numpy import log, sqrt
from scipy.stats import (f_oneway, kruskal, mannwhitneyu,
                         wilcoxon, ttest_ind, ttest_rel, kstest, chisquare,
                         friedmanchisquare)
from skbio.stats.composition import clr

_sig_tests = {'f_oneway': f_oneway,
              'kruskal': kruskal,
              'mannwhitneyu': mannwhitneyu,
              'wilcoxon': wilcoxon,
              'ttest_ind': ttest_ind,
              'ttest_rel': ttest_rel,
              'kstest': kstest,
              'chisquare': chisquare,
              'friedmanchisquare': friedmanchisquare}


_transform_functions = {'sqrt': sqrt,
                        'log': log,
                        'clr': clr}

def statistical_tests():
    return list(_sig_tests.keys())


def transform_functions():
    return list(_transform_functions.keys())


def permutation_fdr(output_dir: str,
                    table : pd.DataFrame,
                    metadata: qiime.MetadataCategory,
                    statistical_test: str='f_oneway',
                    transform_function: str='rank',
                    permutations: int=1000) -> None:
    # See q2-composition for more details
    # https://github.com/qiime2/q2-composition/blob/master/q2_composition/_ancom.py

    # TODO : Consider renaming the functions to match q2-composition

    metadata_series = metadata.to_series()[table.index]
    # Make sure that metadata and table match up
    reject_idx = _pfdr(table.value,
                       metadata_series.values,
                       statistical_test,
                       transform_function,
                       alpha, numperm)
    # TODO : create heatmap using matplotlib imshow
    # and embed inside of html

    # TODO : write table to a csv