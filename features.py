import csv
import cPickle
import itertools
import random
import sys

class Author():
    def __init__(self):
        self.papers = []
        self.journals = []
        self.conferences = []

class Paper():
    def __init__(self):
        self.authors = []
        self.year = -1
        self.venueid = -1
        self.title = None
        self.affiliation = None
        self.paperrank = 0

class Venue():
    def __init__(self):
        self.papers = []

def loadAuthorsPapers(path='dataRev2/'):
    print 'loading authors and papers...'

    authors = {}
    papers = {}
    with open(path + 'PaperAuthor.csv') as csvfile:
        reader = csv.reader(csvfile)
        reader.next() # skip header
        for paperid, authorid, name, affiliation in reader:
            paperid, authorid = int(paperid), int(authorid)
            if paperid not in papers:
                papers[paperid] = Paper()
            papers[paperid].authors.append(authorid)
            # no need for this yet..
            papers[paperid].affiliation = affiliation

            if authorid not in authors:
                authors[authorid] = Author()
            authors[authorid].papers.append(paperid)

    notfound = 0
    with open(path + 'Paper.csv') as csvfile:
        reader = csv.reader(csvfile)
        reader.next() # skip header
        for paperid, title, year, conferenceid, journalid, keyword in reader:
            paperid, year, conferenceid, journalid = int(paperid), int(year), int(conferenceid), int(journalid)
            try:
                if year > 1400 and year < 2014:
                    papers[paperid].year = year
                if journalid > 0:
                    # to map journals and conferences to the same id space, just add 10k to the id because the maxmimum conference id is ~5k
                    papers[paperid].venueid = journalid + 10000
                if conferenceid > 0:
                    # some papers are in both a conference and a journal?
                    papers[paperid].venueid = conferenceid
                # no need for this yet...
                papers[paperid].title = title
            except KeyError:
                notfound += 1

    for paper in papers.values():
        # remove duplicate authors
        paper.authors = list(set(paper.authors))

    # some (~500) papers don't have author information? could be an artifact of how the data was generated, but only a tiny fraction...
    #print 'unable to find ' + str(notfound) + ' papers'

    print 'done.'
    return authors, papers

def loadVenues(authors, papers):
    
    venues = {}
    for pid in papers.keys():
        vid = papers[pid].venueid
        if vid > 0:
            if vid not in venues:
                venues[vid] = Venue()
            venues[vid].papers.append(pid)
    
    return venues

def csvGenerator(mode, path='dataRev2/'):

    if mode == 'train':
        with open(path + 'Train.csv') as csvfile:
            reader = csv.reader(csvfile)
            reader.next() # skip header
            for authorid, confirmedids, deletedids in reader:
                authorid = int(authorid)
                confirmedids = [int(id) for id in confirmedids.split(' ')]
                deletedids = [int(id) for id in deletedids.split(' ')]
                yield authorid, confirmedids + deletedids

    elif mode == 'test':
        with open(path + 'Valid.csv') as csvfile:
            reader = csv.reader(csvfile)
            reader.next() # skip header
            for authorid, paperids in reader:
                authorid = int(authorid)
                paperids = [int(id) for id in paperids.split(' ')]
                yield authorid, paperids

    else:
        print 'mode must be "train" or "test"'
        raise ValueError


def saveFeature(feature, name, mode):
    filename = name + '.' + mode
    print 'saving feature to', filename, '...'
    cPickle.dump(feature, open(filename, 'wb'))

def labels(mode='train', path='dataRev2/'):

    labels = []
    if mode == 'train':
        with open(path + 'Train.csv') as csvfile:
            reader = csv.reader(csvfile)
            reader.next() # skip header
            for authorid, confirmedids, deletedids in reader:
                mylabels = []
                authorid = int(authorid)
                confirmedids = [int(id) for id in confirmedids.split(' ')]
                deletedids = [int(id) for id in deletedids.split(' ')]

                for cid in confirmedids:
                    mylabels.append(1)  # 1 = confirmed
                for did in deletedids:
                    mylabels.append(0)  # 0 = deleted
                labels.append(mylabels)

    elif mode == 'test':
        for authorid, paperids in csvGenerator(mode=mode, path=path):
            labels.append([authorid, paperids])

    else:
        print 'mode must be "train" or "test"'
        raise ValueError

    saveFeature(labels, name='labels', mode=mode)

def nauthors(papers, authors, mode='train', path='dataRev2/'):
    '''
    Number of authors on paper
    '''

    print 'generating nauthors feature...'

    features = []
    for authorid, paperids in csvGenerator(mode=mode, path=path):
        features.append([len(papers[pid].authors) for pid in paperids])

    saveFeature(features, name='nauthors', mode=mode)

def npapers(papers, authors, mode='train', path='dataRev2/'):
    '''
    Number of papers written by author
    '''

    print 'generating npapers feature...'

    features = []
    for authorid, paperids in csvGenerator(mode=mode, path=path):
        features.append([len(authors[authorid].papers) for pid in paperids])

    saveFeature(features, name='npapers', mode=mode)

def year(papers, authors, mode='train', path='dataRev2/'):
    '''
    Year paper was written
    '''

    print 'generating year feature...'

    features = []
    for authorid, paperids in csvGenerator(mode=mode):
        features.append([papers[pid].year for pid in paperids])

    saveFeature(features, name='year', mode=mode)

def nsamevenue(papers, authors, mode='train', path='dataRev2/'):
    '''
    Number of times author has published at venue
    '''

    print 'generating nsamevenue feature...'

    features = []
    for authorid, paperids in csvGenerator(mode=mode, path=path):
        myfeatures = []
        for pid in paperids:
            if papers[pid].venueid > 0:
                myfeatures.append([papers[pid2].venueid for pid2 in authors[authorid].papers].count(papers[pid].venueid))
            else:
                myfeatures.append(-1)

        features.append(myfeatures)

    saveFeature(features, name='nsamevenue', mode=mode)

def nattrib(papers, authors, mode='train', path='dataRev2/'):
    '''
    Number of times paper has been attributed to author
    '''

    print 'generating nattrib feature...'

    features = []
    for authorid, paperids in csvGenerator(mode=mode, path=path):
        myfeatures = []
        for pid in paperids:
            myfeatures.append(authors[authorid].papers.count(pid))
        features.append(myfeatures)

    saveFeature(features, name='nattrib', mode=mode)

def paperrank(papers, authors, mode='train', path='dataRev2/', beta=0.3, nwalks=1000):
    '''
    Personalized page rank
    PC - I have no idea why this works...
    '''
    
    print 'generating paperrank feature...'
    
    for paper in papers.values():
        paper.paperrank = 0
            
    for authorid, paperids in csvGenerator(mode=mode, path=path):
        for pid in authors[authorid].papers:
            for walk in range(nwalks):
                current_pid = pid
                if len(papers[current_pid].authors) > 1:
                    papers[current_pid].paperrank += 1
                    while (random.random() < beta):   # will pass with probability beta...
                        random_aid = authorid
                        while (random_aid == authorid):
                            random_aid = random.choice(papers[current_pid].authors)
                        current_pid = random.choice(authors[random_aid].papers)
                        papers[current_pid].paperrank += 1
    
    features = []
    for authorid, paperids in csvGenerator(mode=mode, path=path):
        features.append([papers[pid].paperrank for pid in paperids])
       
    saveFeature(features, name='paperrank', mode=mode) 
    
def globalpaperrank(papers, authors, mode='train', path='dataRev2/'):
    '''
    Degree on the above paperrank graph
    '''
    
    print 'generating globalpaperrank feature...'
    
    features = []
    for authorid, paperids in csvGenerator(mode=mode, path=path):
        myfeatures = []
        for paperid in paperids:
            globalpaperrank = 0
            for aid in papers[paperid].authors:
                if aid != authorid:
                    for pid in authors[aid].papers:
                        globalpaperrank += 1
                            
            myfeatures.append(globalpaperrank)
        features.append(myfeatures)
    
    saveFeature(features, name='globalpaperrank', mode=mode) 

def ncoauthor(papers, authors, mode='train', path='dataRev2/'):
    '''
    Number of times author has published with coauthors on paper
    '''

    print 'generating ncoauthor feature...'

    features = []
    for authorid, paperids in csvGenerator(mode=mode, path=path):
        myfeatures = []
        for paperid in paperids:
            ncoauthor = 0
            for coauthorid in papers[paperid].authors:
                if coauthorid != authorid:
                    for pid in authors[coauthorid].papers:
                        if pid != paperid and authorid in papers[pid].authors:
                            ncoauthor += 1
            myfeatures.append(ncoauthor)
        features.append(myfeatures)

    saveFeature(features, name='ncoauthor', mode=mode)

def nappear(papers, authors, mode='train', path='dataRev2/'):

    print 'generating nappear feature...'
    
    features = []
    for authorid, paperids in csvGenerator(mode=mode, path=path):
        myfeatures = []
        for pid in paperids:
            myfeatures.append(paperids.count(pid))
        features.append(myfeatures)
        
    saveFeature(features, name='nappear', mode=mode) 

if __name__ == '__main__':

    authors, papers = loadAuthorsPapers()
    #venues = loadVenues(authors, papers)

    for mode in ['train', 'test']:
        labels(mode=mode)
        nauthors(papers, authors, mode=mode)
        npapers(papers, authors, mode=mode)
        year(papers, authors, mode=mode)
        nsamevenue(papers, authors, mode=mode)
        nattrib(papers, authors, mode=mode)
        globalpaperrank(papers, authors, mode=mode)
        paperrank(papers, authors, mode=mode)
        ncoauthor(papers, authors, mode=mode)
        nappear(papers, authors, mode=mode)
