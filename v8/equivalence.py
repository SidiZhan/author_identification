# -*- coding: utf-8 -*-
''' execfile("equivalence.py")  '''
print(__doc__)

import numpy as np
from scipy import stats
import itertools
import time
from db import feature_path, clf_path, equiv_path, plot_path

'''
Equivalence = EC = ec
Equivalence.sample_ec = ...
generated by 
'''
class Equivalence(object):
    target = np.array(['1','2']) #true labels for each sample
    sample_class = None # results of clf.predict_prob(), higher the more likely
    sample_eqClass = None # sparse matrix of question_class, value is the probability, value = zero means not in the ec
    classes = np.array(['1','2']) # true label of classes
    shape = (0,0) # nSample, nClass

    def __init__(self, target):
        self.target = target
        self.shape = (len(target),len(np.unique(target)))
        self.sample_class = np.zeros(self.shape)
        self.sample_eqClass = np.zeros(self.shape) # sparse matrix


    def set_class(self, test_index, classes, sample_class):
        self.classes = classes
        for i in range(len(test_index)):
            for j in range(len(classes)):
                self.sample_class[test_index[i]][np.where(self.classes == classes[j])[0]] = sample_class[i,j]


    def threshold(self, diffs, metric='mean'):
        thres = 0
        if metric == 'mean':
            thres = diffs.mean()
        elif metric == 'median':
            thres = np.median(diffs)
        elif metric == 'mode':
            around = np.around(diffs,decimals=5)
            thres= stats.mode(around).mode[0]
            if thres == 0:
                around = [a for a in around if a != 0]
                thres = np.min(around)
        elif metric == 'percentile':
            thres = np.percentile(diffs, 75)
        return thres


    '''
    equiv_algList = ['jump points','median','percentile','mode','mean']
    '''
    def equivalence_class(self, test_index, equiv_alg = "jump points"):
##        sample_classes_predict = None
        for i in test_index:
            j = np.argmax(self.sample_class[i])
            self.sample_eqClass[i][j] = self.sample_class[i][j]
        sample_class = self.sample_class[test_index]
        if equiv_alg == "jump points":
            sample_class_sorted = np.sort(sample_class, axis=1)[:,::-1] # larger, more precise
            sample_class_ind_sorted = np.argsort(sample_class, axis=1)[:,::-1]
            sample_class_diff = sample_class_sorted - np.column_stack((sample_class_sorted[:,1:],sample_class_sorted[:,-1]))
            thres = self.threshold(sample_class_diff, 'mean')
            inds = np.argmax(sample_class_diff, axis=1)
            jump_points = [(inds[i],sample_class_diff[i][inds[i]]) for i in range(len(inds)) ]
            for i in range(len(jump_points)):
                ind,value = jump_points[i]
                if value>=thres:
                    for ind in range(inds[i]+1):
                        self.sample_eqClass[test_index[i]][sample_class_ind_sorted[i,ind]] = sample_class[i][sample_class_ind_sorted[i,ind]]
        elif equiv_alg == 'median':
            for i in test_index:
                ind = np.where(self.sample_class[i]>=np.median(self.sample_class[i][np.where(self.sample_class[i]!=0)[0]]))[0]
                self.sample_eqClass[i][ind] = self.sample_class[i][ind]
        elif equiv_alg == 'percentile':
            for i in test_index:
                ind = np.where(self.sample_class[i]>=np.percentile(self.sample_class[i][np.where(self.sample_class[i]!=0)[0]],75))[0]
                self.sample_eqClass[i][ind] = self.sample_class[i][ind]
        elif equiv_alg == 'mode':
            for i in test_index:
                ind = np.where(self.sample_class[i]>stats.mode(self.sample_class[i][np.where(self.sample_class[i]!=0)[0]]).mode[0])[0] # mode choose smallest value
                self.sample_eqClass[i][ind] = self.sample_class[i][ind]
        elif equiv_alg == 'mean':                              
            for i in test_index:
                ind = np.where(self.sample_class[i]>=np.mean(self.sample_class[i][np.where(self.sample_class[i]!=0)[0]]))[0]
                self.sample_eqClass[i][ind] = self.sample_class[i][ind]
        return self.sample_eqClass[test_index]


    #sorted (descend) equivalence class (indices, evalue) for that question
    def equiv_class_question(self, q_index):
##        ec = np.trim_zeros(np.sort(self.sample_eqClass[q_index,:])[::-1])
        ev = len(np.where(self.sample_eqClass[q_index,:] != 0)[0])
        ind = np.argsort(self.sample_eqClass[q_index,:])[::-1]
        ec = [self.classes[ind[i]] for i in range(ev)]
        return ec

    #ec for that user
    def equiv_class_user(self, u_label = None, u_index = None):
        ec = None
        if u_index is None and u_label is not None:
##            u_index = np.where(self.classes == u_label)[0][0]
            u_index = self.classes.tolist().index(u_label)
        if u_index is not None:
            ind = np.where(self.sample_eqClass[:,u_index]!=0)[0]
            ec = [self.target[i] for i in ind]
##            ec = np.trim_zeros(np.sort(self.sample_eqClass[:,u_index])[::-1])
        return ec

    # nSample * 1, size of equivalence class
    def equiv_value(self, entity = 'q'):
        ev = None
        if entity == 'q':
            ev = [len(np.where(self.sample_eqClass[i] != 0)[0]) for i in range(self.shape[0])]
        elif entity == 'u':
            ev = [len(np.where(self.sample_eqClass[:,i] != 0)[0]) for i in range(self.shape[1])]
        return ev

    # a matrix (question,question)=1 means they are in the same eqClass
    def question_question_eqClass(self):
        qq_eqClass = np.zeros((self.shape[0],self.shape[0]),dtype=int)
        for i in range(self.shape[1]):
            ind = np.where(self.sample_eqClass[:,i]!=0)[0]
            for x, y in itertools.product(ind, ind):
                qq_eqClass[x,y]=1
        return qq_eqClass

    #predicted questions (indices) for that user
    def equiv_question_user(self, u_label = None, u_index = None):
        ind = None
        if u_index is None and u_label is not None:
            u_index = np.where(self.classes == u_label)[0][0]
        if u_label is not None:
            ind = np.where(self.sample_eqClass[:,u_index]!=0)[0]
        return ind

    #true questions indices for that user
    def equiv_question_user_true(self, u_label = None, u_index = None):
        ind = None
        if u_label is None:
            if u_index is not None:
                u_label = self.classes[u_index]
        if u_label is not None:
            ind = np.where(self.target == u_label)[0]
        return ind


if __name__ == "__main__":
    target = np.loadtxt("target.csv", delimiter=',')
    
    test_index = np.loadtxt('test_index[14].csv', dtype=int, delimiter=',')
    sample_class = np.loadtxt('sample_class[14][svm].csv', dtype=float, delimiter=',')
    classes = np.loadtxt("classes[14][svm].csv", dtype=str, delimiter=',')
    
    equiv = Equivalence((len(target),sample_class.shape[1]))
    equiv.set_class(test_index,classes,sample_class)
    equiv.equivalence_class("jump points")
    