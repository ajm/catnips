import sys
import urllib2
import os
import getopt
import time
import glob
import string
import collections

try :
    from bs4 import BeautifulSoup

except ImportError :
    print >> sys.stderr, "Requires 'BeautifulSoup4' to run (pip install beautifulsoup4)"
    sys.exit(-1)


options = { 
            'delay' : 0.5,
            'fetch' : False,
            'build' : False,
            'pdf-method' : 'pdftotext'
          }

def usage() :
    print >> sys.stderr, """Usage %s [OPTIONS]
    -d NUM  --delay=NUM     (insert delay between downloads, default: %.1f seconds)
    -f      --fetch         (fetch all pdfs from all NIPS conferences)
    -b      --build         (build dataset from downloaded PDFs)
""" % (sys.argv[0], options['delay'])

def get_options() :
    global options

    try :
        opts,args = getopt.getopt(sys.argv[1:], "d:hfb", ["delay=", "fetch", "build", "help"])

    except getopt.GetoptError, err :
        print >> sys.stderr, err
        sys.exit(-1)

    for o,a in opts :
        if o in ('-d', '--delay') :
            try :
                options['delay'] = float(a) 
            except ValueError, ve :
                print >> sys.stderr, "Error: could not parse '%s', delay expected as float" % a
                sys.exit(-1)

        elif o in ('-h', '--help') :
            usage()
            sys.exit(0)

        elif o in ('-f', '--fetch') :
            options['fetch'] = True

        elif o in ('-b', '--build') :
            options['build'] = True

        else :
            print >> sys.stderr, "Error: unhandled option '%s'" % o
            sys.exit(-1)

def rm(filename) :
    try :
        os.remove(filename)
    except :
        pass

def get_pdftotext(pdf_name) :
    ret = os.system("pdftotext %s" % pdf_name)

    if ret != 0 :
        print >> sys.stderr, "Error: pdftotext returned %d" % ret
        sys.exit(-1)

    f = open(pdf_name[:-3] + "txt")
    payload = f.read()
    f.close()

    return payload

def get(pdf_name) :
    global options

    method = options['pdf-method']

    if method == 'pdftotext':
        return get_pdftotext(pdf_name)

    raise Exception("bad pdf method")

def clean(text) :
    goodchars = string.lowercase + "\n "
    return filter(lambda x: x in goodchars, text.lower()).split()

def bag_of_words(tokens) :
    bow = collections.Counter()

    for token in tokens :
        bow[token] += 1
    
    return bow

def merge_bag_of_words(bow_dict) :
    all_words = collections.Counter()

    for bow in bow_dict :
        all_words.update(bow_dict[bow])

    return all_words

def write_bag_of_words(bow_dict, year) :
    year_bow = merge_bag_of_words(bow_dict)
    words = sorted(year_bow.keys())

    # write bag of words for the year
    f = open("%s.bow" % year, 'w')

    for word in words :
        print >> f, "%s %d" % (word, year_bow[word])

    f.close()

    # write bag of words per paper
    f = open("%s_papers.bow" % year, 'w')

    for word in words :
        s = word

        for pdf in bow_dict :
            s += "\t%d" % bow_dict[pdf][word]

        print >> f, s

    f.close()

def get_pdfs() :
    global options
    website = 'http://books.nips.cc/'
    directory = os.path.join(os.getcwd(), 'pdfs')

    pdfs = []

    # get the URLs of all PDFs
    try :
        proceedings = BeautifulSoup(urllib2.urlopen(website))
        pages = proceedings.find_all('a') 

        count = 0
        total = len(pages)
        header = "\rdownloading NIPS proceedings:"
        print >> sys.stderr, "%s %d / %d" % (header, count, total),
        for page in pages : 
            conf = BeautifulSoup(urllib2.urlopen(website + page.get('href')))
            year = page.contents[0]

            for paper in filter(lambda x: x.contents[0] == '[pdf]', conf.find_all('a')) :
                pdfs.append((paper.get('href'), year))

            count += 1
            print >> sys.stderr, "%s %d / %d" % (header, count, total),

        print >> sys.stderr, "%s complete!" % header

    except urllib2.HTTPError, he :
        print >> sys.stderr, "\n%s" % str(he)
        sys.exit(-1)

    except urllib2.URLError, ue :
        print >> sys.stderr, "\n%s" % str(ue)
        sys.exit(-1)


    # create a directory, if necessary
    if not os.path.exists(directory) :
        try :
            os.makedirs(directory)

        except OSError, ose :
            print >> sys.stderr, ose
            sys.exit(-1)

    elif not os.path.isdir(directory) :
        print >> sys.stderr, "Error: '%s' exists, but is not a directory"
        sys.exit(-1)
        
    # download all pdfs, provide progress
    count = 0
    year_counts = collections.Counter()
    total = len(pdfs)
    header = "\rdownloading NIPS papers:"

    errfile = open('errors.txt', 'w')
    errcount = 0
    
    print >> sys.stderr, "%s %d / %d" % (header, count, total),
    for pdf,year in pdfs :
#        pdf_name = os.path.basename(pdf)
#        # only the most recent NIPS have good filenames
#        # many of the early conferences use just numbers
#        if not pdf_name.startswith('NIPS') :
#            pdf_name = os.path.basename(os.path.dirname(pdf)).upper() + "_" + pdf_name
#
#        pdf_dest = os.path.join(directory, pdf_name)

        pdf_dest = os.path.join(directory, "%s_%d.pdf" % (year, year_counts[year]))

        try :
            f = open(pdf_dest, 'w')
            f.write(urllib2.urlopen(pdf).read())
            f.close()
        
        except urllib2.HTTPError, he :
            rm(pdf_dest)
            print >> errfile, "HTTPError %d %s" % (he.getcode(), pdf)
            errcount += 1

        except urllib2.URLError, ue :
            rm(pdf_dest)
            print >> errfile, "URLError %s" % (pdf)
            errcount += 1

        count += 1
        year_counts[year] += 1
        print >> sys.stderr, "%s %d / %d" % (header, count, total),

        time.sleep(options['delay'])

    print >> sys.stderr, "%s complete! (%d errors, see errors.txt)" % (header, errcount)
    errfile.close()

def build_dataset() :
    directory = os.path.join(os.getcwd(), 'pdfs')
    pdfs = glob.glob(os.path.join(directory, "*pdf"))
    pdfs_by_year = {}

    for pdf in pdfs :
        year = os.path.basename(pdf).split('_')[0]
        
        if year not in pdfs_by_year :
            pdfs_by_year[year] = []

        pdfs_by_year[year].append(pdf)

    #years = set([os.path.basename(pdf).split('_')[0] for pdf in pdfs])

    for year in pdfs_by_year :
        pdf_bow = {}

        for pdf in pdfs_by_year[year] :
            pdf_bow[os.path.basename(pdf)] = bag_of_words(clean(get(pdf)))

        write_bag_of_words(pdf_bow, year)

def main() :
    global options

    get_options()
    
    if options['fetch'] :
        get_pdfs()

    if options['build'] :
        build_dataset()

    return 0

if __name__ == '__main__' :
    try :
        sys.exit(main())

    except KeyboardInterrupt :
        print "\nKilled by user..."

