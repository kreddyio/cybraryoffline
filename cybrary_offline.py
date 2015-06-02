#!/usr/bin/python2
import argparse
import sys
import urllib2
import urllib
import cookielib
from threading import Thread
import re
import os
from bs4 import BeautifulSoup as bs

BASE_URL = 'http://cybrary.it'
AUTH_URL = 'https://www.cybrary.it/wp-login.php'
COURSE_URL = 'http://cybrary.it/course/%s'

DEFAULT_HEADERS = {
    'User-Agent' : 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.94 Chrome/37.0.2062.94 Safari/537.36',
    'Accept' : '*/*',
    'Accept-Encoding' : 'gzip,deflate,sdch',
    'Accept-Language' : 'en-US,en;q=0.8',
    'Referer': 'https://cybrary.it/wp-login.php',
    'Origin': 'https://cybrary.it',
    'Connection' : 'keep-alive',
    'X-Requested-With': 'XMLHttpRequest',
    'Content-Type': 'application/x-www-form-urlencoded'
}


def parse_arguments():
    # Uses argparse.Argument parser to parse
    # Commandline arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--shortname", help="""Short name of the course being downloaded.
        This option is required when running the script for the first time""")
    parser.add_argument("-u", "--user", help="username in cybrary")
    parser.add_argument("-p", "--password", help="cybrary Password")
    args = parser.parse_args()

    return args


def login(user,pwd):
	cj = cookielib.CookieJar()
	data = {
		'log':user,
		'pwd':pwd,
		'wp-submit':'Log In',
		'redirect_to':'http://www.cybrary.it',
		'testcookie':'1'
	}
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	try:
		res = opener.open(urllib2.Request(AUTH_URL,urllib.urlencode(data),DEFAULT_HEADERS))
	except Exception, e:
		raise e
	return cj


def parse_course(url,cookie):
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
	data = opener.open(urllib2.Request(url)).read()
	soup = bs(data)
	div_modules = soup.findAll("div",class_="modulelisting")[0]
	title = soup.findAll("h1",class_="single-pagetitle")[0].string
	info = {}
	info['title'] = title
	modules = div_modules.findAll("h4")
	for i in xrange(len(modules)):
		modules[i] = modules[i].a.string
	info['modules'] = modules
	video = div_modules.findAll("div",class_="slide_toggle_content")
	vid_list = []
	for i in video:
		cur_list = i.findAll("div",class_="cvideo")
		for j in xrange(len(cur_list)):
			cur_list[j] = cur_list[j].a['href']
		vid_list.append(cur_list)
	info['videos'] = vid_list
	info['modlen'] = len(modules)
	return info


def vid_info(url,cookie):
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
	data = opener.open(urllib2.Request(url)).read()
	soup = bs(data)
	vid_title = soup.findAll("h1",class_="single-pagetitle")[0].string
	# print vid_title
	vid_link = soup.findAll("div",class_="video-embed-container")[0].iframe
	rq = urllib2.Request(vid_link['src'])
	rq.add_header('Referer',url)
	if_src = bs(opener.open(rq).read()).prettify()
	m3u8_link = re.findall("\"hd\":\"(.*?)\"},",if_src)[0]
	rq2 = urllib2.Request(m3u8_link)
	rq2.add_header('Referer',vid_link["src"])
	new_data = opener.open(rq2).read()
	# print new_data
	ind_link = 'http://'+re.findall(r"http://(.*?).m3u8",new_data)[0]+".m3u8"
	# print ind_link
	rq3 = urllib2.Request(ind_link)
	rq3.add_header('Referer',m3u8_link)
	seg_data = opener.open(rq3).read()
	# print seg_data
	segs = re.findall("http://(.*?).ts",seg_data)
	for i in xrange(len(segs)):
		segs[i] = 'http://'+segs[i]+'.ts'

	# sys.exit(1)
	return [vid_title,segs]
	

def download(urls,dest,cookie):
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
	print 'Started '+dest
	for url in urls:
		try:
			u = opener.open(urllib2.Request(url))
			f = open(dest,"ab")
			block = 8192
			while True:
				buf = u.read(block)
				if not buf:
					break
				f.write(buf)
			f.close()
			u.close()
	    #handle errors
		except urllib2.HTTPError, e:
			print "HTTP Error:", e.code, url
		except urllib2.URLError, e:
			print "URL Error:", e.reason, url
		except Exception,e:
			print "Error!",e


def main():
	args = parse_arguments()
	if args.user and args.password:
		try:
			cookie = login(args.user,args.password)
		except Exception, e:
			raise e
	if args.shortname:
		info = parse_course(COURSE_URL%(args.shortname),cookie)
	# print info
	l = info['modlen']
	if not os.path.exists(info['title']): os.makedirs(info['title'])
	for i in xrange(l):
		new_path = info['title']+'/'+info['modules'][i]
		if not os.path.exists(new_path):
			os.makedirs(new_path)
		c = 1
		for j in info['videos'][i]:
			vid = vid_info(j,cookie)
			save_path = new_path+'/'+str(c)+'.'+vid[0]+'.mp4'
			dl = Thread(target=download, args=[vid[1],save_path,cookie])
			dl.setDaemon(True)
			dl.start()
			dl.join()
			print 'Download Finished.\n'
			c += 1

if __name__ == '__main__':
	main()