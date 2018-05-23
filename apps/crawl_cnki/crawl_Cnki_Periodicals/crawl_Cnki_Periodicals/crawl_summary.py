#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = 'heianhu'

import os
import sys
from django.core.wsgi import get_wsgi_application
from selenium import webdriver  # 导入Selenium的webdriver
from selenium.webdriver.support.ui import Select  # 导入Select
from selenium.webdriver.common.keys import Keys  # 导入Keys
from selenium.webdriver.chrome.options import Options  # Chrome设置内容
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from scrapy.selector import Selector
from datetime import datetime
import time
import re
from django.db.models import Q
from django.db import IntegrityError


import crawl_cnki.crawl_Cnki_Periodicals.crawl_Cnki_Periodicals.utils as utils
from crawl_cnki.crawl_Cnki_Periodicals.crawl_Cnki_Periodicals.RegularExpressions import *

pathname = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.extend([pathname, ])
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ZhiWang.settings")
application = get_wsgi_application()
from crawl_cnki.models import Periodical, Article


class CrawlCnkiSummary(object):
    _root_url = 'http://nvsm.cnki.net'

    def __init__(self, use_Chrome=True, executable_path='', use_GPU=True):
        """
        初始化，建立与Django的models连接，设置初始值
        :param use_Chrome: True使用Chrome，False使用PhantomJS
        :param executable_path: PhantomJS路径
        :param use_GPU: 是否使用界面模式
        """
        self.use_GPU = use_GPU
        self.split_word = re.compile(
            r'(QueryID=[a-zA-Z0-9.]&|CurRec=\d*&|DbCode=[a-zA-Z]*&|urlid=[a-zA-Z0-9.]*&|yx=[a-zA-Z]*)',
            flags=re.I
        )
        self.re_issuing_time = re.compile(
            '((?!0000)[0-9]{4}[-/]((0[1-9]|1[0-2])[-/](0[1-9]|1[0-9]|2[0-8])|(0[13-9]|1[0-2])[-/](29|30)|(0[13578]|1[02])[-/]31)|([0-9]{2}(0[48]|[2468][048]|[13579][26])|(0[48]|[2468][048]|[13579][26])00)[-/]02[-/]29)')
        self.use_Chrome = use_Chrome
        self.executable_path = executable_path

    def test(self):
        summary = Periodical.objects.all()
        summary.abstract = 'ok'
        print(summary.abstract)

    def get_periodicals_summary(self, keyword, *args, first=True):
        """
        获取期刊概览
        (初始爬取功能)
        :param keyword: Periodicals对象
        :param args:
        :param first: 是否由新到旧
        :return:
        """
        start_url = self._root_url + '/kns/brief/result.aspx?dbprefix=CJFQ'

        if self.use_Chrome:
            # 使用Chrome
            if self.use_GPU:
                driver = webdriver.Chrome()  # 指定使用的浏览器，初始化webdriver
            else:
                # 设置Chrome无界面化
                chrome_options = Options()
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--disable-gpu')
                driver = webdriver.Chrome(chrome_options=chrome_options)  # 指定使用的浏览器，初始化webdriver
        else:
            desired_capabilities = DesiredCapabilities.PHANTOMJS.copy()
            desired_capabilities["phantomjs.page.settings.userAgent"] = \
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'
            desired_capabilities["phantomjs.page.settings.loadImages"] = False
            driver = webdriver.PhantomJS(executable_path=self.executable_path)  # 不载入图片，爬页面速度会快很多

        driver.get(start_url)
        elem = driver.find_element_by_id("magazine_value1")  # 找到name为q的元素，这里是个搜索框
        elem.send_keys(keyword.issn_number)
        select = Select(driver.find_element_by_id('magazine_special1'))  # 通过Select来定义该元素是下拉框
        select.select_by_index(1)  # 通过下拉元素的位置来选择
        elem.send_keys(Keys.RETURN)  # 相当于回车键，提交
        time.sleep(2)
        driver.get(
            url=self._root_url + '/kns/brief/brief.aspx?curpage=1&RecordsPerPage=20&QueryID=20&ID=&turnpage=1&dbPrefix=CJFQ&PageName=ASP.brief_result_aspx#J_ORDER&'
        )
        # 根据时间排序
        if first:
            # 第一次来先将时间由新到旧排序
            every_page_url = "/kns/brief/brief.aspx?{0}RecordsPerPage=20&QueryID=1&ID=&pagemode=L&dbPrefix=CJFQ&Fields=&DisplayMode=listmode&SortType=(%E5%8F%91%E8%A1%A8%E6%97%B6%E9%97%B4%2c%27TIME%27)+desc&PageName=ASP.brief_result_aspx#J_ORDER&"
        else:
            # 第二次来将时间由旧到新排序
            every_page_url = "/kns/brief/brief.aspx?{0}RecordsPerPage=20&QueryID=1&ID=&pagemode=L&dbPrefix=CJFQ&Fields=&DisplayMode=listmode&SortType=(%E5%8F%91%E8%A1%A8%E6%97%B6%E9%97%B4%2c%27TIME%27)&PageName=ASP.brief_result_aspx#J_ORDER&"
        t_selector = Selector(text=driver.page_source)
        pagenums = t_selector.css('.countPageMark::text').extract()
        try:
            # 拿到最大页数
            pagenums = int(pagenums[0].split('/')[1])
        except:
            pagenums = 1

        have_done = 0  # 监测是否已经提取过该概览
        for num in range(1, pagenums + 1):
            print(keyword.issn_number + ":page-" + str(num))
            curr_page = "curpage={0}&turnpage={0}&".format(num)
            if num == 1:
                page_url = every_page_url.format('')
            else:
                page_url = every_page_url.format(curr_page)
            # 遍历每一页
            driver.get(
                self._root_url + page_url
            )
            t_selector = Selector(text=driver.page_source)
            summarys = t_selector.css('.GridTableContent tr')[1:]
            # 获取每一个细节
            for i in summarys:
                if have_done >= 20:
                    # 如果有20个连续的url已重复表示之后的也都有收录过了
                    print('之后的爬取过，关闭该issn号')
                    driver.quit()
                    return
                # 匹配url
                url = i.css('.fz14::attr(href)').extract()[0]
                # 改成正常的url
                url = url.split('/kns')[-1]
                url = 'http://kns.cnki.net/KCMS' + url
                url = ''.join(url.split())  # 有些url中含有空格
                url = self.split_word.sub('', url)

                # 匹配title
                title = i.css('.fz14::text').extract()
                if not title:
                    continue
                else:
                    title = title[0][:255]

                # 匹配issuing_time
                issuing_time = i.css('.cjfdyxyz + td::text').extract()[0]
                issuing_time = utils.get_issuing_time(issuing_time)

                # 匹配引用次数
                cited = i.css('.KnowledgeNetcont a::text').extract()
                if not cited:
                    cited = 0
                else:
                    cited = int(cited[0])

                try:
                    summary = Article()
                    summary.url = url
                    summary.title = title
                    summary.periodicals = keyword
                    summary.issuing_time = datetime.strptime(issuing_time, '%Y-%m-%d').date()
                    summary.cited = cited
                    summary.filename = utils.get_filename_from_url(url)
                    summary.save()
                except IntegrityError:
                    have_done += 1
                    continue
        driver.quit()

    def crawl_periodicals_summary(self, *args, start_num=0, mark=False, issn_number=0):
        """
        爬取期刊概览内容
        (初始爬取功能)
        :param start_num: periodicals中ID-1
        :param mark: 若mark为True，则爬取数据库中标记(mark=true)的期刊概览内容，False则爬取全部期刊概览内容
        :param issn_number: issn号
        :return:
        """
        if mark:
            keywords = Periodical.objects.filter(mark=True)[start_num:]
        elif issn_number:
            keywords = Periodical.objects.filter(issn_number=issn_number)[start_num:]
        else:
            keywords = Periodical.objects.all()[start_num:]
        count = start_num
        for i in keywords:
            count += 1
            print(count, i.issn_number, 'new->old')
            self.get_periodicals_summary(i)
            print(count, i.issn_number, 'old->new')
            self.get_periodicals_summary(i, first=False)

    def incremental_crawl(self, *args, start_num=0, mark=False, issn_number=0):
        """
        用于增量处理
        不用去重，而是修改内容
        不仅增加未爬取过的文章，同时更新被引用次数
        :return:
        """
        if mark:
            keywords = Periodical.objects.filter(mark=True)[start_num:]
        elif issn_number:
            keywords = Periodical.objects.filter(issn_number=issn_number)[start_num:]
        else:
            keywords = Periodical.objects.all()[start_num:]
        count = start_num
        for i in keywords:
            count += 1
            print(count, i.issn_number, 'new->old')
            self.get_incremental_periodicals_summary(i)
            print(count, i.issn_number, 'old->new')
            self.get_incremental_periodicals_summary(i, first=False)

    def get_incremental_periodicals_summary(self, keyword, *args, first=True):

        start_url = self._root_url + '/kns/brief/result.aspx?dbprefix=CJFQ'

        if self.use_Chrome:
            # 使用Chrome
            if self.use_GPU:
                driver = webdriver.Chrome()  # 指定使用的浏览器，初始化webdriver
            else:
                # 设置Chrome无界面化
                chrome_options = Options()
                chrome_options.add_argument('--headless')
                chrome_options.add_argument('--disable-gpu')
                driver = webdriver.Chrome(chrome_options=chrome_options)  # 指定使用的浏览器，初始化webdriver
        else:
            desired_capabilities = DesiredCapabilities.PHANTOMJS.copy()
            desired_capabilities["phantomjs.page.settings.userAgent"] = \
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'
            desired_capabilities["phantomjs.page.settings.loadImages"] = False
            driver = webdriver.PhantomJS(executable_path=self.executable_path)  # 不载入图片，爬页面速度会快很多

        driver.get(start_url)
        elem = driver.find_element_by_id("magazine_value1")  # 找到name为q的元素，这里是个搜索框
        elem.send_keys(keyword.issn_number)
        select = Select(driver.find_element_by_id('magazine_special1'))  # 通过Select来定义该元素是下拉框
        select.select_by_index(1)  # 通过下拉元素的位置来选择
        elem.send_keys(Keys.RETURN)  # 相当于回车键，提交
        time.sleep(2)
        driver.get(
            url=self._root_url + '/kns/brief/brief.aspx?curpage=1&RecordsPerPage=20&QueryID=20&ID=&turnpage=1&dbPrefix=CJFQ&PageName=ASP.brief_result_aspx#J_ORDER&'
        )
        # 根据时间排序
        if first:
            # 第一次来先将时间由新到旧排序
            every_page_url = "/kns/brief/brief.aspx?{0}RecordsPerPage=20&QueryID=1&ID=&pagemode=L&dbPrefix=CJFQ&Fields=&DisplayMode=listmode&SortType=(%E5%8F%91%E8%A1%A8%E6%97%B6%E9%97%B4%2c%27TIME%27)+desc&PageName=ASP.brief_result_aspx#J_ORDER&"
        else:
            # 第二次来将时间由旧到新排序
            every_page_url = "/kns/brief/brief.aspx?{0}RecordsPerPage=20&QueryID=1&ID=&pagemode=L&dbPrefix=CJFQ&Fields=&DisplayMode=listmode&SortType=(%E5%8F%91%E8%A1%A8%E6%97%B6%E9%97%B4%2c%27TIME%27)&PageName=ASP.brief_result_aspx#J_ORDER&"
        t_selector = Selector(text=driver.page_source)
        pagenums = t_selector.css('.countPageMark::text').extract()
        try:
            # 拿到最大页数
            pagenums = int(pagenums[0].split('/')[1])
        except:
            pagenums = 1

        for num in range(1, pagenums + 1):
            print(keyword.issn_number + ":page-" + str(num))
            curr_page = "curpage={0}&turnpage={0}&".format(num)
            if num == 1:
                page_url = every_page_url.format('')
            else:
                page_url = every_page_url.format(curr_page)
            # 遍历每一页
            driver.get(
                self._root_url + page_url
            )
            t_selector = Selector(text=driver.page_source)
            summarys = t_selector.css('.GridTableContent tr')[1:]
            # 获取每一个细节
            for i in summarys:

                # 匹配url
                url = i.css('.fz14::attr(href)').extract()[0]
                # 改成正常的url
                url = url.split('/kns')[-1]
                url = 'http://kns.cnki.net/KCMS' + url
                url = ''.join(url.split())  # 有些url中含有空格
                url = self.split_word.sub('', url)

                # 匹配title
                title = i.css('.fz14::text').extract()
                if not title:
                    continue
                else:
                    title = title[0][:255]

                # 匹配issuing_time
                issuing_time = i.css('.cjfdyxyz + td::text').extract()[0]
                issuing_time = utils.get_issuing_time(issuing_time)

                # 匹配引用次数
                cited = i.css('.KnowledgeNetcont a::text').extract()
                if not cited:
                    cited = 0
                else:
                    cited = int(cited[0])

                try:
                    summary = Article()
                    summary.url = url
                    summary.title = title
                    summary.periodicals = keyword
                    summary.issuing_time = datetime.strptime(issuing_time, '%Y-%m-%d').date()
                    summary.cited = cited
                    summary.filename = utils.get_filename_from_url(url)
                    summary.save()
                except IntegrityError:
                    summary = Article.objects.get(url=url)
                    summary.title = title
                    summary.issuing_time = datetime.strptime(issuing_time, '%Y-%m-%d').date()
                    summary.cited = cited
                    summary.save()
        driver.quit()
