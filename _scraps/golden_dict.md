---
layout: post
title: GoldenDict 在线词典配置
tags: GoldenDict iciba bing
date: 2023-02-02
update: 2023-02-02
---
GoldenDict是一款跨平台的词典软件，支持各种不同格式的在线/离线词典，支持划词翻译等。

对于在线词典，GoldenDict会把网页的内容内嵌到软件主页面或者划词翻译的弹窗中。
但是有个问题，在线词典的页面内容中通常有很多无用空间，比如空白，广告等，使用起来体验不佳。

GoldenDict的在线词典没有提供展示页面部分内容的功能，为了达到在界面中重新格式化在线词典内容的目的，可以通过`program`类型的词典。通过我们自定义的程序来处理在线词典的返回网页供GoldenDict读取。

以下方案程序基于<https://github.com/goldendict/goldendict/issues/105#issuecomment-213533788> 做了修改，
可以把iciba的搜索框以及释义上的广告去掉，把bing词典的搜索框去掉，节省显示空间。

## 配置方法
1. 设置Program类型的词典分别为：
  * iciba `/path/getxpath http://www.iciba.com/word?w=%GDWORD% "" "" "" ['/html/body/div/main/div[position()<3]','/html/body/div/div']`
  * bing `/path/getxpath https://cn.bing.com/dict/search?q=%GDWORD% "" "" "" ['/html/body/header']`

2. `/path/getxpath`内容如下，脚本需要执行权限。基本原理就是获取到词典的网页内容，按需修改后返回：

```
#!/usr/bin/python3
import urllib.request
import urllib.parse
import sys
from lxml.html import fromstring, tostring

# Original post:
# https://github.com/goldendict/goldendict/issues/105#issuecomment-245933314

"""
Arguments: url
           select_div             class attribute of the selected part
                                   (used only in output, not for actual selection)
           select_xpath           xpath of the elements that will be output
                                   (leave empty for outputting whole page)
           css_file               file in the same dir as this script
           elements_for_removal   array of xpath addresses,
                                    e.g. ['//div[@class="copyright"]','//input','//img']
           values_for_javascript  (optional) hash of 'key': 'value' pairs
"""

def get_page():
    headers = {}
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0',
               'Accept': '*/*'}
    if len(sys.argv)==7:
      values = eval(sys.argv[6])
      data = urllib.parse.urlencode(values).encode('utf8')
      request = urllib.request.Request(url, data, headers=headers)
    else:
      request = urllib.request.Request(url, headers=headers)
    response = urllib.request.urlopen(request)
    html = response.read()
    response.close()
    return html

def remove(el):
    el.getparent().remove(el)

url = urllib.parse.quote(sys.argv[1],':?/=&#;')
select_div = sys.argv[2]
select_xpath = sys.argv[3]
css_file = sys.argv[4]
if css_file.endswith('.css'):
  css_file = css_file[:-4]
#print("ELEMENTS FOR REMOVAL:"+sys.argv[5])
elements_for_removal = eval(sys.argv[5])
#print("URL: "+url)
#print("class: "+select_div)
#print("select_xpath: "+select_xpath)
#print("CSS_FILE: "+css_file)
#print("ELEMENTS FOR REMOVAL: %s" % elements_for_removal)
try:
  html = get_page()
  page = fromstring(html.decode('utf8','ignore'))
  page.make_links_absolute(base_url=url)
  baseurl = url.split("#",2)

  for address in elements_for_removal:
    for element in page.xpath(address):
      remove(element)

  if css_file != '':
    print('<!DOCTYPE html>')
    print('<html><head><meta charset="utf-8">')
    print('<link rel="stylesheet" type="text/css" href="file://'+css_file+'.css"></head><body><div class="'+css_file+'"><div class="'+select_div+'">')
    if select_xpath != '':
      if not page.findall(select_xpath)==[]:
        for element in page.findall(select_xpath):
          print(tostring(element).decode('utf8').replace(baseurl[0]+"#","#") )
      else:
        print("Nothing found.")
    else:
      print(tostring(page).decode('utf8').replace(baseurl[0]+"#","#") )
    print('</div></div></body></html>')
  else:
    print(tostring(page).decode('utf8').replace(baseurl[0]+"#","#") )

except urllib.error.HTTPError as e:
  print('Downloading the page '+url+' failed with error code %s.' % e.code)
```


> Note
>
> 通过本地脚本输出html的方式可能造成页面上有些功能不可用，例如事件函数可能注册不上。
