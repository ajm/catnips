import sys
import urllib2
import os
import getopt
import time

try :
    from bs4 import BeautifulSoup

except ImportError :
    print >> sys.stderr, "Requires 'BeautifulSoup4' to run (pip install beautifulsoup4)"
    sys.exit(-1)


options = { 
            'delay' : 0.5,
            'fetch' : False,
            'build' : False
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
            
            for paper in filter(lambda x: x.contents[0] == '[pdf]', conf.find_all('a')) :
                pdfs.append(paper.get('href'))

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
    total = len(pdfs)
    header = "\rdownloading NIPS papers:"
    print >> sys.stderr, "%s %d / %d" % (header, count, total),
    for pdf in pdfs :
        pdf_name = os.path.basename(pdf)
        
        try :
            f = open(os.path.join(directory, pdf_name), 'w')
            f.write(urllib2.urlopen(pdf).read())
            f.close()
        
        except urllib2.HTTPError, he :
            print >> sys.stderr, "\n%s" % str(he)
            sys.exit(-1)

        except urllib2.URLError, ue :
            print >> sys.stderr, "\n%s" % str(ue)
            sys.exit(-1)

        count += 1
        print >> sys.stderr, "%s %d / %d" % (header, count, total),

        time.sleep(options['delay'])

    print >> sys.stderr, "%s complete!" % header

def build_dataset() :
    pass

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

