import buildindex
import re
import os
import sys
from os import listdir
from os.path import isfile, join
import pickle
from nltk.stem import PorterStemmer
from nltk.tokenize import sent_tokenize, word_tokenize
import json
# import re
import math


NO_OF_CHARS = 256
 
def badCharHeuristic(string, size):
    badChar = [-1]*NO_OF_CHARS
    for i in range(size):
        badChar[ord(string[i])] = i;
    return badChar 

def search(pat, txt, badChar):
    match_table = []
    m = len(pat)
    n = len(txt) 
    s = 0
    while(s <= n-m):
        j = m-1
        while j>=0 and pat[j] == txt[s+j]:
            j -= 1
        if j<0:
            match_table.append(s)
            s += (m-badChar[ord(txt[s+m])] if s+m<n else 1)
        else:         
            s += max(1, j-badChar[ord(txt[s+j])])
    return match_table

class Query:

	def __init__(self, filenames):
		self.filenames = filenames
		self.index = buildindex.BuildIndex(self.filenames)
		self.invertedIndex = self.index.totalIndex
		self.regularIndex = self.index.regdex


	def one_word_query(self, word):
		pattern = re.compile('[\W_]+')
		word = pattern.sub(' ',word)
		if word in self.invertedIndex.keys():
			return self.rankResults([filename for filename in self.invertedIndex[word].keys()], word)
		else:
			return []

	def free_text_query(self, string):
		pattern = re.compile('[\W_]+')
		string = pattern.sub(' ',string)
		result = []
		for word in string.split():
			result += self.one_word_query(word)
		return self.rankResults(list(set(result)), string)

	def phrase_query(self, string):
		pattern = re.compile('[\W_]+')
		string = pattern.sub(' ',string)
		listOfLists, result = [],[]
		for word in string.split():
			listOfLists.append(self.one_word_query(word))
		setted = set(listOfLists[0]).intersection(*listOfLists)
		for filename in setted:
			temp = []
			for word in string.split():
				temp.append(self.invertedIndex[word][filename][:])
			# for i in range(len(temp)):
			# 	for ind in range(len(temp[i])):
			# 		temp[i][ind] -= i
			if set(temp[0]).intersection(*temp):
				result.append(filename)
		return self.rankResults(result, string)

	def make_vectors(self, documents):
		vecs = {}
		for doc in documents:
			docVec = [0]*len(self.index.getUniques())
			for ind, term in enumerate(self.index.getUniques()):
				docVec[ind] = self.index.generateScore(term, doc)
			vecs[doc] = docVec
		return vecs


	def query_vec(self, query):
		pattern = re.compile('[\W_]+')
		query = pattern.sub(' ',query)
		queryls = query.split()
		queryVec = [0]*len(queryls)
		index = 0
		for ind, word in enumerate(queryls):
			queryVec[index] = self.queryFreq(word, query)
			index += 1
		queryidf = [self.index.idf[word] for word in self.index.getUniques()]
		magnitude = pow(sum(map(lambda x: x**2, queryVec)),.5)
		freq = self.termfreq(self.index.getUniques(), query)
		tf = [x/magnitude for x in freq]
		final = [tf[i]*queryidf[i] for i in range(len(self.index.getUniques()))]
		return final

	def queryFreq(self, term, query):
		count = 0
		#print(query)
		#print(query.split())
		for word in query.split():
			if word == term:
				count += 1
		return count

	def termfreq(self, terms, query):
		temp = [0]*len(terms)
		for i,term in enumerate(terms):
			temp[i] = self.queryFreq(term, query)
			#print(self.queryFreq(term, query))
		return temp

	def dotProduct(self, doc1, doc2):
		if len(doc1) != len(doc2):
			return 0
		return sum([x*y for x,y in zip(doc1, doc2)])

	def rankResults(self, resultDocs, query):
		vectors = self.make_vectors(resultDocs)
		queryVec = self.query_vec(query)
		results = [[self.dotProduct(vectors[result], queryVec), result] for result in resultDocs]
		results.sort(key=lambda x: x[0])
		results = [x[1] for x in results]
		return results



filenames = []
indexing = "y"
if os.stat("names.pkl").st_size != 0:
	names = open("names.pkl", 'rb')
	filenames = pickle.load(names)
	k = input("Enter 1 to add file \n2 to delete file \n3 to search:\n")
else:
	k = "1"
if k == '1':
	name = input("Enter filename with extension: ")
	filenames.append(name)
	names1 = open("names.pkl", 'wb')
	pickle.dump(filenames, names1)

elif k == '2':
	print(filenames)
	name = input("Enter name of file to be deleted: ")
	filenames.remove(name)
	names1 = open("names.pkl", 'wb')
	pickle.dump(filenames, names1)
	
else:
	ps = PorterStemmer()
	pattern1 = input("Enter pattern to be searched: ")
	pattern = ""
	for word in pattern1.split():
		pattern = pattern + " " + ps.stem(word)
	#pattern="book first"
	mypath=sys.argv[1]
	onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]
	updates=[]
	dtime=-1.0
	fname="data.pkl"
	if fname in onlyfiles:
		dtime=os.path.getmtime(mypath+"/"+fname)
	mtime=0.0
	for f in filenames:
		time=os.path.getmtime(mypath+"/"+f)
		if(time>dtime):
			updates.append(f)
		mtime=max(time,mtime)
	# todo = [value for value in updates if value in filenames]
	if dtime==-1:
		q = Query(filenames)
		output=open('data.pkl','wb')
		pickle.dump(q,output)
	elif len(updates):
	# 	pkl_file = open('data.pkl', 'rb')
	# 	q=pickle.load(pkl_file)
		# pkl_file.close()
		# print(updates)
		indexing = input("Inverse-indexing is out of date, do you want to build indexing first? (y/n): ")
		if (indexing == "n"):
			pattern = ps.stem(pattern)
			badChar = badCharHeuristic(pattern, len(pattern))
			for file in filenames:
				matches = []
				lineno = 0
				doc = open(file, 'r')
				for line in doc:
					line1 = line.lower()
					lineno += 1
					matches = search(pattern, line1, badChar)
					if len(matches) > 0:
					      print(file + ": " + str(lineno) + ": " + line)	
		with open("data.pkl", "rb") as f:
			q = pickle.load(f)
		q.index.tf = {}
		q.index.df = {}
		q.index.idf = {}
		q.filenames=filenames
		q.index.filenames = filenames
		file_to_terms = q.index.process_files(updates)
		for file in file_to_terms.keys():
			q.index.file_to_terms[file]=file_to_terms[file]
		regdex = q.index.regIndex(updates)
		for file in regdex.keys():
			q.index.regdex[file]=regdex[file]
		q.index.totalIndex = q.index.execute()
		q.index.vectors = q.index.vectorize()
		q.index.mags = q.index.magnitudes(q.index.filenames)
		q.index.populateScores()
		q.invertedIndex = q.index.totalIndex
		output=open('data.pkl','wb')
		q.regularIndex = q.index.regdex
		pickle.dump(q,output)
	else:
		pkl_file = open('data.pkl', 'rb')
		q=pickle.load(pkl_file)
	# print(q.one_word_query("along"))
	llist=q.regularIndex
	#print(llist)
	#with open('data.json','w') as f:
	#	json.dump(llist['stopwords.txt'],f)
	result=q.phrase_query(pattern)
	# print(result)
	for file in result:
		# if file=="pg135.txt":
		# 	break
		if indexing == "n":
			break
		filedata= []
		doc1 = open(file, 'r').readlines()
		# filedata = doc.split('\n')
		doc1 = [x.strip() for x in doc1]
		doc = []
		for x in doc1:
			#x = x.lower()
			doc.append(x)
		# if pattern in llist[file].keys():
		out1=[]
		for word in pattern.split():
			word=ps.stem(word)
			out1.append(llist[file][word])
		#print(out1)
		out2=set(out1[0]).intersection(*out1)
		out2=sorted(out2)
		out = list(out2)
		out3 = list(out2)
		#if file == "pg74.txt":
		#	print(out)
		#	print(out1)
		for i in range(len(out)):
			index = out[i]
			#if file == "pg74.txt":
			#	print(out3)
			#	print(index)
			#	print(out)
			llistnew=doc[index].lower()
			# print(file + ": " + str(index) + ": " + doc[index])
			k1=len(doc[index].split())
			k2=len(pattern.split())
			for i in range(0,k1-k2+1):
				temp = llistnew.split()[i:i+len(pattern.split())]
				for i in range(len(temp)):
					temp[i] = temp[i].lower()
					temp[i] = ps.stem(temp[i])
					temp[i] = temp[i].strip('.')
					temp[i] = temp[i].strip(',')
				if pattern.split() == temp:
					# print("Match:"+str(pattern.split()) + " : " + str(doc[index].lower().split()[i:i+len(pattern.split())]))
					print("    " + file + ": " + str(index) + ": " + doc[index])
					out3.remove(index)
					break
		print()
		out = out3
		for index in out:
			llistnew=doc[index].lower()
			poplist=pattern.split()
			for word in llistnew.split():
				# if poplist:
				# 	print(word + " : " + poplist[0])
				# else:
				# 	print(word + " : empty list")
				if poplist and poplist[0] == word:
					poplist.pop(0)
			if poplist:
				p=1
			else:	
				print("    " + file + ": " + str(index) + ": " + doc[index])
				out.remove(index)
		print()
		for index in out:
			print("    " + file + ": " + str(index) + ": " + doc[index])
		print()
		print()
